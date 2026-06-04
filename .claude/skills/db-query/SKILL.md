---
name: db-query
description: MariaDB 에 읽기 전용 SQL 을 실행해 데이터를 확인한다. 스키마/데이터 점검, 디버깅 시 사용.
---

# /db

MariaDB(도커 컨테이너)에 SQL 을 실행한다. **기본은 읽기 전용(SELECT/SHOW/DESCRIBE)**.

1. 컨테이너 이름 확인: `docker ps --format '{{.Names}}' | grep -i maria`
2. 접속 정보는 `core/config.py`/`.env` 의 DB_* 를 따른다 (값을 출력하지 말 것).
3. 쿼리 실행:
   `docker exec <컨테이너> mysql -u<user> -p<pw> <db> -e "<SQL>"`
4. 주요 테이블: `content_analysis`, `daily_stock_report`, `sector_report`,
   `ticker_dictionary`, `source`, `daily_summary`, `telegram_user`.

INSERT/UPDATE/DELETE/DDL 은 **사용자에게 명시적으로 확인받은 뒤에만** 실행한다.
스키마 변경은 `sql/` 폴더의 마이그레이션 파일로 관리할 것.
