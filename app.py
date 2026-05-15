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
st.title("🏕️ 울주 캠핑 예약 감시기 (접수중 판독 버전)")

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

def enter_booking_iframe(driver):
    status("🔍 예약창(iframe) 수색 중...")
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for idx, frame in enumerate(iframes):
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame(idx)
            if "달빛" in driver.page_source:
                status(f"✅ 예전 성공 통로 진입 완료! ({idx}번 방)")
                return True
        except:
            continue
    return False

# =========================
# 메인 감시 루프
# =========================
if st.session_state.run:
    while st.session_state.run:
        driver = None
        try:
            driver = create_driver()

            status("🌐 메인 페이지 접속")
            driver.get(BOOKING_URL)
            time.sleep(6)

            status("🔑 예약 시스템 강제 진입 (fn_move_page)")
            driver.execute_script("fn_move_page('01');")
            time.sleep(8)

            # iframe 진입
            ok = enter_booking_iframe(driver)
            if not ok:
                status("❌ 입구 발견 실패. 재접속 시도합니다.")
                driver.quit()
                time.sleep(30)
                continue

            take_shot(driver, "iframe_success")

            # 구역 선택
            status("🏕️ 달빛야영장 구역 고정")
            zone_btn = driver.find_element(By.ID, "site_gubun_01")
            driver.execute_script("arguments[0].click();", zone_btn)
            time.sleep(4)

            # 날짜 클릭
            status(f"🎯 {target_date}일 클릭 시도")
            all_dates = driver.find_elements(By.XPATH, f"//*[text()='{target_date}']")
            
            target_btn = None
            if all_dates:
                target_btn = all_dates[-1]

            if target_btn:
                driver.execute_script("arguments[0].click();", target_btn)
                status("📋 예약 현황판 최종 로딩 (10초 대기)")
                time.sleep(10)
                take_shot(driver, "date_clicked")

                # [핵심 수정] 태희 님 지적사항 반영: '신청' 대신 '접수중' 글자 정밀 감사
                # 화면에 '접수중'이라는 텍스트를 가진 모든 요소를 찾아냅니다.
                apply_buttons = driver.find_elements(By.XPATH, "//*[contains(text(),'접수중')]")
                count = len(apply_buttons)
                status(f"📈 현재 '접수중' 자리 개수: {count}개")

                if count > 0:
                    status("🎉 [대박] 빈자리(접수중) 발견!")
                    take_shot(driver, "SUCCESS_OPEN")
                    if not st.session_state.alerted:
                        telegram_message(f"🔔 울주 캠핑 {target_date}일 [접수중] 자리 발견! 지금 들어가세요!")
                        st.session_state.alerted = True
                        st.balloons()
                else:
                    status("😴 아직 모든 자리가 매진(예약완료) 상태")
                    st.session_state.alerted = False
            else:
                status(f"❌ 달력에서 {target_date}일 버튼을 식별하지 못함")

        except Exception as e:
            status(f"⚠️ 가동 중 오류 발생: {e}")
            if driver:
                take_shot(driver, "error_report")
        finally:
            try:
                if driver:
                    driver.quit()
            except:
                pass

        # 다음 순찰 대기
        status("💤 3분간 대기 후 다음 검사 시작")
        for i in range(180):
            if not st.session_state.run:
                break
            time.sleep(1)
