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
        if int(target_date) < today_day:
            st.error(f"⚠️ {target_date}일은 이미 지난 날짜입니다!")
        else:
            st.session_state.run = True
with col2:
    if st.button("🛑 정지"):
        st.session_state.run = False

log_area = st.empty()

if st.session_state.run:
    log_area.info(f"🔄 {target_date}일 로그인 및 팝업 대응 중...")
    
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
            driver.get("https://camping.ulju.ulsan.kr/index.jsp")
            time.sleep(3)
            
            # 초기 팝업 모두 제거
            try:
                while True:
                    driver.switch_to.alert.accept()
                    time.sleep(0.5)
            except: pass

            # 로그인 로직 강화
            try:
                login_btn = driver.find_elements(By.PARTIAL_LINK_TEXT, "로그인")
                if login_btn:
                    login_btn[0].click()
                    time.sleep(2)
                    
                    inputs = driver.find_elements(By.CLASS_NAME, "inputLogin")
                    if len(inputs) >= 2:
                        inputs[0].send_keys("athdream")
                        inputs[1].send_keys("!raul3011o")
                        inputs[1].send_keys(Keys.ENTER)
                        time.sleep(3) # 로그인 처리 대기
                        
                        # [핵심 수정] "정상 로그인되었습니다" 알림창 무한 확인 및 제거
                        try:
                            while True:
                                driver.switch_to.alert.accept()
                                time.sleep(0.5)
                        except: pass
            except: pass

            # 예약 페이지 이동
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(4)
            # 이동 후에도 팝업이 뜨는지 최종 확인
            try:
                while True:
                    driver.switch_to.alert.accept()
                    time.sleep(0.5)
            except: pass
            
            if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                driver.switch_to.frame(0)

            # 야영장 선택 (달빛)
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
                
                # 구역 추출
                available_sites = []
                rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '신청')]]")
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 3:
                        # '달빛' 명칭이 포함된 칸을 찾아 상세 명칭 추출
                        temp_list = [c.text.strip() for c in cells if "달빛" in c.text and "야영장" not in c.text]
                        if temp_list:
                            available_sites.append(temp_list[0])
                        else:
                            name = cells[2].text.strip()
                            if name and "접수" not in name:
                                available_sites.append(name)
                
                if available_sites:
                    available_sites = sorted(list(set(available_sites)))
                    site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                    
                    msg = (f"🔔 [빈자리 알림!]\n📅 날짜: {target_date}일\n"
                           f"✅ 가능수: {len(available_sites)}개\n"
                           f"------------------\n"
                           f"{site_list_str}\n"
                           f"------------------\n"
                           f"지금 바로 예약하세요!")
                    
                    send_telegram_msg(msg)
                    st.balloons()
                    st.session_state.run = False
                    break
            
            log_area.write(f"[{datetime.now().strftime('%H:%M:%S')}] {target_date}일 감시 중... 이상 없음")
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        # 알림창 때문에 발생하는 에러를 한 번 더 걸러줌
        if "unexpected alert open" in str(e):
            try: driver.switch_to.alert.accept()
            except: pass
        else:
            st.error(f"⚠️ 오류: {e}")
            st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
