import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import requests
import shutil
import os
from datetime import datetime

# [환경 설정] 시간대 서울 설정
os.environ['TZ'] = 'Asia/Seoul'

# [설정] 안태희 님 정보
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    try: requests.get(url, params=params)
    except: pass

def send_telegram_photo(caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open("live_report.png", "rb") as photo:
            requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": photo})
    except: pass

st.set_page_config(page_title="울주 캠핑 정밀 감시", page_icon="📸")
st.title("📸 울주 캠핑 실시간 현장 중계")

target_date = st.text_input("감시할 날짜 입력", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 정밀 감시 시작"):
        st.session_state.run = True
        send_telegram_msg(f"🚨 [감시 가동] {target_date}일 침투를 시작합니다.")
with col2:
    if st.button("🛑 감시 중단"):
        st.session_state.run = False

log_area = st.empty()
image_area = st.empty() 

def status(msg):
    log_area.info(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] {msg}")

if st.session_state.run:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1600") # 세로로 길게 찍히도록 설정
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path: options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            status("🌐 캠핑장 사이트 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(10)
            
            # [단계 1] 버튼 클릭 (스크린샷 증거 남기기)
            try:
                status("🖱️ '예약하기(즉시결제)' 버튼 클릭 시도...")
                # 버튼을 찾아서 클릭
                btns = driver.find_elements(By.XPATH, "//a[contains(text(), '예약하기')]")
                if btns:
                    driver.execute_script("arguments[0].click();", btns[0])
                    time.sleep(5)
                else:
                    status("⚠️ 버튼이 보이지 않습니다. 이미 열려있는지 확인합니다.")
            except: pass

            driver.save_screenshot("live_report.png")
            image_area.image("live_report.png", caption="현재 접속 화면 (1단계)")

            # [단계 2] 예약 시스템(iframe) 내부로 진입
            status("🔍 예약창(iframe) 찾는 중...")
            found_frame = False
            for attempt in range(8):
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for i in range(len(iframes)):
                    driver.switch_to.default_content()
                    try:
                        driver.switch_to.frame(i)
                        if "달빛" in driver.page_source or "일정" in driver.page_source:
                            status(f"✅ {i+1}번 통로로 진입 성공!")
                            found_frame = True; break
                    except: continue
                if found_frame: break
                status(f"⏳ 대기 중... ({attempt+1}/8)")
                time.sleep(5)

            if not found_frame:
                status("❌ 입구 진입 실패. 텔레그램으로 현장 사진을 보냅니다.")
                send_telegram_photo(f"⚠️ {datetime.now().strftime('%H:%M')} 진입 실패 화면")
                driver.refresh()
                continue

            # [단계 3] 달빛야영장 선택 및 날짜 클릭
            try:
                # 구역 선택
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(3); break

                # 날짜 선택
                dates = driver.find_elements(By.XPATH, f"//*[not(self::script) and text()='{target_date}']")
                if dates:
                    driver.execute_script("arguments[0].click();", dates[-1])
                    status(f"📅 {target_date}일 클릭 완료! 로딩 대기 중...")
                    time.sleep(10)
                    
                    # 최종 결과 화면 저장 및 보고
                    driver.save_screenshot("live_report.png")
                    image_area.image("live_report.png", caption=f"{target_date}일 예약 현황")
                    
                    if "신청" in driver.page_source:
                        send_telegram_msg(f"🔔 [빈자리 발견!] {target_date}일에 신청 가능 자리가 떴습니다!")
                        send_telegram_photo(f"✅ {target_date}일 예약 현황 확인하세요!")
                        st.balloons()
                    else:
                        status(f"😴 {target_date}일 아직 자리가 없습니다.")
            except Exception as e:
                status(f"⚠️ 탐색 중 오류: {e}")

            status("💤 차단 방지를 위해 2분간 휴식합니다.")
            time.sleep(120) 
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 오류: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
