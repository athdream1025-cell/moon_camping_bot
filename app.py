# (위쪽 설정 부분은 동일합니다...)

if st.session_state.run:
    log_area.info(f"🔄 {target_date}일 상세 감시 중... (팝업 자동 대응 포함)")
    
    # 크롬 옵션 설정 (이전과 동일)
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
            # 1. 메인 접속
            driver.get("https://camping.ulju.ulsan.kr/index.jsp")
            time.sleep(3)
            
            # [추가] "17시 마감" 같은 갑작스러운 알림창(Alert) 처리
            try:
                alert = driver.switch_to.alert
                alert.accept() # 확인 버튼 클릭
                log_area.warning("⚠️ 안내 팝업창을 닫았습니다.")
            except:
                pass # 알림창이 없으면 그냥 통과

            # 2. 로그인 로직 (이미 로그인되어 있는지 확인하며 진행)
            try:
                login_btn = driver.find_elements(By.PARTIAL_LINK_TEXT, "로그인")
                if login_btn:
                    login_btn[0].click()
                    time.sleep(3)
                    # 알림창이 또 뜰 수 있으므로 한 번 더 체크
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
            
            # 페이지 이동 후에도 알림창이 뜨는지 체크 (17시 마감 안내 등)
            try: driver.switch_to.alert.accept()
            except: pass

            # (이후 구역 선택 및 상세 정보 수집 로직은 동일...)
            # ...
