import streamlit as st
from selenium import webdriver
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
    log_area.info(f"🔄 {target_date}일 상세 구역 감시 중...")
    
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
            driver.get("https://camping.ulju.ulsan.kr/index.jsp")
            time.sleep(3)
            try: driver.switch_to.alert.accept()
            except: pass

            # --- 로그인 및 예약 페이지 이동 (기존과 동일) ---
            try:
                login_btn = driver.find_elements(By.PARTIAL_LINK_TEXT, "로그인")
                if login_btn:
                    login_btn[0].click()
                    time.sleep(3)
                    try: driver.switch_to.alert.accept()
                    except: pass
                    inputs = driver.find_elements(By.CLASS_NAME, "inputLogin")
                    if len(inputs) >= 2:
                        inputs[0].send_keys("athdream")
                        inputs[1].send_keys("!raul3011o")
                        inputs[1].send_keys(Keys.ENTER)
                        time.sleep(3)
                        try: driver.switch_to.alert.accept()
                        except: pass
            except: pass

            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(5)
            try: driver.switch_to.alert.accept()
            except: pass
            
            if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                driver.switch_to.frame(0)

            # 구역(달빛) 및 날짜 선택
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
                
                # --- [수정된 핵심 로직] 구역 상세 명칭 정확히 가져오기 ---
                available_sites = []
                # '신청' 버튼이 포함된 행(tr)들을 모두 찾습니다.
                rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '신청')]]")
                
                for row in rows:
                    # 행 안의 모든 칸(td)을 가져옵니다.
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 3:
                        # 사이트 이름이 있는 정확한 칸(보통 3번째 칸)의 텍스트를 추출합니다.
                        # 웹사이트 구조에 따라 index는 바뀔 수 있습니다. (2 또는 3)
                        site_detail = cells[2].text.strip() 
                        if site_detail:
                            available_sites.append(site_detail)
                
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
                    log_area.success(f"🎉 {len(available_sites)}개 상세 빈자리 발견!")
                    st.session_state.run = False
                    break
            
            log_area.write(f"[{time.strftime('%H:%M:%S')}] {target_date}일 체크 중... 상세 정보 확인 중")
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        st.error(f"⚠️ 오류 발생: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
