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
image_area = st.empty() # [추가] 비서가 보는 화면 출력

def status(msg):
    log_area.info(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] {msg}")

if st.session_state.run:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,2000") # 화면을 길게 잡음
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

            # 2. 구역(라디오) 강제 클릭
            try:
                status("🔘 '달빛야영장' 밸브 여는 중...")
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    parent_text = rb.find_element(By.XPATH, "./..").text
                    if "달빛" in parent_text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(3)
                        break

                # 3. 날짜 클릭 (정확히 텍스트가 일치하는 것만)
                status(f"📅 {target_date}일 버튼 조준 중...")
                # 날짜 버튼을 더 구체적으로 탐색 (p.day 혹은 span)
                dates = driver.find_elements(By.XPATH, f"//*[not(self::script) and text()='{target_date}']")
                if dates:
                    # 이번 달 버튼을 확실히 누르기 위해 리스트의 마지막 요소를 선택
                    target_btn = dates[-1]
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", target_btn)
                    
                    status(f"⏳ 데이터 동기화 대기 중 (15초)...")
                    time.sleep(15) # 표가 로딩될 때까지 충분히 대기
                    
                    # [추가] 비서가 보는 화면을 찍어서 태희 님께 보여줌
                    driver.save_screenshot("current_view.png")
                    image_area.image("current_view.png", caption="비서가 지금 보고 있는 화면")
                    
                    # 4. 빈자리 정밀 추출
                    status("🔍 표 내용 분석 중...")
                    # '신청' 글자가 들어간 모든 행(tr) 또는 버튼(a, button) 탐색
                    available_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '신청')]")
                    
                    if len(available_elements) > 0:
                        # 표 전체 텍스트에서 구역명 추출
                        rows = driver.find_elements(By.TAG_NAME, "tr")
                        available_sites = []
                        for row in rows:
                            if "신청" in row.text and "접수" not in row.text:
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) >= 3:
                                    available_sites.append(cells[2].text.strip())
                        
                        if available_sites:
                            available_sites = sorted(list(set(available_sites)))
                            site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                            msg = f"🔔 [빈자리 발견!]\n📅 날짜: {target_date}일\n✅ 가능수: {len(available_sites)}개\n---\n{site_list_str}"
                            send_telegram_msg(msg)
                            st.balloons()
                        else:
                            status(f"ℹ️ '신청' 글자는 있으나 유효 구역을 못 찾음 (재시도)")
                    else:
                        status(f"😴 {target_date}일은 현재 '신청' 버튼이 없습니다.")
                else:
                    status(f"❌ {target_date}일 버튼을 화면에서 못 찾았습니다.")
            except Exception as e:
                status(f"⚠️ 작업 중 돌발 상황: {e}")

            time.sleep(60) 
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 전원 꺼짐: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
