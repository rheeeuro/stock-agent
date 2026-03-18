import feedparser
import ollama
from youtube_transcript_api import YouTubeTranscriptApi
import sys
import time
import json
import logging

# 로깅 설정: 시간 포함
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)

from core.config import DB_CONFIG, OLLAMA_MODEL
from core.db import get_db
from core.prompts import YOUTUBE_ANALYSIS_PROMPT
from core.ai_utils import parse_ai_json, remove_markdown_code_blocks
from core.notifications import send_analysis_alert

import mysql.connector


class StockYoutubeAgent:
    def __init__(self):
        self.ytt_api = YouTubeTranscriptApi()
        
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(dictionary=True)
        except Exception as e:
            logging.error(f"❌ DB 연결 실패: {e}")
            sys.exit(1)

    def __del__(self):
        try:
            if hasattr(self, 'cursor') and self.cursor:
                self.cursor.close()
            if hasattr(self, 'conn') and self.conn.is_connected():
                self.conn.close()
        except (ReferenceError, AttributeError):
            pass

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

    def save_analysis(self, video_id, channel, title, content, score, related_tickers, market):
        try:
            content = remove_markdown_code_blocks(content)
            tickers_json_str = json.dumps(related_tickers)
            
            query = """
                INSERT INTO content_analysis (external_id, source_name, title, analysis_content, sentiment_score, related_tickers, market, platform, source_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'youtube', %s)
            """
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            self.cursor.execute(query, (video_id, channel, title, content, score, tickers_json_str, market, video_url))
            self.conn.commit()
            logging.info(f"✅ DB 저장 완료: [{market}] {title} (점수: {score}점)")
        except mysql.connector.Error as err:
            logging.error(f"❌ DB 저장 에러: {err}")

    def get_transcript(self, video_id):
        try:
            transcript_list = self.ytt_api.list(video_id)
            transcript = transcript_list.find_transcript(['ko', 'en'])
            fetched = transcript.fetch()
            text = " ".join([snippet.text for snippet in fetched.snippets])
            logging.info(f"📝 자막 가져오기 성공: {len(text)}자")
            return text
        except Exception as e:
            logging.warning(f"⚠️ 자막 가져오기 실패 ({video_id}): {e}")
            return None

    def analyze_with_ai(self, text, title):
        prompt = YOUTUBE_ANALYSIS_PROMPT.format(title=title, content=text[:3000])
        try:
            logging.info(f"🤖 AI 분석 시작 (모델: {OLLAMA_MODEL})...")
            response = ollama.chat(model=OLLAMA_MODEL, messages=[
                {'role': 'user', 'content': prompt}
            ])
            raw_content = response['message']['content']
            
            data = parse_ai_json(raw_content)
            if data is None:
                return None, 50, None, None

            # 필터링 로직
            if data['sentiment_score'] == -1:
                logging.info(f"🚫 비주식 영상으로 판별됨: {title}")
                return None, None, None, None

            logging.info(f"✅ AI 분석 완료: [{data['market']}] {len(data['content'])}자, 점수: {data['sentiment_score']}점")
            return data['content'], data['sentiment_score'], data['related_tickers'], data['market']

        except Exception as e:
            logging.error(f"❌ AI 분석/파싱 에러: {e}")
            return None, 50, None, None

    def run_once(self):
        logging.info("에이전트 실행 시작 (uv)")
        
        # 1. DB에서 채널 목록 조회
        target_channels = self.get_active_channels()
        logging.info(f"📡 모니터링 대상 채널: {len(target_channels)}개")

        for channel in target_channels:
            name = channel['channel_name']
            c_id = channel['channel_id']
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={c_id}"
            
            feed = feedparser.parse(rss_url)
            if not feed.entries: continue
            
            latest_video = feed.entries[0]
            video_id = latest_video.yt_videoid
            video_title = latest_video.title

            if not self.is_video_processed(video_id):
                logging.info(f"🆕 새 영상 발견 [{name}]: {video_title}")
                script_text = self.get_transcript(video_id)
                
                if script_text:
                    analysis, score, related_tickers, market = self.analyze_with_ai(script_text, video_title)
                    if analysis:
                        # 1. DB 저장
                        self.save_analysis(video_id, name, video_title, analysis, score, related_tickers, market)
                        
                        # 2. 텔레그램 전송
                        send_analysis_alert(name, video_title, analysis, score, related_tickers, market)
                        
                        # 3. 연속 호출 방지 딜레이
                        time.sleep(2)
                    else:
                        logging.warning(f"⚠️ AI 분석 결과가 없어 저장하지 않음")
                else:
                    logging.warning(f"⚠️ 자막이 없어 분석하지 않음")
            else:
                pass 

        logging.info("에이전트 실행 종료")

if __name__ == "__main__":
    agent = StockYoutubeAgent()
    agent.run_once()
