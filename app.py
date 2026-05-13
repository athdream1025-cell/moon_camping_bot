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
        send_telegram_msg(f"✅ 캠핑 비서가 {target_date}일 정밀 감시를 시작합니다!") 
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
            time.sleep(6) # 사이트 로딩 대기
            
            # 팝업 처리
            try:
                alert = driver.switch_to.alert
                alert.accept()
            except: pass

            # 1. 달력 프레임 진입
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i in range(len(iframes)):
                driver.switch_to.default_content()
                try:
                    driver.switch_to.frame(i)
                    if "달빛" in driver.page_source:
                        break
                except: continue

            # 2. 구역 및 날짜 클릭
            try:
                # 구역(달빛) 선택
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(2)
                        break

                status(f"📅 {target_date}일 클릭 및 표 로딩 대기 (10초)...")
                date_btns = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
                if date_btns:
                    # 실제 날짜 버튼 클릭
                    driver.execute_script("arguments[0].click();", date_btns[-1])
                    
                    # [핵심] 표가 새로 그려질 때까지 10초간 넉넉히 대기합니다.
                    time.sleep(10) 
                    
                    # 3. 빈자리 추출 (어제 성공 로직)
                    status("🔍 실시간 데이터 추출 중...")
                    # '신청' 또는 '예약' 버튼이 포함된 줄(tr)을 모두 찾습니다.
                    rows = driver.find_elements(By.XPATH, "//tr[contains(., '신청')]")
                    
                    available_sites = []
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 3:
                            site_name = cells[2].text.strip()
                            # '신청' 버튼이 활성화된 행만 수집
                            if site_name and "접수" not in site_name:
                                available_sites.append(site_name)
                    
                    if available_sites:
                        available_sites = sorted(list(set(available_sites)))
                        site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                        msg = f"🔔 [빈자리 발견!]\n📅 날짜: {target_date}일\n✅ 가능수: {len(available_sites)}개\n---\n{site_list_str}\n지금 바로 예약하세요!"
                        send_telegram_msg(msg)
                        st.balloons()
                        # 성공 시에도 정지하지 않고 계속 감시하려면 아래 한 줄을 주석 처리하세요.
                        # st.session_state.run = False
                        # break
                    else:
                        status(f"😴 {target_date}일 현재 빈자리 없음 (재시도 대기)")
            except Exception as e:
                status(f"⚠️ 탐색 중 오류: {e}")

            time.sleep(60) # 1분마다 재확인
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 에러: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
