import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import requests
import shutil
import os
from datetime import datetime

# [환경 설정]
os.environ['TZ'] = 'Asia/Seoul'

# [설정] 안태희 님 텔레그램 정보
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    try: requests.get(url, params=params)
    except: pass

st.set_page_config(page_title="울주 캠핑 비서 Pro", page_icon="🏕️")
st.title("🏕️ 울주 캠핑 최종 진입 모드")

target_date = st.text_input("감시 날짜 (예: 29)", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

if st.button("🚀 감시 재시작"):
    st.session_state.run = True
    send_telegram_msg(f"🚨 [우회 모드 가동] {target_date}일 추적 시작")

log_area = st.empty()
image_area = st.empty() 

def status(msg):
    log_area.info(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] {msg}")

if st.session_state.run:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # [수정] 자동화 흔적 제거 옵션
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--window-size=1280,1024")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path: options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        # [수정] 웹드라이버 감지 방지 스크립트
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        while st.session_state.run:
            status("🌐 우회 경로로 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(15) 
            
            # [수정] iframe 탐색 로직 단순화 및 직접 타격
            status("🔍 예약창 찾는 중...")
            found_frame = False
            
            # 전체 페이지 소스에서 '달빛' 단어가 있는지 먼저 확인
            all_iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i, frame in enumerate(all_iframes):
                driver.switch_to.default_content()
                try:
                    driver.switch_to.frame(i)
                    if "달빛" in driver.page_source or "일정" in driver.page_source:
                        status(f"✅ 입구 발견! 진입합니다.")
                        found_frame = True
                        break
                except: continue
            
            if not found_frame:
                status("❌ 사이트 차단 의심. 5분 뒤 다시 시도합니다.")
                time.sleep(300) # 차단을 피하기 위해 쉬었다가 다시 시도
                driver.refresh()
                continue

            # (이후 로직 동일)
            try:
                # 구역/날짜 클릭 및 '신청' 버튼 체크 로직은 기존과 동일하게 유지
                status("🔘 날짜 및 구역 선택 진행...")
                # ... (생략된 기존 클릭 로직 수행) ...
                # (중략: 이전 코드의 클릭 및 추출 로직이 들어가는 부분)
                driver.save_screenshot("current_view.png")
                image_area.image("current_view.png")
                # ...
            except: pass

            time.sleep(60) 
            driver.refresh()
    except Exception as e:
        status(f"⚠️ 오류 발생: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
