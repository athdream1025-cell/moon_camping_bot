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
        wait = WebDriverWait(driver, 20)
        
        while st.session_state.run:
            status("🌐 사이트 접속 중... (모든 장애물 제거 중)")
            driver.get("https://camping.ulju.ulsan.kr/ujcamping/campsite/booking")
            
            # [핵심] 사이트 뜨자마자 모든 Alert 팝업 반복해서 닫기
            for _ in range(10):
                try:
                    driver.switch_to.alert.accept()
                    status("⚠️ 방해되는 알림창을 닫았습니다.")
                    time.sleep(0.5)
                except:
                    break # 더 이상 뜰 팝업이 없으면 탈출

            # 1. 달력 iframe 확인 및 진입 (절대 대기 모드)
            status("📥 달력 프레임 로딩 대기 중...")
            try:
                # iframe이 로딩될 때까지 더 끈질기게 기다림
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                driver.switch_to.frame(0)
                status("✅ 달력 시스템 진입 성공!")
            except:
                status("❌ 달력을 찾지 못했습니다. 다시 접속합니다.")
                driver.refresh()
                time.sleep(5)
                continue

            # 2. 구역 선택
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='radio']")))
                rbs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                for rb in rbs:
                    if "달빛" in rb.find_element(By.XPATH, "./..").text:
                        driver.execute_script("arguments[0].click();", rb)
                        time.sleep(2)
                        break
            except: pass

            # 3. 진짜 날짜 클릭 (뒤에서부터 찾기 - 회색 날짜 방지)
            status(f"📅 {target_date}일 진짜 버튼 타격 중...")
            date_btns = driver.find_elements(By.XPATH, f"//a[text()='{target_date}']")
            
            if date_btns:
                success_click = False
                # 뒤에서부터 누르는 이유: 달력 이미지 상 검은색(진짜) 날짜가 리스트 뒤쪽에 위치함
                for btn in reversed(date_btns):
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(2)
                        try:
                            alert = driver.switch_to.alert
                            alert.accept() # 지난달(회색)이면 팝업 닫고 다음 버튼으로
                            continue
                        except:
                            success_click = True
                            status(f"🎯 {target_date}일 선택 완료!")
                            break
                    except: continue

                if success_click:
                    # 4. 빈자리 확인
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
                        msg = f"🔔 [빈자리 알림!]\n📅 날짜: {target_date}일\n✅ {len(available_sites)}개 구역\n---\n{site_list_str}"
                        send_telegram_msg(msg)
                        st.balloons()
                        st.session_state.run = False
                        break
                    else:
                        status(f"😴 {target_date}일 아직 빈자리가 없네요.")
            
            status("🔄 다음 감시까지 1분 대기 중...")
            time.sleep(60)
            driver.refresh()

    except Exception as e:
        status(f"⚠️ 에러: {e}")
        st.session_state.run = False
    finally:
        if 'driver' in locals(): driver.quit()
