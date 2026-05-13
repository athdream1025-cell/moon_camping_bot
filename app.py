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
        send_telegram_msg(f"🎯 {target_date}일 달빛야영장 정밀 타격 시작합니다!") 
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
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            status("🌐 사이트 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(7)
            
            # 팝업 처리
            try:
                alert = driver.switch_to.alert
                alert.accept()
            except: pass

            # 1. 모든 프레임을 뒤져서 확실히 진입
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i in range(len(iframes)):
                driver.switch_to.default_content()
                try:
                    driver.switch_to.frame(i)
                    if "달빛" in driver.page_source:
                        status(f"✅ {i+1}번 프레임에서 달력 포착!")
                        break
                except: continue

            # 2. [강력 수정] 달빛야영장 및 날짜 클릭
            try:
                # '달빛'이라는 글자가 포함된 라디오 버튼을 더 정밀하게 찾습니다.
                status("🔘 달빛야영장 선택 중...")
                labels = driver.find_elements(By.TAG_NAME, "label")
                for label in labels:
                    if "달빛" in label.text:
                        # 라벨 클릭이 더 확실할 때가 있습니다.
                        driver.execute_script("arguments[0].click();", label)
                        time.sleep(2)
                        break

                # 날짜 클릭 (p.day 혹은 텍스트 기반)
                status(f"📅 {target_date}일 버튼 강제 클릭...")
                # 텍스트가 정확히 '29'인 요소를 찾아서 가장 마지막 것(이번 달)을 클릭
                date_btns = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
                if date_btns:
                    # 클릭 전 화면 중앙으로 이동 후 클릭
                    target_btn = date_btns[-1]
                    driver.execute_script("arguments[0].scrollIntoView(true);", target_btn)
                    driver.execute_script("arguments[0].click();", target_btn)
                    
                    # [핵심] 클릭 후 표가 완전히 바뀔 때까지 충분히 기다림
                    status("⏳ 표 데이터 로딩 대기 (12초)...")
                    time.sleep(12) 
                    
                    # 3. 빈자리 추출 (어제 14개 성공했던 그 로직)
                    # 표 안에 '신청'이라는 글자가 하나라도 있는지 먼저 확인
                    if "신청" in driver.page_source:
                        status("✨ 빈자리 포착! 목록 정리 중...")
                        rows = driver.find_elements(By.XPATH, "//tr[contains(., '신청')]")
                        available_sites = []
                        for row in rows:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 3:
                                site_name = cells[2].text.strip()
                                # '접수'는 빼고 '신청' 가능한 구역만
                                if site_name and "접수" not in site_name:
                                    available_sites.append(site_name)
                        
                        if available_sites:
                            available_sites = sorted(list(set(available_sites)))
                            site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                            msg = f"🔔 [빈자리 발견!]\n📅 날짜: {target_date}일\n✅ 가능수: {len(available_sites)}개\n---\n{site_list_str}\n지금 바로 예약하세요!"
                            send_telegram_msg(msg)
                            st.balloons()
                        else:
                            status(f"😴 {target_date}일 조건에 맞는 구역 없음")
                    else:
                        status(f"😴 {target_date}일 표에 '신청' 버튼이 안 보임")
                else:
                    status(f"❌ {target_date}일 날짜 버튼을 못 찾았습니다.")
            except Exception as e:
                status(f"⚠️ 클릭 중 오류: {e}")

            time.sleep(60) 
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 에러: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
