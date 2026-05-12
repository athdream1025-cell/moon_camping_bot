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

today_day = datetime.now().day
target_date = st.text_input("감시할 날짜 입력 (예: 29)", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 정밀 감시 시작"):
        st.session_state.run = True
with col2:
    if st.button("🛑 정지"):
        st.session_state.run = False

log_area = st.empty()

def handle_alerts(driver):
    """모든 알림창을 무조건 닫는 함수"""
    try:
        count = 0
        while count < 5: # 최대 5개까지 연속 닫기
            alert = driver.switch_to.alert
            log_area.warning(f"⚠️ 팝업 감지: {alert.text}")
            alert.accept()
            time.sleep(1)
            count += 1
    except:
        pass

if st.session_state.run:
    log_area.info("🔧 브라우저를 실행합니다...")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            # 1. 접속 및 초기 팝업 정리
            log_area.info("🌐 사이트에 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/index.jsp")
            time.sleep(3)
            handle_alerts(driver)

            # 2. 로그인 시도
            log_area.info("🔑 로그인을 시도합니다...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/member/login")
            time.sleep(2)
            
            try:
                inputs = driver.find_elements(By.CLASS_NAME, "inputLogin")
                if len(inputs) >= 2:
                    inputs[0].clear()
                    inputs[0].send_keys("athdream")
                    inputs[1].clear()
                    inputs[1].send_keys("!raul3011o")
                    inputs[1].send_keys(Keys.ENTER)
                    time.sleep(3)
                    
                    # 로그인 성공/실패 팝업 모두 닫기
                    handle_alerts(driver)
                    log_area.success("✅ 로그인 단계 통과!")
            except Exception as e:
                log_area.error(f"로그인 입력 실패: {e}")

            # 3. 예약 페이지로 직접 이동
            log_area.info("📅 예약 페이지로 이동합니다...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(4)
            handle_alerts(driver)
            
            # iframe 체크
            if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                driver.switch_to.frame(0)

            # 4. 야영장 및 날짜 선택
            log_area.info(f"🔎 {target_date}일 빈자리 찾는 중...")
            rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for rb in rbs:
                if "달빛" in rb.find_element(By.XPATH, "./..").text:
                    driver.execute_script("arguments[0].click();", rb)
                    time.sleep(2)
                    break

            dates = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
            if dates:
                driver.execute_script("arguments[0].click();", dates[-1])
                time.sleep(3)
                
                # 상세 정보 수집
                available_sites = []
                rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '신청')]]")
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 3:
                        site_name = next((c.text.strip() for c in cells if "달빛" in c.text and "야영장" not in c.text), cells[2].text.strip())
                        if site_name and "접수" not in site_name:
                            available_sites.append(site_name)
                
                if available_sites:
                    available_sites = sorted(list(set(available_sites)))
                    site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                    
                    msg = (f"🔔 [빈자리 알림!]\n📅 날짜: {target_date}일\n✅ 가능수: {len(available_sites)}개\n"
                           f"------------------\n{site_list_str}\n------------------\n지금 예약하세요!")
                    
                    send_telegram_msg(msg)
                    st.balloons()
                    st.session_state.run = False
                    break
            
            log_area.write(f"[{datetime.now().strftime('%H:%M:%S')}] {target_date}일 감시 중... (정상)")
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        st.error(f"⚠️ 시스템 오류: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
