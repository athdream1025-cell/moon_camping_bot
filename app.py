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
    # 비서의 눈(화면 크기)을 1024px 이하로 고정해서 태희 님이 찾은 코드가 작동하게 합니다.
    options.add_argument("--window-size=1000,1000")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            status("🌐 예약 페이지 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(7)
            
            # 팝업 제거
            try:
                for _ in range(3):
                    driver.switch_to.alert.accept()
                    time.sleep(0.5)
            except: pass

            # 1. 달력 iframe 진입
            try:
                if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                    driver.switch_to.frame(0)
                    status("✅ 달력 시스템 진입 성공!")
                else:
                    status("❌ 달력을 찾지 못했습니다. 재접속 중...")
                    driver.refresh()
                    continue
            except: continue

            # 2. 구역 선택 (달빛야영장)
            try:
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(2)
                        break
            except: pass

            # 3. [수정 포인트] 태희 님이 찾으신 p.day 태그를 직접 타격
            status(f"📅 {target_date}일 날짜(p.day) 선택 시도...")
            
            # 태희 님이 주신 경로를 활용한 정밀 탐색
            # 텍스트가 target_date인 p 태그를 찾습니다.
            date_xpath = f"//p[contains(@class, 'day') and text()='{target_date}']"
            date_btns = driver.find_elements(By.XPATH, date_xpath)
            
            if not date_btns:
                # p 태그가 아니면 그 안의 다른 태그일 수 있으므로 범용 탐색
                date_btns = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")

            if date_btns:
                # 달력 이미지 특성상 진짜 날짜는 뒤에 있음
                driver.execute_script("arguments[0].click();", date_btns[-1])
                time.sleep(3)
                
                # 팝업 대응
                try:
                    alert = driver.switch_to.alert
                    alert.accept()
                    status("⚠️ 지난 날짜 팝업 발생. 다음 확인 대기.")
                except:
                    # 4. 빈자리 추출
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
                        msg = f"🔔 [빈자리 알림!]\n📅 날짜: {target_date}일\n✅ {len(available_sites)}개 구역\n---\n{site_list_str}"
                        send_telegram_msg(msg)
                        st.balloons()
                        st.session_state.run = False
                        break
                    else:
                        status(f"😴 {target_date}일 빈자리 없음")
            
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 에러: {e}")
        st.session_state
