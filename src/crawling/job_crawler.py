import sys
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# 셀레니움을 사용한 HTML 데이터 추출
def crawl_job_html_from_saramin(user_info, max_count=None):
    # Chrome 옵션 설정
    print("셀레니움 초기화 시작...")
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')  # 헤드리스 모드 (브라우저 창 숨김)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36')
    
    # ChromeDriver 자동 설치 및 WebDriver 초기화
    driver = webdriver.Chrome(options=chrome_options)
    print("셀레니움 초기화 완료")
    # 수집된 상세 HTML 조각들을 저장할 리스트 (항상 리스트 반환을 위해 상단에서 초기화)
    details_html_parts = []

    try:
        # URL 구성
        base_url = "https://www.saramin.co.kr/zf_user/search"
        params_list = []
        for key, value in user_info.items():
            params_list.append(f"{key}={value}")
        query_params = "&".join(params_list)
        full_url = f"{base_url}?{query_params}"
        print("페이지 로드 시작...")
        print(f"접속 URL: {full_url}")
        
        # 페이지 로드
        driver.get(full_url)
        print("페이지 로드 완료")
        # 페이지가 완전히 로드될 때까지 대기
        wait = WebDriverWait(driver, 10)
        try:
            # .item_recruit 영역이 로드될 때까지 대기
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "item_recruit")))
            print("채용 정보 영역 로딩 완료")
        except:
            print("채용 정보 영역을 찾을 수 없습니다. 기본 대기 시간을 사용합니다.")
        
        # 추가 대기 시간 (동적 콘텐츠 로딩을 위해)
        time.sleep(3)
        
        try:
            # 공고정보만 추출
            target_elements = driver.find_elements(By.CLASS_NAME, "item_recruit")
            print(f"채용 정보 영역 수: {len(target_elements)}개")
            if target_elements:
                # 상세 링크 및 목록 제목 수집
                detail_items = []  # { 'href': str, 'list_title': str }
                for element in target_elements:
                    try:
                        link_el = element.find_element(By.CSS_SELECTOR, "div.area_job h2 a")
                        href = link_el.get_attribute('href')

                        list_title_text = ""
                        try:
                            span_el = element.find_element(By.CSS_SELECTOR, "h2.job_tit > a > span")
                            list_title_text = span_el.text.strip()
                        except Exception as e:
                            print(f"목록 제목 추출 실패: {e}")

                        if href:
                            detail_items.append({ 'href': href, 'list_title': list_title_text })
                    except Exception as e:
                        print(f"상세 링크 추출 실패: {e}")
                print(f"추출된 상세 링크 수: {len(detail_items)}개")

                # 상세 페이지 접속 및 내용 수집
                index = 0
                for item in detail_items:

                    # 최대 개수 없을시 건너뛰거나, 최대 개수 초과 시 종료
                    if max_count is not None and index > max_count - 1:
                        return details_html_parts
                    href = item.get('href')

                    # 목록 제목 추출
                    list_title = item.get('list_title', "")
                    index = index + 1
                    try:
                        # 상세 페이지 접속
                        print(f"[{index}/{len(detail_items)}] 상세 페이지 접속: {href}")
                        driver.get(href)
                        try:
                            # 첫 번째 section 로딩 대기
                            time.sleep(3)
                            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".wrap_jview > section:first-of-type")))
                        except:
                            print("첫 번째 section 로딩 대기 시간 초과")
                            time.sleep(2)

                        try:
                            # 상세 제목 추출
                            detail_title_text = ""
                            try:
                                title_el = driver.find_element(By.CSS_SELECTOR, ".wrap_jview .wrap_jv_cont h1.tit_job")
                                detail_title_text = title_el.text.strip()
                            except Exception as e:
                                print(f"상세 제목 추출 실패: {e}")

                            # 목록 제목과 일치 여부 판단 (공백 정규화 최소화)
                            is_match = False
                            try:
                                list_title_norm = " ".join(list_title.split())
                                detail_title_norm = " ".join(detail_title_text.split())
                                if list_title_norm and detail_title_norm and list_title_norm == detail_title_norm:
                                    is_match = True
                                    print("상세 제목 일치")
                            except Exception:
                                is_match = False

                            if is_match:
                                # 첫 섹션 컨텍스트에서 원하는 요소들만 결합하여 반환
                                first_section = driver.find_element(By.CSS_SELECTOR, ".wrap_jview > section:first-of-type > div.wrap_jv_cont")

                                # 1) 공고 제목
                                title_outer_html = ""
                                try:
                                    title_el = first_section.find_element(By.CSS_SELECTOR, "h1.tit_job")
                                    title_outer_html = title_el.get_attribute('outerHTML')
                                    print("제목 요소 추출 완료")
                                except Exception as e_title:
                                    print(f"제목 요소 추출 실패: {e_title}")

                                # 2) 요약 영역 (경력, 학력, 근무형태, 급여, 근무지역)
                                summary_outer_html = ""
                                try:
                                    summary_el = first_section.find_element(By.CSS_SELECTOR, "div.jv_cont.jv_summary")
                                    summary_outer_html = summary_el.get_attribute('outerHTML')
                                    print("요약 요소 추출 완료")
                                except Exception as e_summary:
                                    print(f"요약 요소 추출 실패: {e_summary}")

                                # 3) 상세 영역 (iframe이 있을 수도 있고 없을 수도 있음)
                                try:
                                    detail_container = first_section.find_element(By.CSS_SELECTOR, ".jv_cont.jv_detail")
                                except Exception as e_detail_container:
                                    print(f"상세 컨테이너 탐색 실패: {e_detail_container}")
                                    detail_container = None

                                if detail_container is not None:
                                    try:
                                        iframe_elements = detail_container.find_elements(By.TAG_NAME, "iframe")
                                        # iframe이 있으면 첫 번째 iframe 추출
                                        if iframe_elements:
                                            iframe_el = iframe_elements[0]
                                            try:
                                                driver.switch_to.frame(iframe_el)
                                                time.sleep(1)
                                                detail_inner_text = driver.find_element(By.TAG_NAME, "body").text
                                                print("상세 내용 추출 완료")
                                            finally:
                                                driver.switch_to.default_content()
                                        else:
                                            # iframe이 없으면 내부 요소 전체 추출
                                            detail_inner_text = detail_container.text
                                            print("상세 내용 추출 완료")
                                    except Exception as e_detail:
                                        print(f"상세 내용 추출 실패: {e_detail}")
                                
                                # 4) 접수기간 및 방법
                                how_el_html = ""
                                try:
                                    how_el = first_section.find_element(By.CSS_SELECTOR, "div.jv_cont.jv_howto")
                                    how_el_html = how_el.get_attribute('outerHTML')
                                    print("접수기간 및 방법 추출 완료")
                                except Exception as e_how:
                                    print(f"접수기간 및 방법 추출 실패: {e_how}")

                                # 5) 기업정보
                                corp_el_html = ""
                                try:
                                    corp_el = first_section.find_element(By.CSS_SELECTOR, "div.jv_cont.jv_company")
                                    corp_el_html = corp_el.get_attribute('outerHTML')
                                    print("기업정보 추출 완료")
                                except Exception as e_corp:
                                    print(f"기업정보 추출 실패: {e_corp}")
                                
                                # 6) 복리후생
                                benefit_el_html = ""    
                                # 복리후생 버튼 클릭
                                try:
                                    button = first_section.find_element(By.CSS_SELECTOR, "div.jv_cont.jv_benefit button.btn_more_cont")
                                    button.click()
                                    time.sleep(1)  # 클릭 후 DOM 업데이트 대기 (필요 없으면 제거 가능)
                                except Exception as e_benefit_button:
                                    print(f"복리후생 버튼 클릭 실패: {e_benefit_button}")

                                # 복리후생 내용 추출
                                try:
                                    benefit_el = first_section.find_element(By.CSS_SELECTOR, "div.jv_cont.jv_benefit")
                                    benefit_el_html = benefit_el.get_attribute('outerHTML')
                                    print("복리후생 내용 추출 완료")
                                except Exception as e_benefit_content:
                                    print(f"복리후생 내용 추출 실패: {e_benefit_content}")


                                # 7) 근무지 위치
                                location_el_text = ""
                                try:
                                    location_el = first_section.find_element(By.CSS_SELECTOR, "div.jv_cont.jv_location")
                                    location_el_text = location_el.text.strip()
                                    print("근무지 위치 추출 완료")
                                except Exception as e_location:
                                    print(f"근무지 위치 추출 실패: {e_location}")
                                
                                # 8) 지원자 통계
                                applicant_el_html = ""
                                try:
                                    applicant_el = first_section.find_element(By.CSS_SELECTOR, "div.jv_cont.jv_statics")
                                    applicant_el_html = applicant_el.get_attribute('outerHTML')
                                    print("지원자 통계 추출 완료")
                                except Exception as e_applicant:
                                    print(f"지원자 통계 추출 실패: {e_applicant}")

                                # 원하는 요소들만 결합하여 반환
                                combined_html = "".join([
                                    title_outer_html, 
                                    "\n",
                                    summary_outer_html,
                                    "\n",
                                    f'<div class="detail">{detail_inner_text}</div>',
                                    "\n",
                                    how_el_html,
                                    "\n",
                                    corp_el_html,
                                    "\n",
                                    benefit_el_html,
                                    "\n",
                                    location_el_text,
                                    "\n",
                                    applicant_el_html
                                ])

                                details_html_parts.append(combined_html)
                                print(f"공고 {index} 수집 완료")
                            else:
                                print("제목 불일치로 스킵:")
                                print(f"  목록 제목: {list_title}")
                                print(f"  상세 제목: {detail_title_text}")
                        except Exception as e:
                            print(f"첫 번째 section 추출 실패: {e}")
                    except Exception as e:
                        print(f"상세 페이지 처리 실패: {e}")
                
                if len(details_html_parts) > 0:
                    print(f"수집된 상세 공고 수: {len(details_html_parts)}개")
                    return details_html_parts
                else:
                    print("수집된 상세 공고가 없습니다.")
                    return []
            else:
                print("채용 항목을 찾을 수 없습니다.")
                return []
        except Exception as e:
            print(f"목록/상세 처리 중 오류: {e}")
            # 실패 시 수집된 조각이 있으면 그대로, 없으면 빈 리스트 반환
            if len(details_html_parts) > 0:
                print(f"오류 발생 전까지 수집된 상세 공고 수: {len(details_html_parts)}개")
                return details_html_parts
            else:
                print('수집된 데이터가 없어 빈 리스트를 반환합니다.')
                return []
        
    finally:
        # 브라우저 종료
        driver.quit()

if __name__ == "__main__":
    # python -m src.crawling.job_crawler
    print("사람인 채용 정보 추출 시작...")

    # 프론트엔드에서 받은 정보
    user_info = {
        "searchType": "search", # 검색 타입
        "searchword": "AI+%EC%97%94%EC%A7%80%EB%8B%88%EC%96%B4", # 검색 키워드 (AI 엔지니어)
        "loc_mcd": "101000", # 지역 코드
        "edu_min": "6", # 학력 최소
        "edu_max": "9", # 학력 최대
        "edu_none": "y", # 학력 무관
        "company_cd": "0%2C1%2C2%2C3%2C4%2C5%2C6%2C7%2C9%2C10", # 기업 규모 코드
        "exp_cd": "1", # 경력 코드
        "exp_none": "y", # 경력 무관
        "panel_type": "", # 패널 타입
        "search_optional_item": "y", # 선택 검색 항목
        "search_done": "y", # 검색 완료
        "panel_count": "y", # 패널 카운트
        "preview": "y", # 미리보기
    }

    # 사람인 채용 정보 html 추출
    html_content = crawl_job_html_from_saramin(user_info, 3)
    print(html_content)