import requests
import json
from datetime import datetime

def get_deep_news_from_firecrawl(ticker):
    url = "http://127.0.0.1:3002/v2/search"
    headers = {"Content-Type": "application/json"}
    
    # 🚀 핵심: 사람이 검색하듯 아주 심플하고 직관적인 키워드로 변경!
    current_month = datetime.now().strftime("%B %Y")
    query = f"{ticker} stock news analysis insight {current_month}"
    
    payload = {
        "query": query,
        "limit": 5,  # 후보군을 5개로 넉넉하게 늘립니다.
        "scrapeOptions": {
            "formats": ["markdown"],
            "onlyMainContent": True
        }
    }
    
    print(f"🔥 Firecrawl 가동: '{query}' 검색 중...\n")
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result_json = response.json()
        
        combined_markdown = ""
        web_results = result_json.get('data', {}).get('web', [])
        
        valid_articles = 0
        
        print("🔎 [수사 로그] 수집된 문서들을 검토합니다...")
        for i, item in enumerate(web_results):
            title = item.get('title', f'뉴스 {i+1}')
            source_url = item.get('url', '출처 불명')
            markdown_content = item.get('markdown', '')
            
            # 수집된 문서의 상태를 출력해봅니다.
            print(f" 👉 {i+1}번 후보: {title[:40]}... (길이: {len(markdown_content)}자)")
            
            # 방어 로직: 봇 차단 페이지거나 내용이 너무 짧은 경우 스킵
            if "Will be right back" in markdown_content or "Enable JavaScript" in markdown_content:
                print("    ❌ 차단된 페이지입니다. (스킵)")
                continue
            if len(markdown_content) < 300: # 기준을 300자로 대폭 낮춤
                print("    ❌ 내용이 너무 짧습니다. (스킵)")
                continue
                
            print("    ✅ 합격! 본문을 추출합니다.")
            if len(markdown_content) > 2500:
                markdown_content = markdown_content[:2500] + "...(중략)..."
                
            combined_markdown += f"### [출처: {title}]({source_url})\n{markdown_content}\n\n---\n\n"
            valid_articles += 1
            
            # 양질의 기사 2개면 충분합니다.
            if valid_articles >= 2:
                break
                
        if not combined_markdown:
             return "\n❌ 관련된 심층 분석 기사를 찾지 못했습니다. (모두 필터링됨)"
             
        return f"\n========== [최종 수집 완료] ==========\n\n{combined_markdown}"
        
    except Exception as e:
        print(f"\n❌ Firecrawl 수집 에러: {e}")
        return ""

if __name__ == "__main__":
    result = get_deep_news_from_firecrawl("NVDA")
    print(result)