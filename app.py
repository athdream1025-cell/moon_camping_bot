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
st.title("🏕️ 울주 캠핑 최종 점검")

target_date = st.text_input("감시할 날짜 입력 (예: 29)", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 최종 감시 시작"):
        st.session_state.run = True
        send_telegram_msg(f"🚨 [최종 점검] {target_date}일 정밀 감시를 개시합니다.") 
with col2:
    if st.button("🛑 정지"):
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
    options.add_argument("--window-size=1920,2000")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path: options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            status("🌐 사이트 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(8)
            
            # 1. 프레임 진입
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i in range(len(iframes)):
                driver.switch_to.default_content()
                try:
                    driver.switch_to.frame(i)
                    if "달빛" in driver.page_source:
                        status(f"✅ {i+1}번 내부 시설(달력) 진입 성공")
                        break
                except: continue

            # 2. 구역 및 날짜 클릭
            try:
                status("🔘 '달빛야영장' 선택 중...")
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(3)
                        break

                status(f"📅 {target_date}일 버튼 클릭...")
                dates = driver.find_elements(By.XPATH, f"//*[not(self::script) and text()='{target_date}']")
                if dates:
                    target_btn = dates[-1]
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", target_btn)
                    
                    status(f"⏳ 데이터 로딩 대기 (15초)...")
                    time.sleep(15) 
                    
                    # 화면 저장 (확인용)
                    driver.save_screenshot("current_view.png")
                    image_area.image("current_view.png", caption="비서가 지금 보고 있는 화면")
                    
                    # 3. 데이터 추출 (스크린샷 구조 기반 정밀 추출)
                    status("🔍 실시간 표 분석 중...")
                    rows = driver.find_elements(By.XPATH, "//tr[contains(., '신청')]")
                    available_sites = []

                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 3:
                            # 2번째 칸: 사이트 이름, 3번째 칸: 신청 버튼
                            site_name = cells[1].text.strip()
                            status_text = cells[2].text.strip()
                            
                            if "신청" in status_text:
                                available_sites.append(site_name)
                    
                    if available_sites:
                        available_sites = sorted(list(set(available_sites)))
                        site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                        msg = f"🔔 [빈자리 발견!]\n📅 날짜: {target_date}일\n✅ 가능수: {len(available_sites)}개\n---\n{site_list_str}"
                        send_telegram_msg(msg)
                        st.balloons()
                    else:
                        status(f"😴 {target_date}일 현재 예약 가능한 자리가 없습니다.")
                else:
                    status(f"❌ {target_date}일 날짜 버튼을 못 찾았습니다.")
            except Exception as e:
                status(f"⚠️ 탐색 오류: {e}")

            time.sleep(60) 
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 오류: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
