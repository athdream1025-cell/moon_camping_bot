import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import requests
import shutil
from datetime import datetime

# [설정] 안태희 님 정보
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    try: requests.get(url, params=params)
    except: pass

st.set_page_config(page_title="울주 캠핑 비서 Pro", page_icon="🏕️")
st.title("🏕️ 울주 캠핑 예약 비서")

target_date = st.text_input("감시할 날짜 입력 (오늘 이후)", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 감시 시작"):
        st.session_state.run = True
with col2:
    if st.button("🛑 정지"):
        st.session_state.run = False

log_area = st.empty()

if st.session_state.run:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            # 1. 예약 페이지 접속
            log_area.info("🌐 예약 페이지 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(5)
            
            # 모든 팝업 무조건 닫기 (지난 날짜 경고 등)
            try:
                for _ in range(3):
                    driver.switch_to.alert.accept()
                    time.sleep(0.5)
            except: pass

            # 2. 달력 iframe 진입
            if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                driver.switch_to.frame(0)
                log_area.info("📥 달력 시스템 진입 성공")

            # 3. 달빛야영장 선택
            rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for rb in rbs:
                label = rb.find_element(By.XPATH, "./..").text
                if "달빛" in label:
                    driver.execute_script("arguments[0].click();", rb)
                    time.sleep(2)
                    break

            # 4. 날짜 클릭 (정밀 타격 방식)
            log_area.info(f"📅 {target_date}일 선택 시도...")
            
            # 날짜 숫자가 들어있는 칸을 더 정확하게 찾습니다.
            # a 태그 중에서 텍스트가 정확히 입력한 숫자(예: 29)인 것만 찾기
            date_elements = driver.find_elements(By.XPATH, f"//a[text()='{target_date}']")
            
            if date_elements:
                # 여러 개가 나올 수 있으므로 가장 마지막(보통 이번 달 날짜) 요소를 클릭
                driver.execute_script("arguments[0].click();", date_elements[-1])
                time.sleep(3)
                
                # 클릭 직후 팝업이 뜨면(지난 날짜 등) 잽싸게 닫고 다음 루프로
                try:
                    alert = driver.switch_to.alert
                    alert_text = alert.text
                    alert.accept()
                    log_area.error(f"⚠️ 사이트 경고 발생: {alert_text}")
                    time.sleep(2)
                    continue # 다시 처음부터 시도
                except: pass

                # 5. 빈자리 데이터 추출
                available_sites = []
                rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '신청')]]")
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 3:
                        name = next((c.text.strip() for c in cells if "달빛" in c.text and "야영장" not in c.text), cells[2].text.strip())
                        if name and "접수" not in name:
                            available_sites.append(name)
                
                if available_sites:
                    available_sites = sorted(list(set(available_sites)))
                    site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                    msg = f"🔔 [빈자리 알림!]\n📅 날짜: {target_date}일\n✅ 가능수: {len(available_sites)}개\n---\n{site_list_str}\n---\n지금 예약하세요!"
                    send_telegram_msg(msg)
                    st.balloons()
                    st.session_state.run = False
                    break
                else:
                    log_area.write(f"[{datetime.now().strftime('%H:%M:%S')}] {target_date}일 빈자리 없음")
            else:
                log_area.error(f"❌ 달력에서 {target_date}일을 찾을 수 없습니다.")
            
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        if "unexpected alert open" in str(e):
            try: driver.switch_to.alert.accept()
            except: pass
        else:
            st.error(f"⚠️ 에러 발생: {e}")
            st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
