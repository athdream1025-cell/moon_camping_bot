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

def status(msg):
    log_area.info(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] {msg}")

st.set_page_config(page_title="29일 강제 돌파", page_icon="⚡")
st.title("⚡ 29일 예약판 강제 기동 모드")

target_date = st.text_input("감시 날짜 (예: 29)", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 강제 기동 시작"):
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
            status("🌐 사이트 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(10)
            
            # [단계 1] 예약 페이지 강제 진입
            driver.execute_script("fn_move_page('01');") 
            time.sleep(8)

            # [단계 2] iframe 진입
            found_frame = False
            for i in range(10):
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for idx, frame in enumerate(iframes):
                    driver.switch_to.default_content()
                    try:
                        driver.switch_to.frame(idx)
                        if "달빛" in driver.page_source:
                            found_frame = True; break
                    except: continue
                if found_frame: break
                time.sleep(2)

            if not found_frame:
                status("❌ 입구 발견 실패. 재시도합니다.")
                driver.refresh()
                continue

            # [단계 3] 구역 선택 및 29일 데이터 강제 호출
            try:
                status("🔘 '달빛야영장' 구역 고정 중...")
                # 달빛야영장 라디오 버튼 강제 클릭
                driver.execute_script("document.getElementById('site_gubun_01').click();")
                time.sleep(3)

                # [핵심] 29일 클릭 대신, 날짜 데이터 불러오기 함수 직접 실행
                status(f"⚡ {target_date}일 예약 데이터 강제 호출 중...")
                # 사이트 내부 날짜 클릭 함수인 'fn_click_date'를 직접 때려 넣습니다.
                # 2026년 5월 29일 기준 명령 (날짜 형식에 맞춰 자동 생성)
                script_cmd = f"fn_click_date('2026-05-{target_date}');"
                driver.execute_script(script_cmd)
                
                status(f"✅ {target_date}일 데이터 요청 완료. 로딩 대기(15초)...")
                time.sleep(15)
                
                # 확인용 스크린샷
                driver.save_screenshot("final_report.png")
                image_area.image("final_report.png", caption=f"{target_date}일 강제 호출 결과")
                
                if "신청" in driver.page_source:
                    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text=🔔 [대박] {target_date}일 빈자리 강제 포착!")
                    st.balloons()
                else:
                    status(f"😴 {target_date}일 현재 자리가 없습니다.")

            except Exception as e:
                status(f"⚠️ 내부 가동 오류: {e}")

            time.sleep(180) 
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 다운: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
