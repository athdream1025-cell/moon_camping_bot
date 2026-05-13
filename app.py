import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
import shutil
import os
from datetime import datetime

# [환경 설정]
os.environ['TZ'] = 'Asia/Seoul'

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

def status(msg):
    log_area.info(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] {msg}")

if st.session_state.run:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # 진짜 사람처럼 보이게 하는 필수 설정
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 15)
        
        while st.session_state.run:
            status("🌐 예약 사이트 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            
            # 1. 팝업 무조건 제거 (입구 확보)
            time.sleep(3)
            try:
                while True:
                    driver.switch_to.alert.accept()
                    time.sleep(0.5)
            except: pass

            # 2. 달력 iframe 진입 (여기가 막히면 안 됨!)
            status("📥 달력 시스템 진입 시도...")
            try:
                # iframe이 로딩될 때까지 기다림
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                driver.switch_to.frame(0)
                status("✅ 달력 내부 진입 성공!")
            except:
                status("❌ 달력 입구를 찾지 못해 재시도합니다.")
                driver.refresh()
                continue

            # 3. 달빛야영장 라디오 버튼 클릭
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='radio']")))
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(2)
                        break
            except: pass

            # 4. 날짜 클릭 (태희 님이 주신 p.day 구조와 일반 버튼 모두 대응)
            status(f"📅 {target_date}일 선택 중...")
            # 화면상의 '29'라는 숫자를 가진 모든 요소를 찾아 뒤에서부터(진짜 날짜) 클릭
            date_targets = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
            if date_targets:
                driver.execute_script("arguments[0].click();", date_targets[-1])
                time.sleep(3)
                
                # 5. 빈자리 데이터 추출 (텔레그램 성공 폼 그대로 복구)
                status("🔍 구역 이름 추출 중...")
                # '신청' 버튼이 있는 줄(tr)을 찾아서 이름(td)을 가져옵니다.
                rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '신청')]]")
                available_sites = []
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 3:
                        # 태희 님 텔레그램에 찍혔던 "작천정달빛야영장" 이름을 추출
                        site_name = cells[2].text.strip()
                        if site_name and "접수" not in site_name:
                            available_sites.append(site_name)
                
                if available_sites:
                    available_sites = sorted(list(set(available_sites)))
                    site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                    msg = f"🔔 [빈자리 알림!]\n📅 날짜: {target_date}일\n✅ 가능수: {len(available_sites)}개\n---\n{site_list_str}\n지금 바로 예약하세요!"
                    send_telegram_msg(msg)
                    st.balloons()
                    st.session_state.run = False
                    break
                else:
                    status(f"😴 {target_date}일 아직 자리가 없습니다.")
            
            # 다음 확인을 위해 대기
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 에러 발생: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
