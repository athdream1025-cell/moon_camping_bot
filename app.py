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
        wait = WebDriverWait(driver, 20) # 대기 시간을 20초로 더 늘렸습니다.
        
        while st.session_state.run:
            status("🌐 예약 페이지 직접 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(5)
            
            # 1. 화면을 가리는 모든 알림창/팝업 닫기
            try:
                for _ in range(5):
                    driver.switch_to.alert.accept()
                    status("⚠️ 상단 알림창을 확인하고 닫았습니다.")
                    time.sleep(1)
            except: pass

            # 2. 달력 iframe 확인 및 강제 진입
            status("📥 달력 시스템을 찾는 중...")
            try:
                # iframe이 로딩될 때까지 대기
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                
                # 첫 번째 iframe으로 진입
                driver.switch_to.frame(0)
                status("✅ 달력 시스템 진입 성공!")
            except:
                status("❌ 달력 프레임을 찾지 못해 새로고침합니다.")
                driver.refresh()
                continue

            # 3. 달빛야영장 선택
            try:
                status("🏕️ 달빛야영장 구역 선택 중...")
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='radio']")))
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(2)
                        break
            except: pass

            # 4. 날짜 클릭
            status(f"📅 {target_date}일 날짜를 정밀 타격 중...")
            try:
                date_xpath = f"//a[text()='{target_date}']"
                wait.until(EC.element_to_be_clickable((By.XPATH, date_xpath)))
                date_btn = driver.find_elements(By.XPATH, date_xpath)[-1] # 가장 최신 날짜
                driver.execute_script("arguments[0].click();", date_btn)
                time.sleep(3)
                
                # 클릭 후 "지난 날짜" 팝업 대응
                try:
                    alert = driver.switch_to.alert
                    status(f"⚠️ 사이트 경고: {alert.text}")
                    alert.accept()
                    driver.refresh()
                    continue
                except: pass

                # 5. 빈자리 데이터 추출
                rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '신청')]]")
                available_sites = []
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 3:
                        name = next((c.text.strip() for c in cells if "달빛" in c.text and "야영장" not in c.text), cells[2].text.strip())
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
            except Exception as e:
                status(f"❌ 날짜 버튼 클릭 실패: {e}")
            
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 시스템 오류 발생: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
