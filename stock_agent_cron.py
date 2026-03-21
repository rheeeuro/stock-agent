import logging
import time

import feedparser
from youtube_transcript_api import YouTubeTranscriptApi

from core.logging_setup import setup_logging
from core.config import OLLAMA_MODEL
from core.prompts import YOUTUBE_ANALYSIS_PROMPT
from core.ai_service import analyze_content
from core.repository import get_active_sources, is_content_processed, save_content_analysis
from core.notifications import send_analysis_alert

setup_logging()


class StockYoutubeAgent:
    def __init__(self):
        self.ytt_api = YouTubeTranscriptApi()

    def get_transcript(self, video_id: str) -> str | None:
        """YouTube 영상의 자막을 가져옴"""
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

    def run_once(self):
        logging.info("에이전트 실행 시작 (uv)")

        target_channels = get_active_sources('youtube')
        logging.info(f"📡 모니터링 대상 채널: {len(target_channels)}개")

        for channel in target_channels:
            name = channel['name']
            c_id = channel['identifier']
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={c_id}"

            feed = feedparser.parse(rss_url)
            if not feed.entries:
                continue

            latest_video = feed.entries[0]
            video_id = latest_video.yt_videoid
            video_title = latest_video.title

            if is_content_processed(video_id):
                continue

            logging.info(f"🆕 새 영상 발견 [{name}]: {video_title}")
            script_text = self.get_transcript(video_id)

            if not script_text:
                logging.warning("⚠️ 자막이 없어 분석하지 않음")
                continue

            prompt = YOUTUBE_ANALYSIS_PROMPT.format(title=video_title, content=script_text[:3000])
            result = analyze_content(prompt)

            if not result:
                logging.warning("⚠️ AI 분석 결과가 없어 저장하지 않음")
                continue

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            save_content_analysis(
                external_id=video_id,
                source_name=name,
                title=video_title,
                content=result.content,
                score=result.sentiment_score,
                source_url=video_url,
                related_tickers=result.related_tickers,
                platform='youtube',
                market=result.market,
            )

            send_analysis_alert(name, video_title, result.content, result.sentiment_score, result.related_tickers, result.market)
            time.sleep(2)

        logging.info("에이전트 실행 종료")


if __name__ == "__main__":
    agent = StockYoutubeAgent()
    agent.run_once()
