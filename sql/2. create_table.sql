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

CREATE TABLE ticker_dictionary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(100) UNIQUE NOT NULL,
    ticker_symbol VARCHAR(50) NOT NULL,
    market VARCHAR(10) DEFAULT 'KR',       -- 'KR', 'US' 등
    status VARCHAR(20) DEFAULT 'PENDING',  -- 'PENDING'(대기중), 'ACTIVE'(검증완료), 'INACTIVE'(비활성)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 종목일간리포트 테이블 생성
-- Phase 2 수급 분석 결과를 일별로 저장
CREATE TABLE IF NOT EXISTS daily_stock_report (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_date DATE NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,
    sector VARCHAR(50) DEFAULT '기타',
    current_price INT DEFAULT 0,
    change_pct FLOAT DEFAULT 0.0,
    trading_value BIGINT DEFAULT 0,
    market_cap BIGINT DEFAULT 0,

    -- 수급 관련
    supply_grade VARCHAR(10) NOT NULL DEFAULT 'C',
    inst_net_buy BIGINT DEFAULT 0,
    frgn_net_buy BIGINT DEFAULT 0,
    indv_net_buy BIGINT DEFAULT 0,
    prog_net_buy BIGINT DEFAULT 0,
    supply_days INT DEFAULT 0,
    supply_history JSON DEFAULT NULL,    -- 최근 5일 수급 현황 (투자자별 순매수)

    -- 차트 분석
    ma_aligned TINYINT(1) DEFAULT 0,
    near_high TINYINT(1) DEFAULT 0,

    -- 대장주 / 점수
    is_leader TINYINT(1) DEFAULT 0,
    score FLOAT DEFAULT 0.0,
    rank_no INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_date_code (report_date, stock_code),
    INDEX idx_report_date (report_date),
    INDEX idx_stock_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS daily_sector_report (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    report_date    DATE NOT NULL,
    thema_grp_cd   VARCHAR(20) NOT NULL,
    thema_nm       VARCHAR(50) NOT NULL,
    stk_num        INT DEFAULT 0,
    flu_rt         FLOAT DEFAULT 0.0,
    dt_prft_rt     FLOAT DEFAULT 0.0,
    main_stk       VARCHAR(50),
    rising_stk_num INT DEFAULT 0,
    fall_stk_num   INT DEFAULT 0,
    rank_no        INT DEFAULT 0,
    stocks         JSON,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_date_thema (report_date, thema_grp_cd)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
