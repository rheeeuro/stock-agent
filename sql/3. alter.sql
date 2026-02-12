-- video_analysis 테이블에 'sentiment_score' 컬럼 추가
-- 기본값은 50(중립)으로 설정
ALTER TABLE video_analysis 
ADD COLUMN sentiment_score INT DEFAULT 50;