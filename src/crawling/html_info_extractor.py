from bs4 import BeautifulSoup
from job_crawler import crawl_job_html_from_saramin
import sys

sys.path.insert(0, "/content/drive/MyDrive/ai_enginner/job_search/AI/")
sys.path.insert(0, "/content/drive/MyDrive/package")
def extract_job_major_info(html_content):
    """
    HTML에서 .item_recruit 클래스를 가진 채용 정보를 추출하는 함수  
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # .item_recruit 클래스를 가진 모든 채용 항목 찾기
    job_items = soup.find_all('div', class_='item_recruit')
    
    if not job_items:
        print("채용 항목을 찾을 수 없습니다.")
        return []
    
    job_data = []
    
    for item in job_items:
        try:
            # 회사명 - corp_name 클래스 사용
            company_element = item.find('div', class_='corp_name')
            company_name = ""
            if company_element:
                company_name = company_element.get_text(strip=True)
            
            # 채용제목 - job_tit 클래스의 a 태그 사용
            job_title_element = item.find('h2', class_='job_tit')
            job_title = ""
            if job_title_element:
                job_title_link = job_title_element.find('a')
                if job_title_link:
                    job_title = job_title_link.get_text(strip=True)
                else:
                    job_title = job_title_element.get_text(strip=True)
            
            # 직무분야 - job_sector 클래스 사용
            job_sector_element = item.find('div', class_='job_sector')
            job_field = ""
            if job_sector_element:
                job_field = job_sector_element.get_text(strip=True)
            
            # 근무지, 경력, 학력 - job_condition 클래스의 span 태그들 사용
            job_condition_element = item.find('div', class_='job_condition')
            work_place = ""
            career = ""
            education = ""
            if job_condition_element:
                spans = job_condition_element.find_all('span')
                if len(spans) >= 3:
                    work_place = spans[0].get_text(strip=True)  # 첫 번째 span이 근무지
                    career = spans[1].get_text(strip=True)      # 두 번째 span이 경력
                    education = spans[2].get_text(strip=True)   # 세 번째 span이 학력
            
            # 마감일 - job_date 클래스의 span.date 사용
            deadline_element = item.find('div', class_='job_date')
            deadline = ""
            if deadline_element:
                date_span = deadline_element.find('span', class_='date')
                if date_span:
                    deadline = date_span.get_text(strip=True)
            

            
            # 지원링크 - job_tit의 a 태그 href 사용
            apply_link = ""
            if job_title_element:
                job_title_link = job_title_element.find('a')
                if job_title_link:
                    href = job_title_link.get('href', '')
                    if href:
                        apply_link = "https://www.saramin.co.kr" + href
            
            job_info = {
                '회사명': company_name,
                '채용제목': job_title,
                '직무분야': job_field,
                '근무지': work_place,
                '경력': career,
                '학력': education,
                '마감일': deadline,
                '지원링크': apply_link
            }
            
            job_data.append(job_info)
            
        except Exception as e:
            print(f"채용 정보 추출 중 오류 발생: {e}")
            continue
    
    return job_data

def print_job_summary(job_data):
    """
    추출한 채용 정보 요약 출력
    """
    print(f"\n=== 채용 정보 요약 ===")
    print(f"총 {len(job_data)}개의 채용 공고를 찾았습니다.\n")
    
    for i, job in enumerate(job_data, 1):
        print(f"[{i}] {job['회사명']}")
        print(f"    제목: {job['채용제목']}")
        print(f"    직무: {job['직무분야']}")
        print(f"    근무지: {job['근무지']}")
        print(f"    경력: {job['경력']}")
        print(f"    학력: {job['학력']}")
        print(f"    마감일: {job['마감일']}")
        print()

# 사용 예시
if __name__ == "__main__":
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

    # #content > div.recruit_list_renew > div 영역 내의 채용 정보 추출
    job_data = extract_job_major_info(html_content)

    # 채용 정보 요약 출력
    print_job_summary(job_data)