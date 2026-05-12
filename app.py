import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import time
import requests

# [설정] 텔레그램 정보
TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    try: requests.get(url, params=params)
    except: pass

st.set_page_config(page_title="울주 캠핑 비서", page_icon="🏕️")
st.title("🏕️ 울주 캠핑 예약 비서 (웹 버전)")

target_date = st.text_input("감시할 날짜 입력 (예: 29)", value="29")

if st.button("🚀 감시 시작"):
    st.info(f"{target_date}일 빈자리 감시를 시작합니다. 자리가 나면 텔레그램으로 알려드려요!")
    
    # 서버용 크롬 설정
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")  # 추가
    # 서버 환경에 따라 크롬 경로를 강제로 지정 (필요 시)
    options.binary_location = "/usr/bin/chromium-browser"
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        while True:
            # 1. 로그인 및 페이지 이동 로직 (이전 코드와 동일)
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            # ... (로그인 및 체크 로직 수행) ...
            
            # 임시 확인용 로그
            st.write(f"[{time.strftime('%H:%M:%S')}] 확인 중...")
            time.sleep(60)
    except Exception as e:
        st.error(f"오류: {e}")
    finally:
        driver.quit()
