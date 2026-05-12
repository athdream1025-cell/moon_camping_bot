import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import requests
import shutil
from datetime import datetime

# [설정] 안태희 님 정보
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    try: requests.get(url, params=params)
    except: pass

st.set_page_config(page_title="울주 캠핑 비서 Pro", page_icon="🏕️")
st.title("🏕️ 울주 캠핑 예약 비서 Pro")

# [핵심] 오늘 날짜 확인 (5월 13일 기준)
now = datetime.now()
today_day = now.day

target_date = st.text_input("감시할 날짜 입력 (예: 29)", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 감시 시작"):
        # 지난 날짜 입력 방지 로직
        if int(target_date) < today_day:
            st.error(f"⚠️ {target_date}일은 이미 지난 날짜입니다. 오늘({today_day}일) 이후 날짜를 입력해주세요.")
        else:
            st.session_state.run = True
with col2:
    if st.button("🛑 정지"):
        st.session_state.run = False

log_area = st.empty()

if st.session_state.run:
    log_area.info(f"🔄 {target_date}일 예약 감시를 준비합니다...")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            # 1. 접속 및 모든 팝업(지난 날짜 경고 포함) 무조건 닫기
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(3)
            
            try:
                while True: # 알림창이 안 뜰 때까지 반복해서 닫기
                    driver.switch_to.alert.accept()
                    time.sleep(0.5)
            except: pass

            # 2. 로그인 (생략 가능하면 패스, 필요하면 수행)
            # ... (기존 로그인 로직)

            # 3. 달빛야영장 선택
            if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                driver.switch_to.frame(0)

            rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for rb in rbs:
                if "달빛" in rb.find_element(By.XPATH, "./..").text:
                    driver.execute_script("arguments[0].click();", rb)
                    time.sleep(2)
                    break

            # 4. 날짜 클릭 및 빈자리 체크
            dates = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
            if dates:
                driver.execute_script("arguments[0].click();", dates[-1])
                time.sleep(3)
                
                # '신청' 버튼이 있는 행에서 상세 구역명 추출
                available_sites = []
                rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '신청')]]")
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 3:
                        site_name = cells[2].text.strip()
                        if site_name and "접수" not in site_name:
                            available_sites.append(site_name)
                
                if available_sites:
                    available_sites = sorted(list(set(available_sites)))
                    site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                    msg = f"🔔 [빈자리 알림!]\n📅 날짜: {target_date}일\n✅ 가능수: {len(available_sites)}개\n------------------\n{site_list_str}\n------------------\n예약하세요!"
                    send_telegram_msg(msg)
                    st.session_state.run = False
                    break
            
            log_area.write(f"[{datetime.now().strftime('%H:%M:%S')}] {target_date}일 감시 중...")
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        # 예상치 못한 팝업 에러 발생 시 자동 대응
        if "unexpected alert open" in str(e):
            try: driver.switch_to.alert.accept()
            except: pass
        else:
            st.error(f"⚠️ 오류: {e}")
            st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
