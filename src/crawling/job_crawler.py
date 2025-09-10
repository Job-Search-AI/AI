import sys
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# 셀레니움을 사용한 HTML 데이터 추출
def crawl_job_html_from_saramin(user_info):
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
                    if index >= 1:
                        return details_html_parts
                    href = item.get('href')
                    list_title = item.get('list_title', "")
                    index = index + 1
                    try:
                        print(f"[{index}/{len(detail_items)}] 상세 페이지 접속: {href}")
                        driver.get(href)
                        try:
                            time.sleep(3)
                            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".wrap_jview > section:first-of-type")))
                        except:
                            print("첫 번째 section 로딩 대기 시간 초과")
                            time.sleep(2)

                        try:
                            # 상세 제목 추출 후 목록 제목과 일치 여부 확인
                            detail_title_text = ""
                            try:
                                title_el = driver.find_element(By.CSS_SELECTOR, ".wrap_jview .wrap_jv_cont h1.tit_job")
                                detail_title_text = title_el.text.strip()
                            except Exception as e:
                                print(f"상세 제목 추출 실패: {e}")

                            # 일치 여부 판단 (공백 정규화 최소화)
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
                                # 첫 섹션 컨텍스트에서 필요한 요소만 선별 추출
                                first_section = driver.find_element(By.CSS_SELECTOR, ".wrap_jview > section:first-of-type")

                                # 1) 공고 제목 (first_section 내부 한정)
                                title_outer_html = ""
                                try:
                                    title_el = first_section.find_element(By.CSS_SELECTOR, ".wrap_jv_cont h1.tit_job")
                                    title_outer_html = title_el.get_attribute('outerHTML')
                                except Exception as e_title:
                                    print(f"제목 요소 추출 실패: {e_title}")

                                # 2) 요약 영역 (경력, 학력, 근무형태, 급여, 근무지역) - first_section 내부 한정
                                summary_outer_html = ""
                                try:
                                    summary_el = first_section.find_element(By.CSS_SELECTOR, ".wrap_jv_cont div.jv_cont.jv_summary")
                                    summary_outer_html = summary_el.get_attribute('outerHTML')
                                except Exception as e_summary:
                                    print(f"요약 요소 추출 실패: {e_summary}")

                                # 3) 상세 영역 (iframe이 있을 수도 있고 없을 수도 있음) - first_section 내부 한정
                                detail_inner_html = ""
                                try:
                                    detail_container = first_section.find_element(By.CSS_SELECTOR, ".wrap_jv_cont .jv_cont.jv_detail")
                                except Exception:
                                    try:
                                        # first_section 하위 상대 선택자로 재시도 (일부 페이지에서 루트 포함 셀렉터가 실패할 수 있음)
                                        detail_container = first_section.find_element(By.CSS_SELECTOR, ".jv_cont.jv_detail")
                                    except Exception as e_detail_container:
                                        print(f"상세 컨테이너 탐색 실패: {e_detail_container}")
                                        detail_container = None

                                if detail_container is not None:
                                    try:
                                        iframe_elements = detail_container.find_elements(By.TAG_NAME, "iframe")
                                        if iframe_elements:
                                            iframe_el = iframe_elements[0]
                                            try:
                                                driver.switch_to.frame(iframe_el)
                                                time.sleep(1)
                                                detail_inner_text = driver.find_element(By.TAG_NAME, "body").text

                                            finally:
                                                driver.switch_to.default_content()
                                        else:
                                            # iframe이 없으면 내부 요소 전체 추출
                                            detail_inner_text = detail_container.text

                                    except Exception as e_detail:
                                        print(f"상세 내용 추출 실패: {e_detail}")

                                # 원하는 요소들만 결합하여 반환
                                combined_html = "".join([
                                    title_outer_html or "", 
                                    "\n",
                                    summary_outer_html or "",
                                    "\n",
                                    f'<div class="detail">{detail_inner_text}</div>'
                                ])

                                details_html_parts.append(combined_html)
                                return details_html_parts
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
        "cat_kewd": "84", # 직무 코드
        "keydownAccess": "", # 검색 키워드
        "loc_mcd": "101000", # 지역 코드
        "exp_cd": "1", # 경력 코드
        "exp_none": "y", # 경력 무관
        "edu_none": "y", # 학력 무관
        "edu_min": "6", # 학력 최소
        "edu_max": "9", # 학력 최대
        "search_done": "y", # 검색 완료
    }

    # 사람인 채용 정보 html 추출
    html_content = crawl_job_html_from_saramin(user_info)
    print(html_content)