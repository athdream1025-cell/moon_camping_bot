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

# [설정] 안태희 님 텔레그램 정보
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def status(msg):
    log_area.info(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] {msg}")

def take_shot(driver, caption_text):
    try:
        driver.save_screenshot("live_report.png")
        image_area.image("live_report.png", caption=caption_text)
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open("live_report.png", "rb") as photo:
            requests.post(url, data={"chat_id": CHAT_ID, "caption": f"📸 {caption_text}"}, files={"photo": photo})
    except:
        pass

st.set_page_config(page_title="29일 최종 해결", page_icon="⚙️")
st.title("⚙️ 울주 캠핑 29일 동기화 완료 버전")

target_date = st.text_input("감시 날짜", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 감시 가동"):
        st.session_state.run = True
with col2:
    if st.button("🛑 중단"):
        st.session_state.run = False

log_area = st.empty()
image_area = st.empty() 

if st.session_state.run:
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1800")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path: options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        # 정밀 대기 툴 세팅 (최대 20초 대기하도록 설정)
        wait = WebDriverWait(driver, 20)
        
        while st.session_state.run:
            status("🌐 [1단계] 울주 캠핑장 메인 페이지 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(8)
            
            # [2단계] 강제 진입 스크립트 실행
            status("🔑 [2단계] 예약 시스템 호출 중...")
            driver.execute_script("fn_move_page('01');") 
            time.sleep(5)
            
            # [핵심 수정] iframe(예약 방)이 생성될 때까지 기다렸다가 비서를 방 안으로 확실히 밀어넣기
            status("🔍 [3단계] 예약 달력 방(iframe) 탐색 및 입장...")
            found_door = False
            for _ in range(10):
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for idx, frame in enumerate(iframes):
                    driver.switch_to.default_content()
                    try:
                        driver.switch_to.frame(idx)
                        if "달빛" in driver.page_source:
                            status(f"✅ 예약 방 내부 진입 성공! (통로 번호: {idx})")
                            found_door = True; break
                    except: continue
                if found_door: break
                time.sleep(2)

            if not found_door:
                status("❌ 예약 방 입장 실패. 새로고침 후 다시 시도합니다.")
                driver.refresh()
                continue

            # 이 시점에 스크린샷 한 번 찍어보냅니다 (달력이 정상 확인되었는지)
            take_shot(driver, "3단계: 예약 방 내부 진입 인증샷")

            # [4단계] 구역 고정 및 날짜 타격
            try:
                status("🔘 [4단계] 구역 라디오 버튼이 태어날 때까지 대기 중...")
                # 화면에 'site_gubun_01' 이라는 ID를 가진 버튼이 실제로 등장할 때까지 물리적으로 대기합니다.
                zone_btn = wait.until(EC.presence_of_element_located((By.ID, "site_gubun_01")))
                
                status("✅ 구역 버튼 확인! '달빛야영장' 강제 고정합니다.")
                driver.execute_script("arguments[0].click();", zone_btn)
                time.sleep(3)
                
                status(f"🎯 [5단계] 이번 달 {target_date}일 정밀 조준 중...")
                # 지난달/다음달 흐릿한 29일 필터링하여 진짜 이번 달 29일만 지정
                target_btn = wait.until(EC.element_to_be_clickable((By.XPATH, f"//td[not(contains(@class, 'prev')) and not(contains(@class, 'next'))]//a[text()='{target_date}']")))
                driver.execute_script("arguments[0].click();", target_btn)
                
                status(f"✅ {target_date}일 클릭 완료! 예약 현황 표 로딩 대기 (15초)...")
                time.sleep(15)
                
                # 최종 성공 스크린샷 보냄
                take_shot(driver, f"🎯 최종 결과: {target_date}일 예약판 로딩 완료 화면")
                
                if "신청" in driver.page_source:
                    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text=🔔 [성공] {target_date}일 빈자리가 발견되었습니다!")
                    st.balloons()
                else:
                    status(f"😴 {target_date}일은 아직 매진 상태입니다.")

            except Exception as e:
                status(f"⚠️ 내부 조작 중 에러 발생 (로딩 지연): {e}")
                take_shot(driver, "⚠️ 내부 단계 에러 발생 시점 화면")

            status("💤 한 바퀴 순찰 완료. 3분 대기 후 다시 출발합니다.")
            time.sleep(180) 
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 전체 시스템 일시 다운: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
