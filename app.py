```python
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

TELEGRAM_TOKEN = "여기에_토큰"
CHAT_ID = "여기에_CHAT_ID"

BOOKING_URL = "https://camping.ulju.ulsan.kr/ujcamping/campsite/booking"

# =========================
# Streamlit
# =========================

st.set_page_config(page_title="울주 캠핑 감시기", page_icon="🏕️")

st.title("🏕️ 울주 캠핑 예약 감시기")

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

# =========================
# 로그 함수
# =========================

def status(msg):
    now = datetime.now().strftime('%H:%M:%S')
    log_area.info(f"[{now}] {msg}")
    print(msg)

# =========================
# 텔레그램 함수
# =========================

def telegram_message(msg):
    try:
        requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            params={
                "chat_id": CHAT_ID,
                "text": msg
            },
            timeout=10
        )
    except Exception as e:
        status(f"텔레그램 메시지 실패: {e}")

def telegram_photo(path, caption=""):
    try:
        with open(path, "rb") as photo:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption
                },
                files={
                    "photo": photo
                },
                timeout=20
            )
    except Exception as e:
        status(f"텔레그램 사진 실패: {e}")

# =========================
# 스크린샷
# =========================

def take_shot(driver, name):
    filename = f"{name}.png"

    try:
        driver.save_screenshot(filename)

        image_area.image(filename, caption=name)

        telegram_photo(filename, f"📸 {name}")

    except Exception as e:
        status(f"스크린샷 실패: {e}")

# =========================
# 브라우저 생성
# =========================

def create_driver():

    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    options.add_argument("--window-size=1400,2200")

    options.add_argument(
        "user-agent=Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    options.add_experimental_option(
        "excludeSwitches",
        ["enable-automation"]
    )

    options.add_experimental_option(
        'useAutomationExtension',
        False
    )

    chrome_path = (
        shutil.which("chromium")
        or shutil.which("chromium-browser")
    )

    if chrome_path:
        options.binary_location = chrome_path

    driver = webdriver.Chrome(options=options)

    driver.set_page_load_timeout(60)

    return driver

# =========================
# iframe 진입
# =========================

def enter_booking_iframe(driver):

    status("🔍 iframe 탐색 시작")

    for attempt in range(15):

        driver.switch_to.default_content()

        iframes = driver.find_elements(By.TAG_NAME, "iframe")

        status(f"iframe 개수: {len(iframes)}")

        for idx, frame in enumerate(iframes):

            try:
                driver.switch_to.default_content()

                driver.switch_to.frame(frame)

                # 핵심:
                # 달력 요소 등장 자체를 기다림
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "ui-datepicker-calendar")
                    )
                )

                status(f"✅ iframe 진입 성공 ({idx})")

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

            wait = WebDriverWait(driver, 30)

            status("🌐 메인 페이지 접속")

            driver.get(BOOKING_URL)

            time.sleep(5)

            status("🔑 예약 시스템 강제 진입")

            driver.execute_script("fn_move_page('01');")

            time.sleep(8)

            # =====================
            # iframe 진입
            # =====================

            ok = enter_booking_iframe(driver)

            if not ok:

                status("❌ iframe 진입 실패")

                take_shot(driver, "iframe_fail")

                driver.quit()

                time.sleep(60)

                continue

            take_shot(driver, "iframe_success")

            # =====================
            # 구역 버튼
            # =====================

            status("🏕️ 달빛야영장 선택")

            zone_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.ID, "site_gubun_01")
                )
            )

            driver.execute_script(
                "arguments[0].click();",
                zone_btn
            )

            time.sleep(5)

            # =====================
            # 날짜 클릭
            # =====================

            status(f"🎯 {target_date}일 클릭 시도")

            date_xpath = (
                f"//td[not(contains(@class,'prev')) "
                f"and not(contains(@class,'next'))]"
                f"//a[text()='{target_date}']"
            )

            target_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, date_xpath)
                )
            )

            driver.execute_script(
                "arguments[0].click();",
                target_btn
            )

            status("📋 예약 현황 로딩 대기")

            time.sleep(10)

            take_shot(driver, "date_clicked")

            # =====================
            # 신청 버튼 검사
            # =====================

            apply_buttons = driver.find_elements(
                By.XPATH,
                "//a[contains(text(),'신청')]"
            )

            count = len(apply_buttons)

            status(f"예약 가능 버튼 개수: {count}")

            if count > 0:

                status("🎉 빈자리 발견!")

                take_shot(driver, "SUCCESS")

                if not st.session_state.alerted:

                    telegram_message(
                        f"🔔 울주 캠핑 {target_date}일 예약 가능 발견!"
                    )

                    st.session_state.alerted = True

                    st.balloons()

            else:

                status("😴 아직 매진 상태")

                st.session_state.alerted = False

        except TimeoutException:

            status("⏰ 로딩 타임아웃 발생")

            if driver:
                take_shot(driver, "timeout")

        except Exception as e:

            status(f"⚠️ 에러 발생: {e}")

            if driver:
                take_shot(driver, "error")

        finally:

            try:
                if driver:
                    driver.quit()
            except:
                pass

        # =====================
        # 다음 순찰
        # =====================

        status("💤 3분 후 다시 검사")

        for i in range(180):

            if not st.session_state.run:
                break

            time.sleep(1)

```
