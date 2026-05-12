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
        wait = WebDriverWait(driver, 15) # 최대 15초까지 기다리는 타이머
        
        while st.session_state.run:
            log_area.info("🌐 사이트 접속 중...")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(5)
            
            # 모든 팝업 무조건 제거
            try:
                for _ in range(3):
                    driver.switch_to.alert.accept()
                    time.sleep(0.5)
            except: pass

            # 1. 달력 iframe 확인 및 진입
            try:
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
                log_area.info("📥 달력 시스템 진입 성공")
            except:
                log_area.error("❌ 달력을 불러오지 못했습니다. 재시도 중...")
                driver.refresh()
                continue

            # 2. 달빛야영장 라디오 버튼 클릭
            try:
                # 라디오 버튼이 나타날 때까지 대기
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='radio']")))
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(2)
                        break
            except: pass

            # 3. 날짜 클릭 (정밀 타격 및 대기)
            log_area.info(f"📅 {target_date}일 버튼이 뜰 때까지 기다리는 중...")
            try:
                # 29일이라는 글자가 있는 버튼이 뜰 때까지 대기
                date_xpath = f"//a[text()='{target_date}']"
                wait.until(EC.element_to_be_clickable((By.XPATH, date_xpath)))
                
                all_dates = driver.find_elements(By.XPATH, date_xpath)
                
                clicked = False
                for date_btn in all_dates:
                    try:
                        driver.execute_script("arguments[0].click();", date_btn)
                        time.sleep(2)
                        # 클릭 후 '지난 날짜' 팝업 뜨면 닫기
                        try:
                            alert = driver.switch_to.alert
                            alert.accept()
                            continue 
                        except:
                            clicked = True
                            log_area.success(f"✅ {target_date}일 선택 성공!")
                            break
                    except: continue

                if clicked:
                    # 4. 빈자리 데이터 추출
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
                        msg = f"🔔 [빈자리 알림!]\n📅 날짜: {target_date}일\n✅ {len(available_sites)}개 가능\n---\n{site_list_str}"
                        send_telegram_msg(msg)
                        st.balloons()
                        st.session_state.run = False
                        break
                    else:
                        log_area.write(f"[{datetime.now().strftime('%H:%M:%S')}] {target_date}일 빈자리 없음")
                else:
                    log_area.warning(f"⚠️ {target_date}일 버튼 클릭에 실패했습니다.")

            except Exception as e:
                log_area.error(f"❌ 날짜 버튼을 찾을 수 없습니다: {e}")
            
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        if "unexpected alert open" in str(e):
            try: driver.switch_to.alert.accept()
            except: pass
        else:
            st.error(f"⚠️ 시스템 오류: {e}")
            st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
