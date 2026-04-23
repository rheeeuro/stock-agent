"""전략 설정 데이터 접근"""
import json
from datetime import datetime

from core.db import get_db


# StrategyConfig 클래스의 기본값 (DB에 값이 없을 때 사용)
_DEFAULTS = {
    "MIN_TRADING_VALUE": 100_000_000_000,
    "PREFERRED_TRADING_VALUE": 200_000_000_000,
    "MIN_MARKET_CAP": 200_000_000_000,
    "TOP_N_BY_VALUE": 20,
    "MA_PERIODS": [5, 10, 20],
    "MIN_INST_NET_BUY_AMT": 1_000_000_000,
    "MIN_FRGN_NET_BUY_AMT": 1_000_000_000,
    "SUPPLY_CHECK_DAYS": 5,
    "TOP_THEME_COUNT": 8,
    "THEME_PERIOD_DAYS": "10",
    "THEME_STOCK_BONUS": 15,
    "CONTENT_SCORE_MAX": 10,
    "EXCLUDE_KEYWORDS": [
        "ETF", "ETN", "KODEX", "TIGER", "KBSTAR",
        "ARIRANG", "SOL", "HANARO", "RISE",
    ],
}


def get_strategy_config() -> dict:
    """전략 설정 조회 (DB에 없으면 기본값 반환)"""
    with get_db() as (conn, cursor):
        cursor.execute("SELECT config, updated_at FROM strategy_config WHERE id = 1")
        row = cursor.fetchone()
        if row:
            config = json.loads(row["config"]) if isinstance(row["config"], str) else row["config"]
            # 기본값에 DB값을 덮어씀 (새 필드 추가 시 자동 반영)
            merged = {**_DEFAULTS, **config}
            return merged
        return dict(_DEFAULTS)


def update_strategy_config(config: dict) -> dict:
    """전략 설정 저장 (UPSERT)"""
    # 기본값과 동일한 키만 저장 (알 수 없는 키 차단)
    filtered = {k: v for k, v in config.items() if k in _DEFAULTS}
    config_json = json.dumps(filtered, ensure_ascii=False)

    with get_db() as (conn, cursor):
        cursor.execute(
            """INSERT INTO strategy_config (id, config)
               VALUES (1, %s)
               ON DUPLICATE KEY UPDATE config = %s""",
            (config_json, config_json),
        )
        conn.commit()

    return get_strategy_config()
