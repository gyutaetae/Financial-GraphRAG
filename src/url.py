# requests는 HTTP 요청을 보내는 도구예요!
# 마치 "웹사이트에 요청을 보내는 우체국" 같은 거예요!
import requests
# BeautifulSoup은 HTML을 파싱하는 도구예요!
# 마치 "HTML 문서를 읽고 필요한 부분만 뽑아내는 도구" 같은 거예요!
from bs4 import BeautifulSoup
# time은 시간 관련 작업을 하는 도구예요!
import time
# sys는 시스템 관련 작업을 하는 도구예요!
# 마치 "컴퓨터 시스템과 대화하는" 것처럼!
import sys

def auto_researcher(url):
    """
    웹 페이지에서 텍스트를 추출해서 GraphRAG API로 전송하는 함수예요!
    
    Args:
        url: 크롤링할 웹 페이지 URL
        
    Returns:
        API 응답 결과 (dict)
    참고: url 정보도 함께 API로 전송해요!
    """
    try:
        # 1. Web Crawler: 뉴스 페이지 가져오기
        # requests.get()은 웹 페이지에 GET 요청을 보내는 거예요!
        # 마치 "웹사이트에 '이 페이지를 보여줘'라고 요청하는" 것처럼!
        print(f"🌐 웹 페이지 가져오는 중: {url}")
        
        # headers는 "요청 헤더"예요! 웹사이트에 "나는 이런 브라우저야"라고 알려주는 거예요!
        # User-Agent를 설정하면 일부 웹사이트가 크롤링을 차단하지 않아요!
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # requests.get()에 headers를 추가해서 요청해요!
        response = requests.get(url, headers=headers, timeout=10)  # timeout은 "10초 안에 응답이 없으면 포기"라는 뜻이에요!
        
        # response.raise_for_status()는 "응답이 성공적이지 않으면 에러를 발생시켜"라는 뜻이에요!
        response.raise_for_status()
        
        # 2. Parser: 본문 텍스트만 추출
        # BeautifulSoup()은 HTML을 파싱하는 거예요!
        # 'html.parser'는 "HTML 파서를 사용한다"는 뜻이에요!
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # soup.find_all('p')는 "모든 <p> 태그를 찾아"라는 뜻이에요!
        # p.get_text()는 "그 태그 안의 텍스트만 가져와"라는 뜻이에요!
        # " ".join()은 "공백으로 연결해서 하나의 문자열로 만들어"라는 뜻이에요!
        text_content = " ".join([p.get_text() for p in soup.find_all('p')])
        
        # 텍스트가 비어있으면 에러를 발생시켜요!
        if not text_content.strip():
            # <p> 태그가 없으면 다른 태그들도 시도해요!
            text_content = " ".join([tag.get_text() for tag in soup.find_all(['article', 'div', 'main'])])
        
        # 텍스트가 여전히 비어있으면 에러를 발생시켜요!
        if not text_content.strip():
            raise ValueError("웹 페이지에서 텍스트를 추출할 수 없어요!")
        
        print(f"추출된 텍스트 길이: {len(text_content)} 글자")
        
        # 3. API Integration: GraphRAG API로 전송
        api_url = "http://127.0.0.1:8000/insert"
        # payload는 "전송할 데이터"예요!
        # text_content[:1000]은 "앞 1000글자만 사용한다"는 뜻이에요! (테스트용)
        # 전체 텍스트를 사용하려면 [:1000]을 제거하면 돼요!
        # 하지만 너무 길면 API 호출이 오래 걸릴 수 있어요!
        max_length = 5000  # 최대 5000글자로 제한 (필요하면 변경 가능)
        text_to_send = text_content[:max_length] if len(text_content) > max_length else text_content
        
        print(f"🚀 GraphRAG API로 전송 중...")
        print(f"⏱️  인덱싱은 시간이 걸릴 수 있어요. (최대 5분 대기)")
        print(f"💡 팁: 텍스트가 길수록 더 오래 걸려요!")
        
        # timeout을 300초(5분)로 늘려요! 인덱싱은 시간이 걸릴 수 있어요!
        # connect timeout은 "연결하는데 10초", read timeout은 "응답을 읽는데 300초"라는 뜻이에요!
        res = requests.post(api_url, json={"text": text_to_send}, timeout=(10, 300))
        
        # res.raise_for_status()는 "응답이 성공적이지 않으면 에러를 발생시켜"라는 뜻이에요!
        res.raise_for_status()
        
        result = res.json()
        print(f"✅ 인덱싱 완료!")
        return result
        
    except requests.exceptions.RequestException as e:
        # requests.exceptions.RequestException은 "HTTP 요청 관련 에러"예요!
        error_msg = f"HTTP 요청 에러: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg, "status": "error"}
    except ValueError as e:
        # ValueError는 "값이 잘못되었다"는 에러예요!
        error_msg = f"텍스트 추출 에러: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg, "status": "error"}
    except Exception as e:
        # Exception은 "모든 종류의 에러"예요!
        error_msg = f"예상치 못한 에러: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg, "status": "error"}

# if __name__ == "__main__": 이건 "이 파일을 직접 실행했을 때만"이라는 뜻이에요!
# 마치 "이 파일을 직접 실행할 때만 아래 코드를 실행해"라는 의미예요!
if __name__ == "__main__":
    # sys.argv는 "명령줄에서 입력한 인자들"이에요!
    # 예: python3 url.py https://example.com
    #     sys.argv[0] = "url.py"
    #     sys.argv[1] = "https://example.com"
    
    # len(sys.argv)는 "인자의 개수"예요!
    if len(sys.argv) < 2:
        # URL이 입력되지 않았으면 사용법을 알려줘요!
        print("=" * 60)
        print("📚 사용법:")
        print("=" * 60)
        print("python3 src/url.py <URL>")
        print()
        print("예시:")
        print("  python3 src/url.py https://www.example.com")
        print("  python3 src/url.py https://news.ycombinator.com")
        print("=" * 60)
        # sys.exit(1)은 "프로그램을 종료하고 에러 코드 1을 반환한다"는 뜻이에요!
        sys.exit(1)
    
    # sys.argv[1]은 "첫 번째 인자(URL)"예요!
    url = sys.argv[1]
    
    print("=" * 60)
    print("🚀 웹 크롤링 및 GraphRAG 인덱싱 시작")
    print("=" * 60)
    print(f"URL: {url}")
    print()
    
    # auto_researcher 함수를 호출해요!
    result = auto_researcher(url)
    
    print()
    print("=" * 60)
    print("📊 최종 결과:")
    print("=" * 60)
    # json.dumps()는 딕셔너리를 JSON 문자열로 변환하는 거예요!
    # indent=2는 "들여쓰기를 2칸으로 해서 보기 좋게 만들어"라는 뜻이에요!
    # ensure_ascii=False는 "한글도 제대로 표시해"라는 뜻이에요!
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))