import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import shutil
import os
from datetime import datetime

# =========================
# 환경설정
# =========================
os.environ['TZ'] = 'Asia/Seoul'

BOOKING_URL = "https://camping.ulju.ulsan.kr/ujcamping/campsite/booking"

# =========================
# Streamlit UI
# =========================
st.set_page_config(
    page_title="울주 캠핑 감시기",
    page_icon="🏕️"
)

st.title("🏕️ 울주 캠핑 예약 감시기")

target_date = st.text_input(
    "감시 날짜",
    value="29"
)

if "run" not in st.session_state:
    st.session_state.run = False

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

# =========================
# 스크린샷
# =========================
def take_shot(driver, name):

    filename = f"{name}.png"

    try:

        driver.save_screenshot(filename)

        image_area.image(
            filename,
            caption=name
        )

    except Exception as e:

        status(f"스크린샷 실패: {e}")

# =========================
# 드라이버 생성
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
        "useAutomationExtension",
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

    status("🔍 iframe 탐색 중...")

    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located(
            (By.TAG_NAME, "iframe")
        )
    )

    iframes = driver.find_elements(
        By.TAG_NAME,
        "iframe"
    )

    status(f"iframe 개수: {len(iframes)}")

    for idx in range(len(iframes)):

        try:

            driver.switch_to.default_content()

            driver.switch_to.frame(idx)

            time.sleep(2)

            html = driver.page_source

            if "달빛" in html or "예약" in html:

                status(f"✅ iframe 진입 성공 ({idx}번)")

                return True

        except Exception as e:

            status(f"iframe {idx} 실패: {e}")

    return False

# =========================
# 메인 루프
# =========================
if st.session_state.run:

    while st.session_state.run:

        driver = None

        try:

            driver = create_driver()

            # -------------------------
            # 메인 페이지 접속
            # -------------------------
            status("🌐 메인 페이지 접속")

            driver.get(BOOKING_URL)

            time.sleep(5)

            # -------------------------
            # 예약 시스템 진입
            # -------------------------
            status("🔑 예약 시스템 진입")

            driver.execute_script(
                "fn_move_page('01');"
            )

            time.sleep(5)

            # -------------------------
            # iframe 진입
            # -------------------------
            ok = enter_booking_iframe(driver)

            if not ok:

                status("❌ iframe 진입 실패")

                take_shot(driver, "iframe_fail")

                driver.quit()

                time.sleep(30)

                continue

            take_shot(driver, "iframe_success")

            # -------------------------
            # 달빛야영장 선택
            # -------------------------
            status("🏕️ 달빛야영장 선택")

            zone_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable(
                    (By.ID, "site_gubun_01")
                )
            )

            driver.execute_script(
                "arguments[0].click();",
                zone_btn
            )

            time.sleep(5)

            # -------------------------
            # 날짜 클릭
            # -------------------------
            status(f"🎯 {target_date}일 탐색 중...")

            try:

                day_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            f"//p[contains(@class,'day') and text()='{target_date}']"
                        )
                    )
                )

                # 부모 요소 가져오기
                parent = day_element.find_element(
                    By.XPATH,
                    "./.."
                )

                # 중앙으로 이동
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    parent
                )

                time.sleep(1)

                # 강제 클릭
                driver.execute_script(
                    "arguments[0].click();",
                    parent
                )

                status("✅ 날짜 클릭 완료")

                time.sleep(5)

                take_shot(driver, "date_clicked")

            except Exception as e:

                status(f"❌ 날짜 클릭 실패: {e}")

                take_shot(driver, "date_click_fail")

                driver.quit()

                time.sleep(30)

                continue

            # -------------------------
            # 접수중 탐색
            # -------------------------
            status("🔍 접수중 자리 탐색 중...")

            apply_buttons = driver.find_elements(
                By.XPATH,
                "//*[contains(text(),'접수중')]"
            )

            count = len(apply_buttons)

            status(f"📈 접수중 자리 개수: {count}")

            if count > 0:

                status("🎉 빈자리 발견!")

                take_shot(driver, "SUCCESS_OPEN")

                st.success(
                    f"{target_date}일 접수중 자리 발견!"
                )

                st.balloons()

            else:

                status("😴 아직 매진 상태")

        except TimeoutException:

            status("⏰ 요소 탐색 시간 초과")

            if driver:
                take_shot(driver, "timeout_error")

        except Exception as e:

            status(f"⚠️ 오류 발생: {e}")

            if driver:
                take_shot(driver, "error_report")

        finally:

            try:
                if driver:
                    driver.quit()
            except:
                pass

        # -------------------------
        # 다음 검사 대기
        # -------------------------
        status("💤 3분 대기")

        for i in range(180):

            if not st.session_state.run:
                break

            time.sleep(1)

