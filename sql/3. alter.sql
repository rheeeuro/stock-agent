-- video_analysis 테이블에 'sentiment_score' 컬럼 추가
-- 기본값은 50(중립)으로 설정
ALTER TABLE video_analysis 
ADD COLUMN sentiment_score INT DEFAULT 50;

-- 1. 출처 구분 컬럼 (youtube 또는 telegram)
ALTER TABLE video_analysis ADD COLUMN source_type VARCHAR(20) DEFAULT 'youtube';

-- 2. 원문 링크 (텔레그램 메시지 링크 등)
ALTER TABLE video_analysis ADD COLUMN source_url VARCHAR(255);

-- 3. (선택) 기존 데이터는 모두 유튜브로 마킹
UPDATE video_analysis SET source_type = 'youtube' WHERE source_type IS NULL;

-- 1. 테이블 이름 변경
RENAME TABLE video_analysis TO content_analysis;

-- 2. 컬럼 이름 일반화 (영상 전용 용어 제거)
ALTER TABLE content_analysis CHANGE video_id external_id VARCHAR(255); -- 유튜브ID or 텔레그램Link
ALTER TABLE content_analysis CHANGE video_title title VARCHAR(255);     -- 영상제목 or 메시지요약
ALTER TABLE content_analysis CHANGE channel_name source_name VARCHAR(100); -- 채널명

-- 3. 플랫폼 구분 컬럼 확인 (없으면 추가, 이미 있다면 패스)
-- (아까 추가하셨다면 이 줄은 건너뛰세요)
ALTER TABLE content_analysis ADD COLUMN platform VARCHAR(20) DEFAULT 'youtube'; 
-- platform 값 예시: 'youtube', 'telegram', 'news'

-- 2. 기존 유튜브 채널 데이터 이관 (가정)
INSERT INTO sources (platform, identifier, name)
SELECT 'youtube', channel_id, channel_name FROM channels;

-- 3. 기존 텔레그램 채널 데이터 이관 (가정)
INSERT INTO sources (platform, identifier, name)
SELECT 'telegram', channel_identifier, display_name FROM telegram_channels;

-- 4. (선택) 구형 테이블 삭제 (데이터 이관 확인 후 실행!)
-- DROP TABLE channels;
-- DROP TABLE telegram_channels;

ALTER TABLE daily_summary ADD COLUMN buy_ticker VARCHAR(20) AFTER buy_stock;
ALTER TABLE daily_summary ADD COLUMN sell_ticker VARCHAR(20) AFTER sell_stock;

ALTER TABLE content_analysis ADD COLUMN related_tickers VARCHAR(255) DEFAULT NULL;