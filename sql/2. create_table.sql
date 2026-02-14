CREATE TABLE IF NOT EXISTS channels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    channel_name VARCHAR(100) NOT NULL,
    channel_id VARCHAR(50) NOT NULL UNIQUE, -- 유튜브 채널 고유 ID
    is_active BOOLEAN DEFAULT TRUE,         -- 모니터링 활성화 여부 (ON/OFF)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS video_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    video_id VARCHAR(50) NOT NULL UNIQUE, -- 중복 분석 방지용
    channel_name VARCHAR(100),
    video_title VARCHAR(255),
    analysis_content TEXT, -- AI 분석 결과
    market_sentiment INT DEFAULT 0, -- (선택) 감정 점수 저장용
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_video_id (video_id)
);

CREATE TABLE IF NOT EXISTS daily_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_date DATE NOT NULL,
    buy_stock VARCHAR(100),
    buy_reason TEXT,
    sell_stock VARCHAR(100),
    sell_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS telegram_channels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    channel_identifier VARCHAR(100) NOT NULL COMMENT '채널 username(문자) 또는 ID(숫자)',
    display_name VARCHAR(100) COMMENT '대시보드에 표시할 이름',
    is_active BOOLEAN DEFAULT TRUE COMMENT '1: 수집중, 0: 중지',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 1. 통합 소스 테이블 생성
CREATE TABLE IF NOT EXISTS sources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    platform VARCHAR(20) NOT NULL, -- 'youtube', 'telegram' 등
    identifier VARCHAR(100) NOT NULL, -- 채널ID, Username 등
    name VARCHAR(100), -- 표시할 이름 (슈카월드, 등)
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);