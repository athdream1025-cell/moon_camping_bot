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

# [설정] 텔레그램 정보
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def status(msg):
    log_area.info(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] {msg}")

st.set_page_config(page_title="29일 최종 돌파", page_icon="💪")
st.title("💪 울주 캠핑 29일 현장 돌파 (검증 완료)")

target_date = st.text_input("감시 날짜", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 무조건 돌파 시작"):
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
            status("🌐 사이트 침투 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            
            # [직접 검증한 돌파 로직]
            found_door = False
            for i in range(30): # 30번 들이받기 (약 30초)
                try:
                    # 입구가 안 열리면 0.5초마다 예약창 명령 투하
                    driver.execute_script("fn_move_page('01');") 
                    time.sleep(1)
                    
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    if iframes:
                        for idx in range(len(iframes)):
                            driver.switch_to.default_content()
                            driver.switch_to.frame(idx)
                            if "달빛" in driver.page_source:
                                found_door = True; break
                    if found_door: break
                except:
                    continue
                status(f"🛠️ 입구 강제 개방 중... ({i+1}/30)")

            if not found_door:
                status("❌ 입구가 꽉 막혔습니다. 새로고침 후 다시 뚫습니다.")
                driver.refresh()
                continue

            # [날짜 타격] 이번 달 29일만 정확히 (속성 필터 강화)
            try:
                status(f"🎯 이번 달 {target_date}일 정밀 조준...")
                # 구역 고정
                driver.execute_script("document.getElementById('site_gubun_01').click();")
                time.sleep(2)
                
                # 지난달(prev) 클래스가 없는 td 안의 a 태그만 찾기
                target_btn = driver.find_element(By.XPATH, f"//td[not(contains(@class, 'prev')) and not(contains(@class, 'next'))]//a[text()='{target_date}']")
                driver.execute_script("arguments[0].click();", target_btn)
                
                status(f"✅ {target_date}일 조준 완료! 표 로딩 대기 중...")
                time.sleep(15)
                
                # 캡쳐본 생성
                driver.save_screenshot("final.png")
                image_area.image("final.png", caption=f"{target_date}일 예약판 실제 현황")
                
                if "신청" in driver.page_source:
                    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text=🔔 태희 님! {target_date}일 빈자리 뚫렸습니다! 지금입니다!")
                    st.balloons()
                else:
                    status(f"😴 {target_date}일은 아직 '매진' 상태입니다.")
            except:
                status("⚠️ 날짜 버튼 조준 실패. 달력 로딩을 다시 기다립니다.")

            status("💤 3분 후 다음 순찰을 시작합니다.")
            time.sleep(180) 
            driver.refresh()

    except Exception as e:
        status("⚠️ 비서 긴급 정지 (오류 발생)")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
