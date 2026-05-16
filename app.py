import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
import shutil
import os

# [설정] 안태희 님 정보 고정
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
    log_area.info(f"🔄 {target_date}일 상세 감시 중... (사이트명 정밀 수집)")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    try:
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 15)
        
        while st.session_state.run:
            # 1. 메인 접속 및 팝업 닫기
            driver.get("https://camping.ulju.ulsan.kr/index.jsp")
            time.sleep(3)
            try: driver.switch_to.alert.accept()
            except: pass

            # 2. 로그인 수행
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

            # 3. 예약 페이지 이동
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            time.sleep(5)
            try: driver.switch_to.alert.accept()
            except: pass
            
            status_ok = False
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for idx, frame in enumerate(iframes):
                driver.switch_to.default_content()
                try:
                    driver.switch_to.frame(idx)
                    if "달빛" in driver.page_source:
                        status_ok = True
                        break
                except: continue
            
            if not status_ok:
                log_area.warning("⚠️ 예약창 진입 지연... 대기 후 새로고침합니다.")
                time.sleep(10)
                driver.refresh()
                continue

            # 4. 야영장(달빛) 선택
            rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for rb in rbs:
                if "달빛" in rb.find_element(By.XPATH, "./..").text:
                    driver.execute_script("arguments[0].click();", rb)
                    time.sleep(4)
                    try: driver.switch_to.alert.accept()
                    except: pass
                    break

            # 5. 날짜 타격
            date_xpath = (
                f"//td[not(contains(@class,'prev')) "
                f"and not(contains(@class,'next'))]"
                f"//a[text()='{target_date}']"
            )
            
            try:
                target_btn = wait.until(EC.element_to_be_clickable((By.XPATH, date_xpath)))
                driver.execute_script("arguments[0].click();", target_btn)
                time.sleep(8)
            except:
                log_area.warning(f"⚠️ {target_date}일 버튼 로딩 지연. 다음 바퀴를 노립니다.")
                time.sleep(10)
                driver.refresh()
                continue
                
            # 6. 상세 정보 수집 ([핵심 오버홀] 시설종류 대신 진짜 '사이트명' 칸만 콕 집어 수집)
            available_sites = []
            # 예약 현황 칸에 '접수중' 글자가 있는 행(tr)들을 수색
            rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '접수중')]]")
            
            for row in rows:
                try:
                    # 행 내부에서 2번째 td(즉, 사이트명이 적힌 칸)의 텍스트만 정확하게 추출합니다.
                    site_name_element = row.find_element(By.XPATH, "./td[2]")
                    site_info = site_name_element.text.strip()
                    if site_info:
                        available_sites.append(site_info)
                except:
                    continue
            
            if available_sites:
                site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                msg = (f"🔔 [빈자리 발견! - 접수중]\n📅 날짜: {target_date}일\n"
                       f"✅ 가능 구역 수: {len(available_sites)}개\n"
                       f"------------------\n"
                       f"{site_list_str}\n"
                       f"------------------\n"
                       f"태희 님, 지금 즉시 예약 버튼을 누르세요!")
                
                send_telegram_msg(msg)
                st.balloons()
                log_area.success(f"🎉 {len(available_sites)}개 빈자리({site_list_str}) 발견 및 텔레그램 발송 완료!")
                st.session_state.run = False
                break
            
            log_area.write(f"[{time.strftime('%H:%M:%S')}] {target_date}일 달빛야영장 순찰 중... 전부 매진 상태")
            time.sleep(120)
            driver.refresh()

    except Exception as e:
        st.error(f"⚠️ 시스템 오류 발생: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals():
            driver.quit()
