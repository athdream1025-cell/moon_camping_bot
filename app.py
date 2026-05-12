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
    
    # [위장술 강화] 진짜 사람 브라우저처럼 보이게 하는 설정
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        # 봇 감지 우회 스크립트 실행
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })
        
        wait = WebDriverWait(driver, 30) # 대기 시간을 30초로 대폭 늘림
        
        while st.session_state.run:
            status("🌐 사이트 보안 확인 및 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            
            # 1. 팝업 철저 제거
            time.sleep(5)
            try:
                for _ in range(5):
                    driver.switch_to.alert.accept()
                    status("⚠️ 알림창을 닫았습니다.")
                    time.sleep(0.5)
            except: pass

            # 2. 달력 iframe 진입 시도 (더 끈질기게)
            status("📥 달력 데이터를 불러오는 중 (최대 30초 대기)...")
            try:
                # iframe이 나타날 때까지 30초간 뚫어지게 쳐다봅니다.
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                driver.switch_to.frame(0)
                status("✅ 달력 데이터 로딩 성공!")
            except:
                status("❌ 달력 로딩 실패. 사이트 응답이 느립니다. 재시도...")
                driver.refresh()
                continue

            # 3. 달빛야영장 구역 선택
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='radio']")))
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(2)
                        break
            except: pass

            # 4. 진짜 날짜 클릭 (지난달 회색 날짜 방지)
            status(f"📅 {target_date}일 날짜 확정 중...")
            date_btns = driver.find_elements(By.XPATH, f"//a[text()='{target_date}']")
            
            if date_btns:
                success_click = False
                for btn in reversed(date_btns): # 뒤에서부터 클릭 (진짜 날짜 우선)
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(3)
                        try:
                            alert = driver.switch_to.alert
                            alert.accept() # 지난달 날짜면 닫고 다음 후보로
                            continue
                        except:
                            success_click = True
                            status(f"🎯 {target_date}일 선택 완료!")
                            break
                    except: continue

                if success_click:
                    # 5. 빈자리 데이터 추출
                    status("🔍 실시간 빈자리 확인 중...")
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
                        msg = f"🔔 [빈자리 알림!]\n📅 날짜: {target_date}일\n✅ {len(available_sites)}개 가능\n---\n{site_list_str}"
                        send_telegram_msg(msg)
                        st.balloons()
                        st.session_state.run = False
                        break
                    else:
                        status(f"😴 {target_date}일 아직 빈자리가 없네요.")
            
            status("🔄 다음 확인을 위해 1분간 대기합니다.")
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 오류: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
