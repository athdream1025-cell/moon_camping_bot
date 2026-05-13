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
            time.sleep(5)
            
            # 1. 팝업 즉시 처리
            try:
                alert = driver.switch_to.alert
                alert.accept()
                status("ℹ️ 팝업을 닫았습니다.")
            except: pass

            # 2. [핵심 전략 수정] 모든 프레임을 하나씩 다 뒤져서 '달빛' 찾기
            status("🔍 달력 시스템 수색 중...")
            found_door = False
            
            # 메인 페이지에서 먼저 찾아보기
            if "달빛" in driver.page_source:
                status("✅ 메인 페이지에서 직접 발견!")
                found_door = True
            else:
                # iframe들을 하나씩 들어가보며 수색
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for i in range(len(iframes)):
                    driver.switch_to.default_content()
                    try:
                        driver.switch_to.frame(i)
                        if "달빛" in driver.page_source:
                            status(f"✅ {i+1}번 프레임 안에서 달력 발견!")
                            found_door = True
                            break
                    except: continue

            if not found_door:
                status("❌ 여전히 입구를 못 찾았습니다. 재시도 중...")
                driver.refresh()
                time.sleep(3)
                continue

            # 3. 구역 및 날짜 선택 (어제 성공한 그 로직)
            try:
                # 달빛야영장 라디오 버튼
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    parent_text = rb.find_element(By.XPATH, "./..").text
                    if "달빛" in parent_text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(2)
                        break

                status(f"📅 {target_date}일 선택 시도...")
                # 날짜 버튼 클릭 (p.day 혹은 span 등 모든 텍스트 기반 탐색)
                date_btns = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
                if date_btns:
                    driver.execute_script("arguments[0].click();", date_btns[-1])
                    time.sleep(3)
                    
                    # 4. 빈자리 추출 (어제 성공 로직 복원)
                    rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '신청')]]")
                    available_sites = []
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 3:
                            site_name = cells[2].text.strip()
                            if site_name and "접수" not in site_name:
                                available_sites.append(site_name)
                    
                    if available_sites:
                        available_sites = sorted(list(set(available_sites)))
                        site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                        msg = f"🔔 [빈자리 알림!]\n📅 날짜: {target_date}일\n✅ 가능수: {len(available_sites)}개\n---\n{site_list_str}\n지금 바로 예약하세요!"
                        send_telegram_msg(msg)
                        st.balloons()
                        st.session_state.run = False
                        break
                    else:
                        status(f"😴 {target_date}일 빈자리 없음")
            except Exception as e:
                status(f"⚠️ 내부 탐색 중 오류: {e}")

            time.sleep(60)
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 에러: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
