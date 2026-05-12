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

target_date = st.text_input("감시할 날짜 입력 (예: 29)", value="29")

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
            log_area.info("🌐 사이트 접속 및 환경 설정 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(5)
            
            # 모든 초기 팝업 강제 제거
            try:
                for _ in range(5):
                    driver.switch_to.alert.accept()
                    time.sleep(0.5)
            except: pass

            if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                driver.switch_to.frame(0)

            # 달빛야영장 선택
            rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for rb in rbs:
                if "달빛" in rb.find_element(By.XPATH, "./..").text:
                    driver.execute_script("arguments[0].click();", rb)
                    time.sleep(2)
                    break

            # --- [핵심 수정] 날짜 선택 로직 강화 ---
            log_area.info(f"📅 {target_date}일 버튼을 정밀하게 찾는 중...")
            
            # 1. 'a' 태그 중에서 텍스트가 target_date와 정확히 일치하는 것들을 모두 찾음
            all_dates = driver.find_elements(By.XPATH, f"//a[text()='{target_date}']")
            
            clicked = False
            for date_btn in all_dates:
                # 2. 버튼의 부모나 주변 요소에 '지난 날짜'를 뜻하는 클래스가 있는지 체크 (사이트마다 다름)
                # 여기서는 '미래 날짜'여서 클릭 가능한 버튼인지 시도해보고 팝업이 뜨면 다음 버튼으로 넘깁니다.
                try:
                    driver.execute_script("arguments[0].click();", date_btn)
                    time.sleep(2)
                    
                    # 클릭 직후 팝업이 뜨는지 확인
                    try:
                        alert = driver.switch_to.alert
                        log_area.warning(f"⚠️ 무시된 버튼: {alert.text}")
                        alert.accept() # 지난 날짜 팝업이면 닫고 다음 버튼 시도
                        continue 
                    except:
                        # 팝업이 안 떴다면 정상적으로 날짜가 선택된 것!
                        clicked = True
                        log_area.success(f"✅ {target_date}일 선택 성공!")
                        break
                except:
                    continue

            if clicked:
                # 3. 빈자리 데이터 추출
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
                    msg = f"🔔 [빈자리 알림!]\n📅 날짜: {target_date}일\n✅ {len(available_sites)}개 가능\n---\n{site_list_str}"
                    send_telegram_msg(msg)
                    st.balloons()
                    st.session_state.run = False
                    break
                else:
                    log_area.write(f"[{datetime.now().strftime('%H:%M:%S')}] {target_date}일 빈자리 없음")
            else:
                log_area.error(f"❌ {target_date}일을 클릭할 수 없습니다. (날짜 확인 필요)")
            
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
