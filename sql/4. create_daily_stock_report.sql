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
