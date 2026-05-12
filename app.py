import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 15)
        
        while st.session_state.run:
            status("🌐 예약 페이지 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(5)
            
            # 팝업 제거
            try:
                for _ in range(3):
                    driver.switch_to.alert.accept()
                    time.sleep(0.5)
            except: pass

            # 1. 달력 iframe 진입
            try:
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
                status("✅ 달력 시스템 진입 성공!")
            except:
                driver.refresh()
                continue

            # 2. 구역 선택
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='radio']")))
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(2)
                        break
            except: pass

            # 3. [핵심] 진짜 날짜 골라내기
            status(f"📅 {target_date}일 버튼 찾는 중 (회색 날짜 제외)...")
            
            # 회색 날짜(지난달/다음달)는 보통 'calendar-other-month' 같은 클래스가 붙거나
            # 색상이 흐릿합니다. 여기서는 텍스트가 target_date인 모든 'a' 태그를 찾은 뒤,
            # 지난달 에러를 피하기 위해 리스트의 마지막 요소를 선택하는 전략을 더 강화합니다.
            date_btns = driver.find_elements(By.XPATH, f"//a[text()='{target_date}']")
            
            if date_btns:
                # 울주 달력 특성상 진짜 날짜는 리스트의 마지막에 위치할 확률이 높습니다.
                # 만약 버튼이 여러 개면, '지난 날짜' 에러가 안 나는 녀석을 찾을 때까지 시도합니다.
                success_click = False
                for btn in reversed(date_btns): # 뒤에서부터(최신 날짜부터) 시도
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(2)
                        
                        # 클릭 후 '지난 날짜' 팝업 뜨면 닫고 다음 버튼 시도
                        try:
                            alert = driver.switch_to.alert
                            alert.accept()
                            continue
                        except:
                            success_click = True
                            status(f"🎯 {target_date}일 선택 완료!")
                            break
                    except: continue

                if success_click:
                    # 4. 빈자리 확인
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
                        status(f"😴 {target_date}일 아직 자리가 없네요.")
            
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 오류: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
