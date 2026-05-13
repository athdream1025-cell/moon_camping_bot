import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import requests
import shutil
import os
from datetime import datetime

# [환경 설정] 서버 시간 맞춤
os.environ['TZ'] = 'Asia/Seoul'

# [설정] 안태희 님 정보 (텔레그램 연동)
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    try: requests.get(url, params=params)
    except: pass

st.set_page_config(page_title="울주 캠핑 비서 Pro", page_icon="🏕️")
st.title("🏕️ 울주 캠핑 최종 감시 모드")

# 감시할 날짜 입력 (기본값 29)
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
image_area = st.empty() # 비서가 보는 화면 실시간 출력용

def status(msg):
    log_area.info(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] {msg}")

if st.session_state.run:
    options = Options()
    options.add_argument("--headless") # 서버 구동을 위해 헤드리스 모드 유지
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,2000") # 화면을 길게 찍어서 표 전체 확인
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path: options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            status("🌐 사이트 접속 시도 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(8)
            
            # 1. 예약 달력이 포함된 iframe 진입
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            found_frame = False
            for i in range(len(iframes)):
                driver.switch_to.default_content()
                try:
                    driver.switch_to.frame(i)
                    if "달빛" in driver.page_source:
                        status(f"✅ 예약 시스템 진입 성공")
                        found_frame = True
                        break
                except: continue
            
            if not found_frame:
                status("❌ 예약 시스템(iframe)을 찾지 못했습니다. 재시도합니다.")
                time.sleep(10)
                continue

            # 2. 구역(달빛야영장) 및 날짜 선택
            try:
                # '작천정달빛야영장' 라디오 버튼 클릭
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(3)
                        break

                # 지정된 날짜 버튼 클릭
                dates = driver.find_elements(By.XPATH, f"//*[not(self::script) and text()='{target_date}']")
                if dates:
                    target_btn = dates[-1] # 이번 달 날짜 선택
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", target_btn)
                    
                    status(f"⏳ {target_date}일 데이터 로딩 대기 (15초)...")
                    time.sleep(15) 
                    
                    # 현재 비서가 보고 있는 화면 캡쳐 및 Streamlit 표시
                    driver.save_screenshot("current_view.png")
                    image_area.image("current_view.png", caption="비서가 현재 보고 있는 예약 현황 화면")
                    
                    # 3. 데이터 추출 (행 전체 텍스트 분석법)
                    status("🔍 표 내용 정밀 분석 중...")
                    rows = driver.find_elements(By.TAG_NAME, "tr")
                    available_sites = []

                    for row in rows:
                        row_text = row.text.replace("\n", " ")
                        # '신청' 글자가 있고 '접수'는 없는 행만 필터링
                        if "신청" in row_text and "접수" not in row_text:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 2:
                                # 스크린샷 기준 2번째 칸에 사이트 이름 존재
                                site_name = cells[1].text.strip()
                                if site_name:
                                    available_sites.append(site_name)
                    
                    if available_sites:
                        available_sites = sorted(list(set(available_sites)))
                        count = len(available_sites)
                        site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                        
                        msg = f"🔔 [빈자리 발견!]\n📅 날짜: {target_date}일\n✅ 가능수: {count}개\n---\n{site_list_str}\n\n지금 바로 예약하세요!"
                        send_telegram_msg(msg)
                        st.balloons()
                        status(f"🎉 성공! {count}개 사이트 알림 발송 완료.")
                    else:
                        status(f"😴 {target_date}일 현재 예약 가능한 '신청' 버튼이 없습니다.")
                else:
                    status(f"❌ {target_date}일 날짜 버튼을 찾지 못했습니다.")
            except Exception as e:
                status(f"⚠️ 탐색 중 오류 발생: {e}")

            # 1분 간격으로 새로고침 및 재수색
            time.sleep(60) 
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 오류: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
