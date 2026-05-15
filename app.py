import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import requests
import shutil
import os
from datetime import datetime

# =========================
# 환경설정
# =========================
os.environ['TZ'] = 'Asia/Seoul'

TELEGRAM_TOKEN = "8739300740:AAH7xfPuMW8cdnDdzC48VpvQv68jgoJzSGY"
CHAT_ID = "529787781"
BOOKING_URL = "https://camping.ulju.ulsan.kr/ujcamping/campsite/booking"

# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="울주 캠핑 감시기", page_icon="🏕️")
st.title("🏕️ 울주 캠핑 예약 감시기 (정밀 동기화)")

target_date = st.text_input("감시 날짜", value="29")

if "run" not in st.session_state:
    st.session_state.run = False
if "alerted" not in st.session_state:
    st.session_state.alerted = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 감시 시작"):
        st.session_state.run = True
with col2:
    if st.button("🛑 중단"):
        st.session_state.run = False

log_area = st.empty()
image_area = st.empty()

def status(msg):
    now = datetime.now().strftime('%H:%M:%S')
    log_area.info(f"[{now}] {msg}")

def telegram_message(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        status(f"텔레그램 메시지 실패: {e}")

def telegram_photo(path, caption=""):
    try:
        with open(path, "rb") as photo:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": photo}, timeout=20)
    except Exception as e:
        status(f"텔레그램 사진 실패: {e}")

def take_shot(driver, name):
    filename = f"{name}.png"
    try:
        driver.save_screenshot(filename)
        image_area.image(filename, caption=name)
        telegram_photo(filename, f"📸 {name}")
    except Exception as e:
        status(f"스크린샷 실패: {e}")

def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1400,2200")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver

# [수정] iframe 진입 체크 강화
def enter_booking_iframe(driver):
    status("🔍 iframe 탐색 및 예약 데이터 로딩 대기...")
    for attempt in range(15):
        driver.switch_to.default_content()
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        
        for idx, frame in enumerate(iframes):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                
                # 단순히 달력 클래스뿐만 아니라 구역 선택 ID까지 같이 준비되었는지 체크
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.ID, "site_gubun_01"))
                )
                status(f"✅ iframe 및 구역 제어반 진입 성공 ({idx})")
                return True
            except:
                continue
        time.sleep(2)
    return False

# =========================
# 메인 감시 루프
# =========================
if st.session_state.run:
    while st.session_state.run:
        driver = None
        try:
            driver = create_driver()
            wait = WebDriverWait(driver, 20) # 30초에서 20초로 최적화

            status("🌐 메인 페이지 접속")
            driver.get(BOOKING_URL)
            time.sleep(5)

            status("🔑 예약 시스템 강제 진입 (fn_move_page)")
            driver.execute_script("fn_move_page('01');")
            time.sleep(8)

            # iframe 진입
            ok = enter_booking_iframe(driver)
            if not ok:
                status("❌ iframe 진입 실패")
                take_shot(driver, "iframe_fail")
                driver.quit()
                time.sleep(60)
                continue

            take_shot(driver, "iframe_success")

            # 구역 선택
            status("🏕️ '달빛야영장' 구역 버튼 클릭 시도")
            zone_btn = wait.until(EC.element_to_be_clickable((By.ID, "site_gubun_01")))
            driver.execute_script("arguments[0].click();", zone_btn)
            
            # [핵심 수리] 구역을 선택하면 달력이 새로고침되므로, 
            # 새롭게 바뀐 달력과 날짜 버튼이 완전히 클릭 가능해질 때까지 '정밀 대기'를 걸어줍니다.
            status("⏳ 구역 변경에 따른 달력 새로고침 대기 중...")
            time.sleep(5) 

            # 날짜 클릭
            status(f"🎯 이번 달 {target_date}일 정밀 타격 시도")
            date_xpath = (
                f"//td[not(contains(@class,'prev_month')) "
                f"and not(contains(@class,'next_month')) "
                f"and not(contains(@class,'other_month'))]"
                f"//a[text()='{target_date}']"
            )

            # 완벽하게 로딩되어 클릭 가능할 때까지 대기 후 조작
            target_btn = wait.until(EC.element_to_be_clickable((By.XPATH, date_xpath)))
            driver.execute_script("arguments[0].click();", target_btn)

            status("📋 예약 현황 최종 판독 대기 (10초)")
            time.sleep(10)
            take_shot(driver, "date_clicked")

            # 신청 버튼 검사
            apply_buttons = driver.find_elements(By.XPATH, "//a[contains(text(),'신청')]")
            count = len(apply_buttons)
            status(f"📈 현재 예약 신청 가능 구역 수: {count}개")

            if count > 0:
                status("🎉 [필승] 빈자리 감지 완료!")
                take_shot(driver, "SUCCESS_OPEN")
                if not st.session_state.alerted:
                    telegram_message(f"🔔 [대박] 울주 캠핑 달빛야영장 {target_date}일 빈자리 뚫렸습니다! 즉시 접속하세요!")
                    st.session_state.alerted = True
                    st.balloons()
            else:
                status("😴 모든 자리가 매진 상태입니다.")
                st.session_state.alerted = False

        except TimeoutException:
            status("⏰ 사이트 로딩 타임아웃 (서버 응답 지연)")
            if driver:
                take_shot(driver, "timeout_report")
        except Exception as e:
            status(f"⚠️ 시스템 내부 에러 발생: {e}")
            if driver:
                take_shot(driver, "error_report")
        finally:
            try:
                if driver:
                    driver.quit()
            except:
                pass

        # 다음 순찰
        status("💤 3분간 대기 후 다음 교대 순찰을 시작합니다.")
        for i in range(180):
            if not st.session_state.run:
                break
            time.sleep(1)
