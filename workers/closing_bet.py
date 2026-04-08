"""
종가베팅 알고리즘 v2.0 — 전략 오케스트레이터
============================================================
[타임라인]
  13:00~14:30  사전 스크리닝 & 시장 분위기 파악
  14:30~15:00  수급 정밀 체크 & 매수 후보 확정
  15:00~15:20  분할 매수 실행
  익일 09:00~10:30  매도 실행
"""

import time
import logging
from datetime import datetime

from core.kiwoom_api import KiwoomConfig, KiwoomRestAPI
from core.trading_engine import (
    StrategyConfig,
    SupplyGrade,
    StockCandidate,
    AnalysisEngine,
    OrderExecutor,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ClosingBet")


class ClosingBetStrategy:
    def __init__(self):
        self.api_cfg = KiwoomConfig()
        self.strategy_cfg = StrategyConfig()
        self.api = KiwoomRestAPI(self.api_cfg)
        self.engine = AnalysisEngine(self.api, self.strategy_cfg)
        self.executor = OrderExecutor(self.api, self.strategy_cfg)

    def run(self):
        logger.info("=" * 60)
        logger.info("종가베팅 알고리즘 v2.0 (키움 REST API)")
        logger.info("=" * 60)

        # 0. 인증 (au10001)
        self.api.get_access_token()

        try:
            # 1. Phase 1 — 사전 스크리닝 (13:00~)
            # self._wait_until(self.strategy_cfg.SCREENING_START)
            candidates = self._phase1_screening()
            logger.info(f"Phase 1 완료: {len(candidates)}개 후보")
            logger.info("Phase 1 상위 후보:")
            for i, c in enumerate(candidates[:10], 1):
                logger.info(
                    f"  {i:2d}. {c.name:10s} "
                    f"등락={c.change_pct:+.1f}%  "
                    f"거래대금={c.trading_value/1e8:,.0f}억  섹터={c.sector}"
                )

            # 2. Phase 2 — 수급 정밀 분석 (14:30~)
            # self._wait_until(self.strategy_cfg.SUPPLY_CHECK_START)
            candidates = self._phase2_supply_analysis(candidates)
            logger.info(f"Phase 2 완료: {len(candidates)}개 후보")

            return  # Phase 3 매수 실행은 테스트를 위해 일단 보류

            # # 3. Phase 3 — 매수 실행 (15:00~15:20)
            # self._wait_until(self.strategy_cfg.BUY_WINDOW_START)
            # self._phase3_execute_buy(candidates)

            # # 4. Phase 4 — 익일 매도 (09:00~10:30)
            # logger.info("익일 오전 매도 대기...")
            # self._wait_until("09:05")
            # self.executor.execute_morning_sell()

            # logger.info("전략 실행 완료")
        finally:
            self.api.revoke_access_token()

    # ── Phase 1: 스크리닝 ──
    def _phase1_screening(self) -> list[StockCandidate]:
        candidates = []
        seen_codes = set()

        # (a) 거래대금 TOP N (코스피 + 코스닥)
        for mrkt in ["001", "101"]:
            try:
                data = self.api.get_trading_value_rank(mrkt_tp=mrkt)
                items = data.get("trde_prica_upper", [])
                for item in items[:self.strategy_cfg.TOP_N_BY_VALUE]:
                    code = item.get("stk_cd", "").split("_")[0]
                    name = item.get("stk_nm", "")
                    tv = abs(self.engine.parse_price(item.get("trde_prica", "0"))) * 1_000_000
                    cp = abs(self.engine.parse_price(item.get("cur_prc", "0")))
                    chg = self.engine.parse_float(item.get("flu_rt", "0"))
                    mc = 0

                    if code in seen_codes:
                        continue
                    if not self.engine.filter_basic(name, tv, mc):
                        continue

                    sector = self._find_sector(code)
                    candidates.append(StockCandidate(
                        code=code, name=name, sector=sector,
                        current_price=cp, trading_value=tv,
                        market_cap=mc, change_pct=chg,
                    ))
                    seen_codes.add(code)
            except Exception as e:
                logger.error(f"거래대금순위 조회 실패 (mrkt={mrkt}): {e}")
            time.sleep(0.3)

        # (b) 관심섹터 종목 보강
        for sector, codes in self.strategy_cfg.WATCHLIST_SECTORS.items():
            for code in codes:
                if code in seen_codes:
                    continue
                try:
                    info = self.api.get_stock_basic_info(code)
                    name = info.get("stk_nm", code)
                    cp = self.engine.parse_price(info.get("cur_prc", "0"))
                    mc_raw = self.engine.parse_price(info.get("mac", "0"))
                    mc = mc_raw * 100_000_000
                    if mc >= self.strategy_cfg.MIN_MARKET_CAP:
                        candidates.append(StockCandidate(
                            code=code, name=name, sector=sector,
                            current_price=cp, market_cap=mc,
                        ))
                        seen_codes.add(code)
                    time.sleep(0.3)
                except Exception as e:
                    logger.warning(f"종목 조회 실패 [{code}]: {e}")

        return candidates

    # ── Phase 2: 수급 분석 ──
    def _phase2_supply_analysis(self, candidates: list[StockCandidate]) -> list[StockCandidate]:
        filtered = []

        for c in candidates:
            is_aligned, near_high = self.engine.check_ma_alignment(c.code)
            if not is_aligned and not near_high:
                logger.debug(f"정배열 아님 → 제외: {c.name}")
                continue
            c.ma_aligned = is_aligned
            c.near_high = near_high

            supply = self.engine.analyze_supply_demand(c.code, c.current_price)
            c.inst_net_buy = supply["inst_net_buy"]
            c.frgn_net_buy = supply["frgn_net_buy"]
            c.prog_net_buy = supply["prog_net_buy"]
            c.supply_grade = supply["supply_grade"]
            c.supply_days = supply["supply_days"]

            if c.supply_grade == SupplyGrade.C:
                logger.debug(f"수급 없음 → 제외: {c.name}")
                continue

            filtered.append(c)
            time.sleep(0.5)

        filtered = self.engine.identify_sector_leaders(filtered)

        for c in filtered:
            self.engine.score_candidate(c)

        filtered.sort(key=lambda x: x.score, reverse=True)

        logger.info("=" * 60)
        logger.info("Phase 2 결과 (점수순)")
        logger.info("-" * 60)
        for i, c in enumerate(filtered[:10], 1):
            logger.info(
                f"  {i:2d}. [{c.supply_grade.name}] {c.name:10s} "
                f"점수={c.score:.0f}  등락={c.change_pct:+.1f}%  "
                f"기관={c.inst_net_buy/1e8:+,.0f}억  "
                f"외인={c.frgn_net_buy/1e8:+,.0f}억  "
                f"{'★대장' if c.is_leader else ''}"
            )
        return filtered

    # ── Phase 3: 매수 ──
    def _phase3_execute_buy(self, candidates: list[StockCandidate]):
        selected_sectors = set()
        buy_targets = []

        for c in candidates:
            if len(buy_targets) >= self.strategy_cfg.MAX_POSITIONS:
                break
            if c.sector in selected_sectors:
                continue
            buy_targets.append(c)
            selected_sectors.add(c.sector)

        if not buy_targets:
            logger.warning("매수 대상 없음 — 오늘은 관망")
            return

        logger.info(f"매수 대상: {[f'{t.name}({t.sector})' for t in buy_targets]}")

        for target in buy_targets:
            self.executor.execute_split_buy(target)

    # ── 유틸 ──
    def _find_sector(self, code: str) -> str:
        for sector, codes in self.strategy_cfg.WATCHLIST_SECTORS.items():
            if code in codes:
                return sector
        return "기타"

    def _wait_until(self, time_str: str):
        while True:
            now = datetime.now().strftime("%H:%M")
            if now >= time_str:
                return
            logger.info(f"대기 중... ({now} → {time_str})")
            time.sleep(30)


if __name__ == "__main__":
    strategy = ClosingBetStrategy()
    strategy.run()
