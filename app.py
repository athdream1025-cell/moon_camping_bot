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
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 10) # 대기 시간을 효율적으로 단축
        
        while st.session_state.run:
            status("🌐 사이트 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            
            # 1. [유연한 팝업 처리] 있으면 닫고, 없으면 바로 통과
            try:
                # 2초만 딱 기다려보고 팝업 있으면 확인 클릭
                WebDriverWait(driver, 2).until(EC.alert_is_present())
                while True:
                    alert = driver.switch_to.alert
                    alert.accept()
                    time.sleep(0.3)
            except:
                status("ℹ️ 현재는 팝업창이 없습니다. 바로 진행합니다.")

            # 2. [입구 돌파] iframe 진입 강화
            status("📥 달력 시스템 진입 시도...")
            try:
                # iframe이 나타날 때까지 최대 10초 대기 후 즉시 전환
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
                status("✅ 달력 내부 진입 성공!")
            except:
                status("❌ 입구 진입 실패. 다시 시도합니다.")
                driver.refresh()
                continue

            # 3. 어제 성공했던 14개 추출 로직 시작
            try:
                # 구역 선택 (달빛)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='radio']")))
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(1)
                        break

                # 날짜 선택
                status(f"📅 {target_date}일 선택 시도...")
                date_btns = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
                if date_btns:
                    driver.execute_script("arguments[0].click();", date_btns[-1])
                    time.sleep(2)
                    
                    # 4. 빈자리 추출 (어제 성공 로직)
                    rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '신청')]]")
                    available_sites = []
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 3:
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
                        status(f"😴 {target_date}일 빈자리 없음")
            except: pass

            time.sleep(60)
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 에러: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
