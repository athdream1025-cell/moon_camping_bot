import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import requests
import shutil

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

target_date = st.text_input("감시할 날짜 입력 (예: 29)", value="29")

if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 상세 감시 시작"):
        st.session_state.run = True
with col2:
    if st.button("🛑 정지"):
        st.session_state.run = False
        st.warning("감시를 중단합니다.")

log_area = st.empty()

if st.session_state.run:
    log_area.info(f"🔄 {target_date}일 상세 빈자리 감시 중...")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        
        while st.session_state.run:
            # --- 로그인 및 페이지 이동 (생략, 기존과 동일) ---
            driver.get("https://camping.ulju.ulsan.kr/index.jsp")
            time.sleep(2)
            # (로그인 로직 생략... 안태희 님 기존 코드 사용)

            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(4)
            if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                driver.switch_to.frame(0)

            # 달빛야영장 클릭
            rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for rb in rbs:
                if "달빛" in rb.find_element(By.XPATH, "./..").text:
                    driver.execute_script("arguments[0].click();", rb)
                    time.sleep(2)
                    break

            # 날짜 클릭
            dates = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
            if dates:
                driver.execute_script("arguments[0].click();", dates[-1])
                time.sleep(3)
                
                # --- 여기서부터 상세 정보 추출 ---
                available_sites = []
                # '신청' 버튼이 있는 모든 행(tr)을 찾습니다.
                rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '신청')]]")
                
                for row in rows:
                    # 해당 줄에서 야영장 이름(보통 첫 번째나 두 번째 td)을 가져옵니다.
                    site_name = row.text.split('\n')[0] 
                    available_sites.append(site_name)
                
                if available_sites:
                    site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                    msg = (f"🔔 [빈자리 알림!]\n📅 날짜: {target_date}일\n"
                           f"✅ 가능수: {len(available_sites)}개\n"
                           f"------------------\n"
                           f"{site_list_str}\n"
                           f"------------------\n"
                           f"지금 바로 예약하세요!")
                    
                    send_telegram_msg(msg)
                    st.balloons()
                    log_area.success(f"🎉 {len(available_sites)}개 빈자리 발견!")
                    st.session_state.run = False
                    break
            
            log_area.write(f"[{time.strftime('%H:%M:%S')}] {target_date}일 체크 중... 아직 없음")
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        st.error(f"오류: {e}")
    finally:
        if 'driver' in locals(): driver.quit()
