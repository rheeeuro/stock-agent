-- ============================================================
-- 미국장 제거 마이그레이션 (국장-only 전환)
-- - 비-국장(KR) 데이터 삭제 후 market 컬럼 제거
-- - content_analysis: KR만 유지 (US/UNKNOWN/CRYPTO/기타 전부 삭제)
-- - ticker_dictionary: US만 삭제 (KR 유지)
-- - daily_summary:     KR만 유지 (US/NULL 삭제)
-- 실행 전 백업 권장. market 컬럼 DROP은 되돌릴 수 없음.
-- ============================================================

-- 1) content_analysis: 국장(KR) 외 전부 삭제 후 컬럼 제거
DELETE FROM content_analysis WHERE market IS NULL OR market <> 'KR';
ALTER TABLE content_analysis DROP COLUMN market;

-- 2) ticker_dictionary: 미국(US) 티커 삭제 후 컬럼 제거
DELETE FROM ticker_dictionary WHERE market = 'US';
ALTER TABLE ticker_dictionary DROP COLUMN market;

-- 3) daily_summary: 국장(KR) 외(US/NULL) 삭제 후 컬럼 제거
DELETE FROM daily_summary WHERE market IS NULL OR market <> 'KR';
ALTER TABLE daily_summary DROP COLUMN market;
