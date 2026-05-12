import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import requests
import shutil

# [설정] 안태희 님 정보
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    try: requests.get(url, params=params)
    except: pass

st.set_page_config(page_title="울주 캠핑 비서", page_icon="🏕️")
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
        st.warning("감시를 중단합니다.")

log_area = st.empty()

if st.session_state.run:
    log_area.info(f"🔄 {target_date}일 빈자리 감시 시작...")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # 서버에 설치된 크롬 경로 찾기
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        # webdriver-manager 대신 셀레니움 4.x의 기본 드라이버 매니저 사용
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            driver.get("https://camping.ulju.ulsan.kr/index.jsp")
            time.sleep(3)
            
            # --- 로그인 로직 ---
            try:
                driver.find_element(By.PARTIAL_LINK_TEXT, "로그인").click()
                time.sleep(3)
                login_inputs = driver.find_elements(By.CLASS_NAME, "inputLogin")
                if len(login_inputs) >= 2:
                    login_inputs[0].send_keys("athdream")
                    login_inputs[1].send_keys("!raul3011o")
                    login_inputs[1].send_keys(Keys.ENTER)
                    time.sleep(3)
                    try: driver.switch_to.alert.accept()
                    except: pass
            except: pass

            # --- 예약 확인 로직 ---
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(5)
            if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                driver.switch_to.frame(0)

            # 야영장(달빛) 선택
            rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for rb in rbs:
                if "달빛" in rb.find_element(By.XPATH, "./..").text:
                    driver.execute_script("arguments[0].click();", rb)
                    time.sleep(2)
                    try: driver.switch_to.alert.accept()
                    except: pass
                    break

            # 날짜 선택 및 신청 버튼 체크
            dates = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
            if dates:
                driver.execute_script("arguments[0].click();", dates[-1])
                time.sleep(3)
                
                apply_btns = driver.find_elements(By.XPATH, "//*[contains(text(), '신청')]")
                active_list = [b for b in apply_btns if b.is_displayed()]
                
                if active_list:
                    msg = f"🔔 [빈자리!] {target_date}일 예약 가능! 지금 바로 접속하세요!"
                    send_telegram_msg(msg)
                    st.balloons()
                    log_area.success(msg)
                    st.session_state.run = False
                    break
            
            log_area.write(f"[{time.strftime('%H:%M:%S')}] {target_date}일 체크 중... 빈자리 없음")
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        st.error(f"⚠️ 오류 발생: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals():
            driver.quit()
