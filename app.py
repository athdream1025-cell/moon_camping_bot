# ... (앞부분 설정 및 접속 로직은 동일) ...

                    # 3. 데이터 추출 (스크린샷 image_657ffe.png 구조 반영)
                    status("🔍 실시간 표 분석 중...")
                    
                    # '신청'이라는 글자가 포함된 행(tr)을 모두 찾습니다.
                    rows = driver.find_elements(By.XPATH, "//tr[contains(., '신청')]")
                    available_sites = []

                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        # 스크린샷 확인 결과: 
                        # cells[0]: 시설종류 / cells[1]: 사이트명 / cells[2]: 예약현황(신청버튼)
                        if len(cells) >= 3:
                            site_name = cells[1].text.strip()  # [교정] 2번째 칸에서 이름 추출
                            status_text = cells[2].text.strip() # 3번째 칸에 '신청' 버튼 확인
                            
                            if "신청" in status_text:
                                available_sites.append(site_name)
                    
                    if available_sites:
                        available_sites = sorted(list(set(available_sites)))
                        site_list_str = "\n".join([f"📍 {site}" for site in available_sites])
                        msg = f"🔔 [빈자리 발견!]\n📅 날짜: {target_date}일\n✅ 가능수: {len(available_sites)}개\n---\n{site_list_str}\n\n지금 바로 예약하세요!"
                        send_telegram_msg(msg)
                        st.balloons()
                        status(f"🎉 {len(available_sites)}개 구역 발견! 알림을 보냈습니다.")
                    else:
                        status(f"😴 {target_date}일 '신청' 가능 자리가 없습니다.")

# ... (뒷부분 생략) ...
