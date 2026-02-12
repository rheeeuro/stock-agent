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
        내용 요약 및 투자 인사이트를 정리해줘.
        
        [반드시 아래 Markdown 형식을 지켜서 출력해]:
        
        ## 1. 3줄 핵심 요약
        - (요약 1)
        - (요약 2)
        - (요약 3)
        
        ## 2. 주요 언급 종목
        - **종목명**: (호재/악재 판단)
        
        ## 3. 대응 전략
        > (한 줄 조언)

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
        query = "SELECT channel_name, channel_id FROM channels WHERE is_active = TRUE"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def is_video_processed(self, video_id):
        query = "SELECT count(*) as cnt FROM video_analysis WHERE video_id = %s"
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

    def save_analysis(self, video_id, channel, title, content):
        try:
            # 앞뒤의 markdown 코드 블록 마커 제거
            content = self.remove_markdown_code_blocks(content)
            
            query = """
                INSERT INTO video_analysis (video_id, channel_name, video_title, analysis_content)
                VALUES (%s, %s, %s, %s)
            """
            self.cursor.execute(query, (video_id, channel, title, content))
            self.conn.commit()
            print(f"✅ DB 저장 완료: {title}")
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
            result = response['message']['content']
            print(f"✅ AI 분석 완료: {len(result)}자")
            return result
        except Exception as e:
            print(f"❌ AI 분석 에러: {e}")
            print(f"💡 사용 가능한 모델 확인: docker exec stock_ollama ollama list")
            print(f"💡 모델 설치 예시: docker exec stock_ollama ollama pull {model_name}")
            return None
    
    def send_telegram(self, channel, title, analysis):
        """텔레그램 메시지 발송 함수"""
        try:
            # 앞뒤의 markdown 코드 블록 마커 제거
            analysis = self.remove_markdown_code_blocks(analysis)
            
            # 메시지가 너무 길면 텔레그램 전송이 실패할 수 있어 800자로 제한
            short_analysis = analysis[:800] + "..." if len(analysis) > 800 else analysis
            
            message = (
                f"🚨 [{channel}] 새 리포트 도착!\n"
                f"📺 {title}\n\n"
                f"{short_analysis}\n\n"
                f"👉 대시보드: https://stock.rheeeuro.com/"
            )
            
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            # 타임아웃 10초 설정
            res = requests.post(url, data=data, timeout=10)
            
            if res.status_code == 200:
                print(f"📨 텔레그램 전송 성공")
            else:
                print(f"⚠️ 텔레그램 전송 실패: {res.text}")
                
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
                    analysis = self.analyze_with_ai(script_text, video_title)
                    if analysis:
                        # 1. DB 저장
                        self.save_analysis(video_id, name, video_title, analysis)
                        
                        # 2. ✅ 텔레그램 전송
                        self.send_telegram(name, video_title, analysis)
                        
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
