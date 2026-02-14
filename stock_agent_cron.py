import feedparser
import ollama
import mysql.connector
from youtube_transcript_api import YouTubeTranscriptApi
from datetime import datetime
import sys
import os
import time
import requests
import re
import json

from dotenv import load_dotenv
load_dotenv()

# DB 설정: .env의 DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT 사용
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'user': os.getenv('DB_USER', 'stock_user'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'stock_agent'),
    'port': int(os.getenv('DB_PORT', '3307')),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'use_unicode': True,
}

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
CHAT_ID = os.getenv('CHAT_ID', '')

# AI 분석 프롬프트 템플릿. {title}, {content} 플레이스홀더 사용. .env의 AI_PROMPT_TEMPLATE으로 덮어쓰기 가능
AI_PROMPT_TEMPLATE = """
        영상 제목: {title}

        [중요 지시사항]
        먼저 이 영상이 **'주식, 경제, 투자, 기업 분석, 시장 전망'**과 관련된 내용인지 판단해.
        
        1. 만약 **관련 없는 내용(일상, 먹방, 게임, 단순 유머 등)**이라면:
           반드시 JSON의 sentiment_score를 **-1**로 설정하고 content는 비워둬.
           
        2. **관련 있는 내용**이라면 다음 두 가지를 분석해서 반드시 **JSON 포맷**으로만 출력해.
            - sentiment_score: 시장 전망 점수 (0: 폭락/공포 ~ 50: 중립 ~ 100: 폭등/탐욕)
            - content: 마크다운 형식의 투자 인사이트 분석 리포트 (3줄 요약, 종목, 대응 전략 포함)
        
            [반드시 아래 Markdown 형식을 지켜서 출력해]:
            
            ## 1. 3줄 핵심 요약
            - (요약 1)
            - (요약 2)
            - (요약 3)
            
            ## 2. 주요 언급 종목
            - **종목명**: (호재/악재 판단)
            
            ## 3. 대응 전략
            > (한 줄 조언)
        
        [필수 출력 형식 - JSON Only]:
        {{
            "sentiment_score": 75,  // 아닐 경우 -1
            "content": "분석 내용..." // 아닐 경우 ""
        }}

        [자막 내용]: {content}
        """

class StockYoutubeAgent:
    def __init__(self):
        self.ytt_api = YouTubeTranscriptApi()
        # self.channels 딕셔너리 제거됨 (DB에서 동적 로딩)
        
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(dictionary=True) # 결과를 딕셔너리로 받기
        except Exception as e:
            print(f"❌ DB 연결 실패: {e}")
            sys.exit(1)

    def __del__(self):
        try:
            if hasattr(self, 'cursor') and self.cursor:
                self.cursor.close()
            if hasattr(self, 'conn') and self.conn.is_connected():
                self.conn.close()
        except (ReferenceError, AttributeError):
            pass  # 객체가 이미 소멸된 경우 무시

    def get_active_channels(self):
        """DB에서 활성화된 채널 목록 가져오기"""
        query = "SELECT identifier as channel_id, name as channel_name FROM sources WHERE platform = 'youtube' AND is_active = TRUE"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def is_video_processed(self, video_id):
        query = "SELECT count(*) as cnt FROM content_analysis WHERE external_id = %s"
        self.cursor.execute(query, (video_id,))
        result = self.cursor.fetchone()
        return result['cnt'] > 0

    def remove_markdown_code_blocks(self, content):
        """앞뒤의 markdown 코드 블록 마커 제거"""
        if not content:
            return content
        
        # 앞뒤 공백 제거
        content = content.strip()
        
        # 앞에서 시작하는 ``` 제거 (언어 태그 포함: ```markdown, ```python 등)
        content = re.sub(r'^```[a-zA-Z]*\s*\n?', '', content, flags=re.MULTILINE)
        content = re.sub(r'^```\s*\n?', '', content, flags=re.MULTILINE)
        
        # 뒤에서 끝나는 ``` 제거
        content = re.sub(r'\r?\n```\s*$', '', content)  # 줄바꿈 후 ```
        content = re.sub(r'```\s*$', '', content)  # 바로 ```
        
        # 최종 공백 정리
        return content.strip()

    def save_analysis(self, video_id, channel, title, content, score):
        try:
            # 앞뒤의 markdown 코드 블록 마커 제거
            content = self.remove_markdown_code_blocks(content)
            
            query = """
                INSERT INTO content_analysis (external_id, source_name, title, analysis_content, sentiment_score, platform, source_url)
                VALUES (%s, %s, %s, %s, %s, 'youtube', %s)
            """
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            self.cursor.execute(query, (video_id, channel, title, content, score, video_url))
            self.conn.commit()
            print(f"✅ DB 저장 완료: {title} (점수: {score}점)")
        except mysql.connector.Error as err:
            print(f"❌ DB 저장 에러: {err}")

    def get_transcript(self, video_id):
        try:
            transcript_list = self.ytt_api.list(video_id)
            transcript = transcript_list.find_transcript(['ko', 'en'])
            fetched = transcript.fetch()
            # fetch()는 FetchedTranscript 객체를 반환. snippets 속성 사용
            text = " ".join([snippet.text for snippet in fetched.snippets])
            print(f"📝 자막 가져오기 성공: {len(text)}자")
            return text
        except Exception as e:
            print(f"⚠️ 자막 가져오기 실패 ({video_id}): {e}")
            return None

    def analyze_with_ai(self, text, title):
        prompt = AI_PROMPT_TEMPLATE.format(title=title, content=text[:3000])
        model_name = os.getenv('OLLAMA_MODEL', 'deepseek-r1:8b')  # 기본값: deepseek-r1:8b
        try:
            print(f"🤖 AI 분석 시작 (모델: {model_name})...")
            response = ollama.chat(model=model_name, messages=[
                {'role': 'user', 'content': prompt}
            ])
            raw_content = response['message']['content']
            
            # DeepSeek 모델 특성상 <think> 태그나 ```json 마크다운이 섞일 수 있어 제거
            clean_json = raw_content.replace('```json', '').replace('```', '').strip()

            # <think> 태그 제거 로직 (DeepSeek-R1 대응)
            if '</think>' in clean_json:
                clean_json = clean_json.split('</think>')[-1].strip()

            data = json.loads(clean_json)

            # 필터링 로직 추가
            if data['sentiment_score'] == -1:
                print(f"🚫 비주식 영상으로 판별됨: {title}")
                return None, None  # 저장하지 않고 종료

            print(f"✅ AI 분석 완료: {len(data['content'])}자, 점수: {data['sentiment_score']}점")
            return data['content'], data['sentiment_score']

        except Exception as e:
            print(f"❌ AI 분석/파싱 에러: {e}")
            # 에러 나면 기본값 반환 (내용은 원본, 점수는 50)
            return None, 50
    
    def send_telegram(self, channel, title, analysis, score=50):
        """텔레그램 메시지 발송 함수"""
        try:
            # 1. 상태 이모지 결정
            if score >= 80:
                status = "🔥 *강력 매수* (탐욕)"
            elif score >= 60:
                status = "📈 *긍정적* (매수)"
            elif score <= 20:   
                status = "🥶 *공포* (현금화)"
            elif score <= 40:
                status = "📉 *부정적* (보수적)"
            else:
                status = "😐 *중립* (관망)"

            # 2. 메시지 길이 제한 (너무 길면 전송 실패함)
            short_analysis = analysis[:800] + "..." if len(analysis) > 800 else analysis
            
            # 3. 마크다운 변환 (중요!)
            # AI는 '**'를 쓰지만 텔레그램(Legacy Markdown)은 '*'가 볼드체입니다.
            # 따라서 '**'를 '*'로 바꿔줘야 텔레그램에서 예쁘게 나옵니다.
            formatted_analysis = short_analysis.replace("**", "*")
            message = (
                f"🚨 *[{channel}] 분석 완료!*\n"
                f"📊 관점: {score}점 - {status}\n\n"
                f"📺 {title}\n"
                f"──────────────────\n"
                f"{formatted_analysis}\n\n"
                f"👉 [대시보드 바로가기](https://stock.rheeeuro.com)" # 링크 거는 문법
            )
            
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "Markdown", # ✅ 핵심: "이거 마크다운이야!"라고 알려줌
                "disable_web_page_preview": True # (선택) 링크 미리보기 끄기 (깔끔하게)
            }
            
            requests.post(url, data=data, timeout=10)
            print(f"📨 텔레그램 전송 성공: {title} ({score}점)")
                
        except Exception as e:
            print(f"❌ 텔레그램 에러: {e}")

    def run_once(self):
        print(f"[{datetime.now()}] 에이전트 실행 시작 (uv)")
        
        # 1. DB에서 채널 목록 조회
        target_channels = self.get_active_channels()
        print(f"📡 모니터링 대상 채널: {len(target_channels)}개")

        for channel in target_channels:
            name = channel['channel_name']
            c_id = channel['channel_id']
            # RSS URL 동적 생성
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={c_id}"
            
            feed = feedparser.parse(rss_url)
            if not feed.entries: continue
            
            latest_video = feed.entries[0]
            video_id = latest_video.yt_videoid
            video_title = latest_video.title

            if not self.is_video_processed(video_id):
                print(f"🆕 새 영상 발견 [{name}]: {video_title}")
                script_text = self.get_transcript(video_id)
                
                if script_text:
                    analysis, score = self.analyze_with_ai(script_text, video_title)
                    if analysis:
                        # 1. DB 저장
                        self.save_analysis(video_id, name, video_title, analysis, score)
                        
                        # 2. 텔레그램 전송 (✅ score 인자 전달)
                        self.send_telegram(name, video_title, analysis, score)
                        
                        # 3. 연속 호출 방지 딜레이
                        time.sleep(2)
                    else:
                        print(f"⚠️ AI 분석 결과가 없어 저장하지 않음")
                else:
                    print(f"⚠️ 자막이 없어 분석하지 않음")
            else:
                pass 

        print(f"[{datetime.now()}] 에이전트 실행 종료")

if __name__ == "__main__":
    agent = StockYoutubeAgent()
    agent.run_once()
