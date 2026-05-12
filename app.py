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

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    try: requests.get(url, params=params)
    except: pass

st.set_page_config(page_title="울주 캠핑 비서 Pro", page_icon="🏕️")
st.title("🏕️ 울주 캠핑 예약 비서")

target_date = st.text_input("감시할 날짜 입력 (예: 29)", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 감시 시작"):
        st.session_state.run = True
with col2:
    if st.button("🛑 정지"):
        st.session_state.run = False

log_area = st.empty()

def status(msg):
    log_area.info(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] {msg}")

if st.session_state.run:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1200,1000") # 화면을 넉넉하게 잡음
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 20) # 20초까지는 무조건 기다려주는 비서
        
        while st.session_state.run:
            status("🌐 사이트 접속 및 예열 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            
            # 모든 팝업 무조건 제거
            time.sleep(3)
            try:
                while True:
                    driver.switch_to.alert.accept()
                    time.sleep(0.5)
            except: pass

            # [핵심] 달력 프레임이 나타날 때까지 대기 후 진입
            status("📥 달력 프레임 찾는 중...")
            try:
                # iframe이 화면에 생길 때까지 최대 20초 대기
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                driver.switch_to.frame(0)
                status("✅ 달력 내부 진입 성공!")
            except:
                status("❌ 달력이 숨어있습니다. 새로고침 중...")
                driver.refresh()
                continue

            # 구역 선택
            try:
                # 라디오 버튼이 뜰 때까지 대기
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='radio']")))
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(2)
                        break
            except: pass

            # [핵심] 태희 님이 찾은 p.day 구조 타격
            status(f"📅 {target_date}일 선택 시도...")
            try:
                # 텍스트가 정확히 숫자 29인 모든 요소를 다 뒤짐
                # p 태그 뿐만 아니라 span, a 등 모든 가능성을 열어둠
                possible_dates = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
                
                if possible_dates:
                    # 마지막 요소(이번 달 진짜 날짜) 클릭
                    driver.execute_script("arguments[0].click();", possible_dates[-1])
                    time.sleep(3)
                    
                    # 팝업 확인 (지난 날짜 방어)
                    try:
                        alert = driver.switch_to.alert
                        status(f"⚠️ 경고: {alert.text}")
                        alert.accept()
                    except:
                        # 빈자리 확인 로직
                        rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '신청')]]")
                        available_sites = []
                        for row in rows:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 3:
                                name = cells[2].text.strip()
                                if name and "접수" not in name:
                                    available_sites.append(name)
                        
                        if available_sites:
                            available_sites = sorted(list(set(available_sites)))
                            site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                            msg = f"🔔 [빈자리 발견!]\n📅 {target_date}일 달빛야영장\n---\n{site_list_str}"
                            send_telegram_msg(msg)
                            st.balloons()
                            st.session_state.run = False
                            break
                        else:
                            status(f"😴 {target_date}일 빈자리 없음 (1분 뒤 확인)")
            except: pass

            time.sleep(60)
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 오류: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
