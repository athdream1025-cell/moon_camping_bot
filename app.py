import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
st.title("🏕️ 울주 캠핑 예약 비서 Pro")

# [중요] 오늘 날짜를 기준으로 기본값 설정
now = datetime.now()
current_day = now.day # 오늘이 13일이면 13이 됨

# 사용자에게 날짜를 입력받되, 기본값을 29일(미래)로 고정
target_date = st.text_input("감시할 날짜 입력 (오늘 이후 날짜만 가능)", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 정밀 감시 시작"):
        # 지난 날짜를 입력했을 경우 실행 차단
        if int(target_date) <= current_day:
            st.error(f"⚠️ {target_date}일은 오늘({current_day}일)이거나 이미 지났습니다! 14일 이후를 입력하세요.")
        else:
            st.session_state.run = True
with col2:
    if st.button("🛑 정지"):
        st.session_state.run = False

log_area = st.empty()

if st.session_state.run:
    log_area.info(f"🔄 {target_date}일 데이터를 가져오는 중... (철저 방어 모드)")
    
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
            # 1. 예약 페이지로 바로 접속
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(4)
            
            # 사이트 접속하자마자 뜨는 모든 알림창(지난 날짜 등) 무조건 닫기
            try:
                for _ in range(3):
                    driver.switch_to.alert.accept()
                    time.sleep(0.5)
            except: pass

            # 2. iframe 전환 (달력 영역으로 들어가기)
            if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                driver.switch_to.frame(0)

            # 3. 달빛야영장 라디오 버튼 클릭
            rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for rb in rbs:
                label = rb.find_element(By.XPATH, "./..").text
                if "달빛" in label:
                    driver.execute_script("arguments[0].click();", rb)
                    time.sleep(2)
                    break

            # 4. 날짜 클릭 (target_date가 13보다 커야 에러가 안 남)
            dates = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
            if dates:
                driver.execute_script("arguments[0].click();", dates[-1])
                time.sleep(3)
                
                # 클릭 후에도 팝업이 뜨면 닫기
                try: driver.switch_to.alert.accept()
                except: pass
                
                # 5. 상세 구역 이름 수집
                available_sites = []
                rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '신청')]]")
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 3:
                        # '달빛' 글자가 포함된 상세 명칭 칸을 찾음
                        name = next((c.text.strip() for c in cells if "달빛" in c.text and "야영장" not in c.text), cells[2].text.strip())
                        if name and "접수" not in name:
                            available_sites.append(name)
                
                if available_sites:
                    available_sites = sorted(list(set(available_sites)))
                    site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                    msg = f"🔔 [빈자리 알림!]\n📅 날짜: {target_date}일\n✅ 가능수: {len(available_sites)}개\n------------------\n{site_list_str}\n------------------\n지금 예약하세요!"
                    send_telegram_msg(msg)
                    st.balloons()
                    st.session_state.run = False
                    break
            
            log_area.write(f"[{datetime.now().strftime('%H:%M:%S')}] {target_date}일 감시 중... 이상 없음")
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        if "unexpected alert open" in str(e):
            try: driver.switch_to.alert.accept()
            except: pass
        else:
            st.error(f"⚠️ 시스템 오류: {e}")
            st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
