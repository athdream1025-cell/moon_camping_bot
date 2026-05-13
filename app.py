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

# [설정] 안태희 님 텔레그램 연동 정보
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    try: requests.get(url, params=params)
    except: pass

st.set_page_config(page_title="울주 캠핑 비서 Pro", page_icon="🏕️")
st.title("🏕️ 울주 캠핑 필승 감시 모드")

target_date = st.text_input("감시할 날짜 입력 (예: 29)", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 감시 시작 (필승)"):
        st.session_state.run = True
        send_telegram_msg(f"🚨 [최종병기 가동] {target_date}일 달빛야영장 추적을 시작합니다.") 
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
    # 사람처럼 보이게 하는 속성 추가
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path: options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            status("🌐 캠핑장 사이트 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(10) # 초기 로딩 대기 강화
            
            # 1. 예약 시스템(iframe) 진입 - 끈기 있게 1분간 찾기
            status("🔍 예약 시스템 문 두드리는 중... (최대 1분 대기)")
            found_frame = False
            for attempt in range(12): # 5초씩 12번 = 60초
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for i in range(len(iframes)):
                    driver.switch_to.default_content()
                    try:
                        driver.switch_to.frame(i)
                        if "달빛" in driver.page_source or "일정" in driver.page_source:
                            status(f"✅ 입구 진입 성공! ({i+1}번 통로)")
                            found_frame = True
                            break
                    except: continue
                if found_frame: break
                status(f"⏳ 시스템 응답 기다리는 중... ({attempt+1}/12)")
                time.sleep(5)
            
            if not found_frame:
                status("❌ 사이트 응답이 너무 느립니다. 새로고침 후 재도전합니다.")
                driver.refresh()
                continue

            # 2. 구역 및 날짜 선택
            try:
                # 구역 선택
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(3)
                        break

                # 날짜 선택
                dates = driver.find_elements(By.XPATH, f"//*[not(self::script) and text()='{target_date}']")
                if dates:
                    target_btn = dates[-1] 
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
                    time.sleep(2)
                    driver.execute_script("arguments[0].click();", target_btn)
                    
                    status(f"⏳ {target_date}일 표 로딩 대기 (15초)...")
                    time.sleep(15) 
                    
                    # 증거 사진 남기기
                    driver.save_screenshot("current_view.png")
                    image_area.image("current_view.png", caption="비서가 현재 보고 있는 현장 화면")
                    
                    # 3. 데이터 추출 (단순하고 강력한 텍스트 분석)
                    status("🔍 '신청' 버튼 눈으로 확인 중...")
                    rows = driver.find_elements(By.TAG_NAME, "tr")
                    available_sites = []

                    for row in rows:
                        row_text = row.text.replace("\n", " ")
                        # 행에 '신청'이 있고 '접수'가 없으면 무조건 빈자리!
                        if "신청" in row_text and "접수" not in row_text:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 2:
                                site_name = cells[1].text.strip()
                                if site_name: available_sites.append(site_name)
                    
                    if available_sites:
                        available_sites = sorted(list(set(available_sites)))
                        site_list = "\n".join([f"📍 {s}" for s in available_sites])
                        send_telegram_msg(f"🔔 [빈자리 발견!]\n📅 {target_date}일\n✅ 가능수: {len(available_sites)}개\n---\n{site_list}")
                        st.balloons()
                        status(f"🎉 성공! 텔레그램 확인하세요!")
                    else:
                        status(f"😴 {target_date}일 아직 자리가 없거나 로딩 중입니다.")
                else:
                    status(f"❌ {target_date}일 버튼을 찾지 못했습니다.")
            except Exception as e:
                status(f"⚠️ 탐색 오류 발생: {e}")

            time.sleep(60) 
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 오류: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
