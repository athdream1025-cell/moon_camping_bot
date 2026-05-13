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
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def status(msg):
    log_area.info(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] {msg}")

st.set_page_config(page_title="29일 정밀 돌파", page_icon="🎯")
st.title("🎯 울주 캠핑 29일 정밀 조준 모드")

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
        wait = WebDriverWait(driver, 20)
        
        while st.session_state.run:
            status("🌐 사이트 접속 및 부품 대기 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            
            # [핵심 수리] 'fn_move_page' 부품이 로딩될 때까지 최대 20초 대기
            try:
                wait.until(lambda d: d.execute_script("return typeof fn_move_page === 'function'"))
                status("✅ 시스템 부품 준비 완료. 진입합니다.")
                driver.execute_script("fn_move_page('01');") 
                time.sleep(10)
            except:
                status("⚠️ 로딩 지연으로 재접속합니다.")
                driver.refresh()
                continue

            # [단계 2] iframe 진입
            found_frame = False
            for _ in range(5):
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for i, frame in enumerate(iframes):
                    driver.switch_to.default_content()
                    try:
                        driver.switch_to.frame(i)
                        if "달빛" in driver.page_source:
                            found_frame = True; break
                    except: continue
                if found_frame: break
                time.sleep(3)

            if found_frame:
                status("🔍 이번 달 29일 조준 중...")
                # 달빛야영장 고정
                driver.execute_script("document.getElementById('site_gubun_01').click();")
                time.sleep(3)

                # [태희 님 지적 사항] 지난달 29일 제외하고 이번 달만 클릭
                # td 태그 중 prev_month 클래스가 없는 녀석 안의 29일을 찾습니다.
                try:
                    target_btn = driver.find_element(By.XPATH, f"//td[not(contains(@class, 'prev')) and not(contains(@class, 'next'))]//a[text()='{target_date}']")
                    driver.execute_script("arguments[0].click();", target_btn)
                    status(f"🎯 이번 달 {target_date}일 정밀 타격 성공!")
                    time.sleep(15)
                    
                    driver.save_screenshot("report.png")
                    image_area.image("report.png", caption=f"{target_date}일 실제 상황")
                    
                    if "신청" in driver.page_source:
                        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text=🔔 {target_date}일 빈자리 떴습니다!")
                        st.balloons()
                except:
                    status(f"❌ 이번 달 {target_date}일을 아직 찾지 못했습니다.")

            time.sleep(180)
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 다운: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
