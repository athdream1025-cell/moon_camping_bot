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

# [추가] 단계별 사진 촬영 및 텔레그램 발송 함수
def take_shot(driver, caption_text):
    try:
        driver.save_screenshot("live_report.png")
        image_area.image("live_report.png", caption=caption_text)
        # 텔레그램으로도 실시간 전송하여 폰으로 바로 확인 가능하게 함
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open("live_report.png", "rb") as photo:
            requests.post(url, data={"chat_id": CHAT_ID, "caption": f"📸 {caption_text}"}, files={"photo": photo})
    except:
        pass

st.set_page_config(page_title="29일 실시간 추적", page_icon="📸")
st.title("📸 울주 캠핑 단계별 실시간 인증 모드")

target_date = st.text_input("감시 날짜", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 실시간 추적 시작"):
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
            status("🌐 [1단계] 사이트 주소 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(8)
            
            # 인증샷 1: 접속 직후 메인 화면이 떴는지 확인
            take_shot(driver, "1단계: 사이트 접속 직후 화면")
            
            found_door = False
            for i in range(15): # 15번 돌파 시도
                try:
                    status(f"🔑 [2단계] 입구 강제 개방 시도 중... ({i+1}/15)")
                    driver.execute_script("fn_move_page('01');") 
                    time.sleep(2)
                    
                    # 매 시도마다 화면이 변하는지 캡쳐
                    if i % 3 == 0:
                        take_shot(driver, f"2단계: 입구 개방 시도 중 ({i+1}회째)")
                    
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

            if not found_door:
                status("❌ 입구 돌파 실패. 사진 전송 후 새로고침합니다.")
                take_shot(driver, "⚠️ 입구 돌파 실패 시점의 최종 화면")
                time.sleep(5)
                driver.refresh()
                continue

            # 인증샷 2: iframe 내부 진입 성공 확인
            take_shot(driver, "✅ 2단계 성공: 예약 달력 창 진입 완료")

            # [3단계] 구역 고정 및 날짜 타격
            try:
                status("🔘 [3단계] '달빛야영장' 구역 선택 중...")
                driver.execute_script("document.getElementById('site_gubun_01').click();")
                time.sleep(2)
                
                status(f"🎯 [4단계] 이번 달 {target_date}일 정밀 조준...")
                target_btn = driver.find_element(By.開, f"//td[not(contains(@class, 'prev')) and not(contains(@class, 'next'))]//a[text()='{target_date}']")
                driver.execute_script("arguments[0].click();", target_btn)
                
                status(f"✅ {target_date}일 클릭 완료! 최종 로딩 중...")
                time.sleep(12)
                
                # 인증샷 3: 날짜 클릭 후 최종 결과 화면
                take_shot(driver, f"🎯 최종 결과: {target_date}일 예약판 상황")
                
                if "신청" in driver.page_source:
                    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text=🔔 빈자리 감지! 지금 선점하세요!")
                    st.balloons()
            except Exception as e:
                status("⚠️ 내부 탐색 중 오류 발생")
                take_shot(driver, "⚠️ 날짜 클릭 단계 오류 발생 시점 화면")

            status("💤 순찰 완료. 3분 대기 후 다음 바퀴를 돕니다.")
            time.sleep(180) 
            driver.refresh()

    except Exception as e:
        status("⚠️ 시스템 오류 발생으로 정지")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
