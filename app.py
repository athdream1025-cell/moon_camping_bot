import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

target_date = st.text_input("감시할 날짜 입력 (예: 29)", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 정밀 감시 시작"):
        st.session_state.run = True
with col2:
    if st.button("🛑 정지"):
        st.session_state.run = False

log_area = st.empty()

def status(msg):
    log_area.info(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] {msg}")

if st.session_state.run:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # 사람처럼 보이게 하는 필수 설정
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 15) # 최대 15초 대기 설정
        
        while st.session_state.run:
            # 1. 메인 접속
            status("🌐 사이트 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/index.jsp")
            time.sleep(3)
            
            # 팝업 제거
            try:
                while True:
                    driver.switch_to.alert.accept()
                    status("⚠️ 팝업창을 닫았습니다.")
                    time.sleep(1)
            except: pass

            # 2. 로그인 시도
            status("🔑 로그인 페이지 이동...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/member/login")
            time.sleep(3)
            
            try:
                id_field = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "inputLogin")))
                inputs = driver.find_elements(By.CLASS_NAME, "inputLogin")
                if len(inputs) >= 2:
                    inputs[0].send_keys("athdream")
                    inputs[1].send_keys("!raul3011o")
                    inputs[1].send_keys(Keys.ENTER)
                    status("🚀 로그인 정보 전송 완료")
                    time.sleep(5) # 로그인 후 대기시간 충분히
                    
                    try:
                        while True:
                            driver.switch_to.alert.accept()
                            status("⚠️ 로그인 성공/실패 팝업 확인")
                            time.sleep(1)
                    except: pass
            except:
                status("ℹ️ 이미 로그인 상태이거나 입력 필드를 찾지 못함")

            # 3. 예약 페이지 이동
            status("📅 예약 캘린더 페이지 이동...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(5)
            
            try: driver.switch_to.alert.accept()
            except: pass

            if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                driver.switch_to.frame(0)
                status("📥 프레임(iframe) 전환 완료")

            # 4. 야영장 및 날짜 클릭
            status(f"🔎 {target_date}일 빈자리 체크 중...")
            rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for rb in rbs:
                if "달빛" in rb.find_element(By.XPATH, "./..").text:
                    driver.execute_script("arguments[0].click();", rb)
                    time.sleep(2)
                    break

            dates = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
            if dates:
                driver.execute_script("arguments[0].click();", dates[-1])
                time.sleep(3)
                
                # 상세 추출
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
                    msg = f"🔔 [빈자리!]\n📅 {target_date}일\n✅ {len(available_sites)}개 구역\n---\n{site_list_str}"
                    send_telegram_msg(msg)
                    st.balloons()
                    status("🎉 텔레그램 발송 완료!")
                    st.session_state.run = False
                    break
            
            status(f"😴 {target_date}일 자리 없음. 60초 후 재시도...")
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 에러 발생: {e}")
    finally:
        if 'driver' in locals(): driver.quit()
