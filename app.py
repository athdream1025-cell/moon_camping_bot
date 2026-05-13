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

def send_telegram_photo(caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open("live_report.png", "rb") as photo:
            requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": photo})
    except: pass

st.set_page_config(page_title="울주 캠핑 정밀 타격", page_icon="🎯")
st.title("🎯 울주 캠핑 이번 달 29일 정밀 타격")

target_date = st.text_input("감시 날짜 (예: 29)", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 정밀 감시 시작"):
        st.session_state.run = True
        send_telegram_msg(f"🎯 [타격 시작] {target_date}일(이번 달) 추적 개시")
with col2:
    if st.button("🛑 중단"):
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
    options.add_argument("--window-size=1280,1800")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path: options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            status("🌐 사이트 접속 및 강제 진입 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(12)
            
            # [단계 1] 버튼 무시하고 강제 예약창 열기
            try:
                driver.execute_script("fn_move_page('01');") 
                time.sleep(8)
            except: pass

            # [단계 2] iframe 내부 수색
            found_frame = False
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i in range(len(iframes)):
                driver.switch_to.default_content()
                try:
                    driver.switch_to.frame(i)
                    if "달빛" in driver.page_source:
                        found_frame = True; break
                except: continue
            
            if not found_frame:
                status("❌ 진입 실패. 재시도합니다.")
                driver.refresh()
                continue

            # [단계 3] 구역 선택 및 이번 달 날짜 타격
            try:
                # 구역 선택
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(4); break

                # 날짜 선택 (이번 달만 골라내기)
                status(f"🎯 이번 달 {target_date}일 찾는 중...")
                all_dates = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
                
                target_btn = None
                for btn in all_dates:
                    p_class = btn.find_element(By.XPATH, "./..").get_attribute("class") or ""
                    # 지난달(prev), 다음달(next) 클래스가 없는 것만 선택
                    if "prev" not in p_class and "next" not in p_class:
                        target_btn = btn; break
                
                if not target_btn and all_dates: target_btn = all_dates[-1]

                if target_btn:
                    driver.execute_script("arguments[0].click();", target_btn)
                    status(f"✅ {target_date}일 클릭 완료. 로딩 대기(15초)...")
                    time.sleep(15)
                    
                    driver.save_screenshot("live_report.png")
                    image_area.image("live_report.png", caption=f"{target_date}일 예약 현황")
                    
                    if "신청" in driver.page_source:
                        send_telegram_msg(f"🔔 [성공] {target_date}일 자리가 있습니다!")
                        st.balloons()
                else:
                    status(f"❌ {target_date}일을 찾지 못했습니다.")

            except Exception as e:
                status(f"⚠️ 탐색 오류: {e}")

            time.sleep(180) # 3분 간격
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 오류: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
