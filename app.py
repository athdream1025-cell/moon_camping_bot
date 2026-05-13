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

# [설정] 텔레그램 정보
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48Vpv (나머지 토큰)"
CHAT_ID = "529787781"

def status(msg):
    log_area.info(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] {msg}")

st.set_page_config(page_title="울주 캠핑 정밀 침투", page_icon="🎯")
st.title("🎯 울주 캠핑 경로 재정비 모드")

target_date = st.text_input("감시 날짜", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 감시 시작"):
        st.session_state.run = True
with col2:
    if st.button("🛑 중단"):
        st.session_state.run = False

log_area = st.empty()
image_area = st.empty() 

if st.session_state.run:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1800")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path: options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            status("🌐 사이트 접속 시도...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            
            # 페이지가 안정화될 때까지 대기 (최대 20초)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(5)
            
            # [수정] 강제 진입 전 현재 화면 캡쳐 (진단용)
            driver.save_screenshot("check.png")
            image_area.image("check.png", caption="진입 시도 전 메인 화면")

            try:
                status("🔑 강제 진입 스크립트 가동...")
                driver.execute_script("fn_move_page('01');") 
                time.sleep(10) # 예약창 생성 대기 시간 대폭 늘림
            except: pass

            # [수정] iframe 탐색 로직 강화
            status("🔍 예약창(iframe) 내부 수색 중...")
            found_frame = False
            for _ in range(5):
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for i in range(len(iframes)):
                    driver.switch_to.default_content()
                    try:
                        driver.switch_to.frame(i)
                        if "달빛" in driver.page_source:
                            status(f"✅ {i+1}번 통로 진입 성공!")
                            found_frame = True; break
                    except: continue
                if found_frame: break
                time.sleep(3)

            if not found_frame:
                status("❌ 입구 발견 실패. 다시 접속합니다.")
                driver.refresh()
                continue

            # [날짜 선택 로직은 이전과 동일하게 유지]
            # (이번 달 29일 정밀 타격 코드 삽입)
            
            time.sleep(180) 
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 오류: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
