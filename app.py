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

# [UI 튜닝] 월 선택 스위치와 날짜 입력칸 배치
month_option = st.radio("감시할 월 선택", ["이번 달", "다음 달 (6월)"], horizontal=True)
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
    log_area.info(f"🔄 [{month_option}] {target_date}일 상세 감시 중... (팝업 자동 대응)")
    
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
            
            if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                driver.switch_to.frame(0)

            # 4. 야영장(달빛) 선택
            rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for rb in rbs:
                if "달빛" in rb.find_element(By.XPATH, "./..").text:
                    driver.execute_script("arguments[0].click();", rb)
                    time.sleep(2)
                    try: driver.switch_to.alert.accept()
                    except: pass
                    break

            # [새 부품] 5. 화면에서 '다음 달'을 선택했을 경우, 달력의 다음 달 버튼(>) 클릭
            if month_option == "다음 달 (6월)":
                try:
                    # 울주캠핑장 달력의 다음달 이동 버튼 클래스(datepicker-next 등)를 찾아 클릭
                    next_month_btn = driver.find_element(By.XPATH, "//a[contains(@class, 'ui-datepicker-next')]")
                    driver.execute_script("arguments[0].click();", next_month_btn)
                    time.sleep(2) # 달력 넘어가는 대기 시간
                except:
                    # 만약 위 코드가 안 먹힐 경우를 대비한 2선 방어용 텍스트 매칭
                    try:
                        next_month_btn = driver.find_element(By.XPATH, "//a[span[contains(text(), '다음달')]]")
                        driver.execute_script("arguments[0].click();", next_month_btn)
                        time.sleep(2)
                    except: pass

            # 6. 날짜 선택
            dates = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
            if dates:
                driver.execute_script("arguments[0].click();", dates[-1])
                time.sleep(3)
                
                # 7. 상세 정보 수집 (사이트명 정밀 추출 순정 버전)
                available_sites = []
                rows = driver.find_elements(By.XPATH, "//tr[descendant::*[contains(text(), '접수중')]]")
                
                for row in rows:
                    try:
                        site_name_element = row.find_element(By.XPATH, "./td[2]")
                        site_info = site_name_element.text.strip()
                        if site_info:
                            available_sites.append(site_info)
                    except: continue
                
                if available_sites:
                    site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                    msg = (f"🔔 [빈자리 알림!]\n📅 날짜: {month_option} {target_date}일\n"
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
            
            log_area.write(f"[{time.strftime('%H:%M:%S')}] {month_option} {target_date}일 체크 중... 아직 없음")
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        st.error(f"⚠️ 오류 발생: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals():
            driver.quit()
