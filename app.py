import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import time
import requests

# [설정] 안태희 님 텔레그램 정보
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.get(url, params=params)
    except:
        pass

# 웹 화면 구성
st.set_page_config(page_title="울주 캠핑 비서", page_icon="🏕️")
st.title("🏕️ 울주 캠핑 예약 비서")
st.write("날짜를 입력하고 감시를 시작하면, 빈자리가 날 때 텔레그램으로 알려드립니다.")

target_date = st.text_input("감시할 날짜 입력 (예: 29)", value="29")

# 상태 관리 변수
if "run" not in st.session_state:
    st.session_state.run = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 감시 시작"):
        st.session_state.run = True
with col2:
    if st.button("🛑 정지"):
        st.session_state.run = False
        st.warning("감시를 중단합니다.")

log_area = st.empty()

# 감시 로직 시작
if st.session_state.run:
    log_area.info(f"🔄 {target_date}일 빈자리 감시를 시작합니다...")
    
    # 서버 전용 크롬 설정 (매우 중요)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # 서버에 설치된 크롬 경로를 자동으로 찾기 위해 webdriver-manager 사용
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        while st.session_state.run:
            # 1. 사이트 접속 및 로그인
            driver.get("https://camping.ulju.ulsan.kr/index.jsp")
            time.sleep(3)
            
            try:
                driver.find_element(By.PARTIAL_LINK_TEXT, "로그인").click()
                time.sleep(3)
                
                inputs = driver.find_elements(By.CLASS_NAME, "inputLogin")
                if len(inputs) >= 2:
                    inputs[0].send_keys("athdream")
                    inputs[1].send_keys("!raul3011o")
                    inputs[1].send_keys(Keys.ENTER)
                    time.sleep(3)
                    try: driver.switch_to.alert.accept()
                    except: pass
            except:
                pass # 이미 로그인된 경우 등 예외 처리

            # 2. 예약 페이지로 이동
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(5)
            
            # 프레임 전환 (예약 시스템이 프레임 안에 있을 경우)
            if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                driver.switch_to.frame(0)

            # 3. 달빛야영장 선택
            rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for rb in rbs:
                label_text = rb.find_element(By.XPATH, "./..").text
                if "달빛" in label_text:
                    driver.execute_script("arguments[0].click();", rb)
                    time.sleep(2)
                    try: driver.switch_to.alert.accept()
                    except: pass
                    break

            # 4. 날짜 선택
            dates = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
            if dates:
                driver.execute_script("arguments[0].click();", dates[-1])
                time.sleep(3)

                # 5. 신청 버튼 확인
                # '신청' 텍스트를 포함한 버튼이나 링크 찾기
                apply_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '신청')]")
                active_list = [el for el in apply_elements if el.is_displayed()]
                
                if len(active_list) > 0:
                    msg = f"🔔 [빈자리 알림!]\n울주 캠핑장 {target_date}일 자리가 생겼습니다!\n지금 바로 접속하세요!"
                    send_telegram_msg(msg)
                    st.balloons()
                    log_area.success("🎉 빈자리를 찾았습니다! 텔레그램을 확인하세요.")
                    st.session_state.run = False
                    break
                else:
                    log_area.write(f"[{time.strftime('%H:%M:%S')}] {target_date}일 확인 결과: 빈자리 없음")
            
            # 부하 방지를 위해 1분 대기
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        st.error(f"⚠️ 오류가 발생했습니다: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals():
            driver.quit()
