import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import requests
import shutil
import os
from datetime import datetime

# [환경 설정] 서버 시간대 서울 맞춤
os.environ['TZ'] = 'Asia/Seoul'

# [설정] 안태희 님 텔레그램 연동 정보
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    try: requests.get(url, params=params)
    except: pass

st.set_page_config(page_title="울주 캠핑 비서 Pro", page_icon="🏕️")
st.title("🏕️ 울주 캠핑 최종 정밀 감시")

# 감시할 날짜 입력
target_date = st.text_input("감시할 날짜 입력 (예: 29)", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 최종 감시 시작"):
        st.session_state.run = True
        send_telegram_msg(f"🚨 [정밀 감시] {target_date}일 달빛야영장 추적을 시작합니다.") 
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
            
            # 1. 예약 시스템(iframe) 진입 강화 로직
            status("🔍 예약 시스템(iframe) 탐색 중... (최대 30초 대기)")
            found_frame = False
            for attempt in range(6): # 5초씩 6번 = 총 30초 대기
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for i in range(len(iframes)):
                    driver.switch_to.default_content()
                    try:
                        driver.switch_to.frame(i)
                        # '달빛'이나 '일정' 텍스트가 있으면 성공으로 간주
                        if "달빛" in driver.page_source or "일정" in driver.page_source:
                            status(f"✅ 예약 시스템 진입 성공")
                            found_frame = True
                            break
                    except: continue
                
                if found_frame: break
                status(f"⏳ 시스템 응답 대기 중... ({attempt+1}/6)")
                time.sleep(5)
            
            if not found_frame:
                status("❌ iframe을 찾지 못해 새로고침합니다.")
                driver.refresh()
                continue

            # 2. 구역 및 날짜 선택
            try:
                status("🔘 '달빛야영장' 구역 선택...")
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(3)
                        break

                status(f"📅 {target_date}일 날짜 클릭...")
                dates = driver.find_elements(By.XPATH, f"//*[not(self::script) and text()='{target_date}']")
                if dates:
                    target_btn = dates[-1] 
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", target_btn)
                    
                    status(f"⏳ 데이터 로딩 대기 (15초)...")
                    time.sleep(15) 
                    
                    # 실시간 화면 캡쳐 표시
                    driver.save_screenshot("current_view.png")
                    image_area.image("current_view.png", caption="비서가 현재 보고 있는 화면")
                    
                    # 3. 데이터 추출 (행 전체 텍스트 분석 - image_656e18.png 완벽 대응)
                    status("🔍 표 내용 정밀 수색 중...")
                    rows = driver.find_elements(By.TAG_NAME, "tr")
                    available_sites = []

                    for row in rows:
                        row_text = row.text.replace("\n", " ")
                        # '신청' 글자가 들어있고 '접수'는 없는 행만 선택
                        if "신청" in row_text and "접수" not in row_text:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 2:
                                # 사이트 이름은 2번째 칸(인덱스 1)에 위치
                                site_name = cells[1].text.strip()
                                if site_name:
                                    available_sites.append(site_name)
                    
                    if available_sites:
                        available_sites = sorted(list(set(available_sites)))
                        count = len(available_sites)
                        site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                        
                        msg = f"🔔 [빈자리 발견!]\n📅 날짜: {target_date}일\n✅ 가능수: {count}개\n---\n{site_list_str}\n\n지금 예약하세요!"
                        send_telegram_msg(msg)
                        st.balloons()
                        status(f"🎉 성공! {count}개 사이트 발견.")
                    else:
                        status(f"😴 {target_date}일 현재 '신청' 가능한 구역이 없습니다.")
                else:
                    status(f"❌ {target_date}일 날짜 버튼을 찾지 못했습니다.")
            except Exception as e:
                status(f"⚠️ 탐색 오류: {e}")

            time.sleep(60) 
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 오류: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
