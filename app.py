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
        # 대기 시간을 30초로 늘려 비서에게 인내심을 줍니다.
        wait = WebDriverWait(driver, 30)
        
        while st.session_state.run:
            status("🌐 사이트 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            
            # 1. 팝업 제거 (문 앞의 장애물 제거)
            time.sleep(5)
            try:
                for _ in range(5):
                    driver.switch_to.alert.accept()
                    time.sleep(1)
            except: pass

            # 2. [강화] 달력 입구(iframe) 찾기
            status("📥 달력 입구가 보일 때까지 기다리는 중...")
            try:
                # iframe이 로딩될 때까지 최대 30초 대기
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                
                # 발견하면 즉시 모든 프레임을 뒤져서 진입
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                found_cal = False
                for i in range(len(iframes)):
                    driver.switch_to.default_content()
                    driver.switch_to.frame(i)
                    if "달빛" in driver.page_source or "calendar" in driver.page_source.lower():
                        status(f"✅ {i+1}번 통로에서 달력 발견! 진입합니다.")
                        found_cal = True
                        break
                
                if not found_cal:
                    raise Exception("달력 내용이 비어있음")
                    
            except Exception as e:
                status("❌ 입구를 찾지 못했습니다. 기계 예열하듯 다시 시도합니다.")
                driver.refresh()
                time.sleep(5)
                continue

            # 3. 구역 및 날짜 클릭 (성공했던 로직 적용)
            try:
                # 달빛야영장 선택
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(2)
                        break

                status(f"📅 {target_date}일 선택 시도...")
                date_btns = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
                if date_btns:
                    driver.execute_script("arguments[0].click();", date_btns[-1])
                    time.sleep(3)
                    
                    # 4. 빈자리 확인 (성공했던 알림 포맷)
                    rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '신청')]]")
                    available_sites = []
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 3:
                            name = cells[2].text.strip()
                            if name and "접수" not in name:
                                available_sites.append(name)
                    
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
            except: pass

            time.sleep(60)
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 오류: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
