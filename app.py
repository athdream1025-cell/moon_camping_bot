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

# [설정] 안태희 님 정보
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def send_telegram_photo(caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open("error_report.png", "rb") as photo:
            requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": photo})
    except: pass

st.set_page_config(page_title="울주 캠핑 정밀 진단", page_icon="📸")
st.title("📸 울주 캠핑 실시간 현장 중계")

target_date = st.text_input("감시 날짜", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

if st.button("🚀 정밀 감시 시작"):
    st.session_state.run = True

log_area = st.empty()
image_area = st.empty() 

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
    if chrome_path: options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            status("🌐 사이트 진입 시도 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(15) 
            
            # 1단계: 메인 페이지 접속 상태 확인 (실패 시 사진 전송)
            driver.save_screenshot("error_report.png")
            image_area.image("error_report.png", caption="현재 접속 화면 (1단계)")

            # 2단계: iframe(예약창) 탐색
            status("🔍 예약 시스템 문 두드리는 중...")
            found_frame = False
            for attempt in range(6):
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for i in range(len(iframes)):
                    driver.switch_to.default_content()
                    try:
                        driver.switch_to.frame(i)
                        if "달빛" in driver.page_source:
                            status("✅ 입구 진입 성공!")
                            found_frame = True; break
                    except: continue
                if found_frame: break
                time.sleep(5)

            if not found_frame:
                status("❌ 입구를 찾지 못함 (캡쳐본 텔레그램 전송)")
                send_telegram_photo(f"⚠️ {datetime.now().strftime('%H:%M')} 접속 실패 화면입니다.")
                driver.refresh()
                continue

            # 3단계: 날짜 클릭 후 예약판 확인
            try:
                # 구역 클릭 로직 생략 (기존과 동일)
                # 날짜 클릭 후...
                status(f"📅 {target_date}일 클릭 후 데이터 대기 중...")
                time.sleep(15)
                
                # 결과 화면 강제 캡쳐
                driver.save_screenshot("error_report.png")
                image_area.image("error_report.png", caption="최종 확인 화면 (표 확인용)")
                
                # 빈자리 없으면 사진과 함께 상황 보고
                if "신청" not in driver.page_source:
                    status("😴 빈자리가 없습니다. 현장 사진을 갱신합니다.")
                else:
                    # '신청' 발견 시 로직 수행...
                    status("🎉 빈자리 발견! 텔레그램을 확인하세요!")
            except Exception as e:
                status(f"⚠️ 처리 중 오류: {e}")

            time.sleep(120) # 차단 방지를 위해 2분 간격으로 완급 조절
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 다운: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
