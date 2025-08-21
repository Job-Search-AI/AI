import sys

sys.path.insert(0, "/content/drive/MyDrive/ai_enginner/job_search/AI/")
sys.path.insert(0, "/content/drive/MyDrive/package")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# 셀레니움을 사용한 HTML 데이터 추출
def crawl_job_html_from_saramin(user_info):
    # Chrome 옵션 설정
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')  # 헤드리스 모드 (브라우저 창 숨김)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36')
    
    # ChromeDriver 자동 설치 및 WebDriver 초기화
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # URL 구성
        base_url = "https://www.saramin.co.kr/zf_user/search"
        query_params = "&".join([f"{key}={value}" for key, value in user_info.items()])
        full_url = f"{base_url}?{query_params}"
        
        print(f"접속 URL: {full_url}")
        
        # 페이지 로드
        driver.get(full_url)
        
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
        
        # 특정 영역만 추출
        try:
            target_elements = driver.find_elements(By.CLASS_NAME, "item_recruit")
            if target_elements:
                # 모든 item_recruit 요소의 HTML을 합치기
                html_parts = []
                for element in target_elements:
                    html_parts.append(element.get_attribute('outerHTML'))
                
                html_content = '\n'.join(html_parts)
                print(f'추출된 영역 HTML 길이: {len(html_content)} 문자')
                print(f'추출된 채용 항목 수: {len(target_elements)}개')
                return html_content
            else:
                print("채용 항목을 찾을 수 없습니다.")
                return ""
        except Exception as e:
            print(f"특정 영역 추출 실패: {e}")
            # 실패 시 전체 페이지 소스 반환
            html_content = driver.page_source
            print('전체 HTML 반환 (길이):', len(html_content))
            return html_content
        
    finally:
        # 브라우저 종료
        driver.quit()

if __name__ == "__main__":
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
    
    # 채용 정보 추출
    # job_data = extract_job_major_info(html_content)

    # print(job_data)
    
    # # 결과 출력
    # print_job_summary(job_data)
    
    # # DataFrame 생성 및 상세 출력
    # df = pd.DataFrame(job_data)
    # print_dataframe_pretty(df)