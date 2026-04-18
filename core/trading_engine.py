"""
종가베팅 비즈니스 로직
============================================================
모델(데이터클래스), 분석 엔진, 주문 실행기를 포함합니다.

[타임라인]
  13:00~14:30  사전 스크리닝 & 시장 분위기 파악
  14:30~15:00  수급 정밀 체크 & 매수 후보 확정
  15:00~15:20  분할 매수 실행
  익일 09:00~10:30  매도 실행
"""

import time
import logging
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from core.kiwoom_api import KiwoomRestAPI

logger = logging.getLogger("ClosingBet")


# ============================================================
# 모델 & 상수
# ============================================================

class StrategyConfig:
    """종가베팅 전략 파라미터 (API 설정과 분리)"""

    # ---- 필터 임계값 ----
    MIN_TRADING_VALUE = 100_000_000_000      # 거래대금 최소 1,000억
    PREFERRED_TRADING_VALUE = 200_000_000_000
    MIN_MARKET_CAP = 200_000_000_000         # 시총 최소 2,000억
    TOP_N_BY_VALUE = 20

    # ---- 이동평균 정배열 기준 ----
    MA_PERIODS = [5, 10, 20]

    # ---- 수급 기준 ----
    MIN_INST_NET_BUY_AMT = 1_000_000_000     # 기관 순매수 금액 최소 10억
    MIN_FRGN_NET_BUY_AMT = 1_000_000_000
    SUPPLY_CHECK_DAYS = 5

    # ---- 매매 설정 ----
    MAX_POSITIONS = 2
    SPLIT_COUNT = 3
    SPLIT_INTERVAL_SEC = 300
    MAX_POSITION_RATIO = 0.15
    PROFIT_TARGET = 0.02
    STOP_LOSS = -0.015
    MORNING_SELL_DEADLINE = "10:30"

    # ---- 매수/매도 시간대 ----
    SCREENING_START = "13:00"
    SUPPLY_CHECK_START = "14:30"
    BUY_WINDOW_START = "15:00"
    BUY_WINDOW_END = "15:20"

    # ---- 관심 섹터 (API 동적 로드, ka90001 + ka90002) ----
    WATCHLIST_SECTORS: dict[str, list[str]] = {}
    TOP_THEME_COUNT = 8           # 상위 테마 그룹 수
    THEME_PERIOD_DAYS = "10"      # 기간수익률 기준 일수
    THEME_STOCK_BONUS = 15        # 오늘의 테마주 가산점

    EXCLUDE_KEYWORDS = ["ETF", "ETN", "KODEX", "TIGER", "KBSTAR",
                        "ARIRANG", "SOL", "HANARO", "RISE"]

    # ---- 콘텐츠 분석 가산점 ----
    CONTENT_SCORE_MAX = 10            # 콘텐츠 분석 최대 가산점

    def load_from_db(self):
        """DB에서 전략 설정값을 로드하여 인스턴스에 덮어씀"""
        try:
            from core.repository.strategy_config import get_strategy_config
            config = get_strategy_config()
            for key, value in config.items():
                if hasattr(self, key) and key != "WATCHLIST_SECTORS":
                    setattr(self, key, value)
            logger.info("전략 설정 DB 로드 완료")
        except Exception as e:
            logger.warning(f"전략 설정 DB 로드 실패, 기본값 사용: {e}")


class SupplyGrade(Enum):
    S = "외국인+기관 양매수"
    A = "기관 강한 매수"
    B = "외국인 단독 매수"
    C = "해당없음"


@dataclass
class StockCandidate:
    code: str
    name: str
    sector: str
    current_price: int = 0
    trading_value: int = 0
    market_cap: int = 0
    change_pct: float = 0.0
    ma_aligned: bool = False
    near_high: bool = False
    supply_grade: SupplyGrade = SupplyGrade.C
    inst_net_buy: int = 0
    frgn_net_buy: int = 0
    indv_net_buy: int = 0
    prog_net_buy: int = 0
    supply_days: int = 0
    score: float = 0.0
    is_leader: bool = False
    is_theme_stock: bool = False
    market_suffix: str = "KS"  # yfinance suffix: KS=KOSPI, KQ=KOSDAQ
    supply_history: list = field(default_factory=list)  # 최근 5일 수급 현황
    hourly_candles: list = field(default_factory=list)  # 1시간봉 캔들 데이터
    content_count: int = 0        # 오늘 관련 콘텐츠 분석 건수
    content_avg_score: float = 0  # 콘텐츠 평균 sentiment_score


@dataclass
class Position:
    code: str
    name: str
    sector: str
    avg_price: float
    quantity: int
    bought_at: str
    splits_done: int = 0


# ============================================================
# 분석 엔진
# ============================================================

class AnalysisEngine:
    def __init__(self, api: KiwoomRestAPI, config: StrategyConfig):
        self.api = api
        self.cfg = config

    # ── 가격 문자열 파싱 (키움 응답은 "+53500", "-1200" 형태) ──
    @staticmethod
    def parse_price(val: str) -> int:
        if not val:
            return 0
        return int(val.replace("+", "").replace(",", ""))

    @staticmethod
    def parse_float(val: str) -> float:
        if not val:
            return 0.0
        return float(val.replace("+", "").replace(",", ""))

    # ── 기본 필터 ──
    def filter_basic(self, name: str, trading_val: int, market_cap: int) -> bool:
        if any(kw in name for kw in self.cfg.EXCLUDE_KEYWORDS):
            return False
        if market_cap > 0 and market_cap < self.cfg.MIN_MARKET_CAP:
            return False
        if trading_val < self.cfg.MIN_TRADING_VALUE:
            return False
        return True

    # ── 1시간봉 캔들 데이터 조회 ──
    def fetch_hourly_candles(self, stk_cd: str) -> list[dict]:
        """ka10080 연속조회로 1시간봉 1주일치(약 30~35개) 수집"""
        try:
            raw = self.api.get_minute_chart_pages(
                stk_cd, tic_scope="60", max_pages=3,
            )
            if not raw:
                return []

            candles = []
            for item in raw:
                cntr_tm = item.get("cntr_tm", "")
                if len(cntr_tm) < 12:
                    continue
                candles.append({
                    "time": f"{cntr_tm[:4]}-{cntr_tm[4:6]}-{cntr_tm[6:8]}T{cntr_tm[8:10]}:{cntr_tm[10:12]}",
                    "open": abs(self.parse_price(item.get("open_pric", "0"))),
                    "high": abs(self.parse_price(item.get("high_pric", "0"))),
                    "low": abs(self.parse_price(item.get("low_pric", "0"))),
                    "close": abs(self.parse_price(item.get("cur_prc", "0"))),
                    "volume": abs(self.parse_price(item.get("trde_qty", "0"))),
                })

            # API 응답은 최신순 → 오래된순으로 정렬
            candles.sort(key=lambda x: x["time"])
            return candles
        except Exception as e:
            logger.warning(f"1시간봉 조회 실패 [{stk_cd}]: {e}")
            return []

    # ── 이동평균 정배열 판단 ──
    def check_ma_alignment(self, stk_cd: str) -> tuple[bool, bool]:
        """일봉 차트(ka10081)로 정배열 + 신고가 근처 판단"""
        try:
            data = self.api.get_daily_chart(stk_cd)
            candles = data.get("stk_dt_pole_chart_qry", [])
            logger.debug(f"[{stk_cd}] 일봉 {len(candles)}개 조회")
            if not candles or len(candles) < 120:
                return False, False

            closes = [abs(self.parse_price(c.get("cur_prc", "0"))) for c in candles]
            closes = [p for p in closes if p > 0]

            if len(closes) < 120:
                return False, False

            # 이동평균 계산
            mas = {}
            for period in self.cfg.MA_PERIODS:
                if len(closes) >= period:
                    mas[period] = sum(closes[:period]) / period

            # 정배열 조건 체크
            periods = [p for p in self.cfg.MA_PERIODS if p in mas]

            # (1) 5MA > 10MA > 20MA
            ma_ordered = all(
                mas[periods[i]] > mas[periods[i + 1]]
                for i in range(len(periods) - 1)
            )

            # (2) 종가가 5일선 위
            close_above_ma5 = closes[0] > mas[5] if 5 in mas else False

            # (3) 5일선 기울기 상승 (오늘 5MA > 어제 5MA)
            if len(closes) >= 6:
                ma5_prev = sum(closes[1:6]) / 5
                ma5_rising = mas[5] > ma5_prev
            else:
                ma5_rising = False

            is_aligned = ma_ordered and close_above_ma5 and ma5_rising

            # 역배열 체크 (즉시 제외 대상)
            is_reverse = len(periods) >= 3 and all(
                mas[periods[i]] < mas[periods[i + 1]]
                for i in range(len(periods) - 1)
            )
            if is_reverse:
                return False, False

            # 52주(약 250거래일) 신고가 근처 (95% 이상)
            high_range = min(len(closes), 250)
            high_52w = max(closes[:high_range])
            near_high = closes[0] >= high_52w * 0.95

            return is_aligned, near_high

        except Exception as e:
            logger.warning(f"차트 분석 실패 [{stk_cd}]: {e}")
            return False, False

    # ── 수급 분석 ──
    def analyze_supply_demand(self, stk_cd: str, current_price: int) -> dict:
        result = {
            "inst_net_buy": 0,
            "frgn_net_buy": 0,
            "indv_net_buy": 0,
            "prog_net_buy": 0,
            "supply_grade": SupplyGrade.C,
            "supply_days": 0,
            "foreign_brokers_buying": False,
            "supply_history": [],
        }

        # (a) 장중 투자자별 매매 (ka10059) — 14:30 이후 잠정치
        try:
            inv_data = self.api.get_intraday_investor(stk_cd)
            items = inv_data.get("stk_invsr_orgn", [])
            if items:
                today = items[0]
                result["inst_net_buy"] = self.parse_price(
                    today.get("orgn", "0")) * 1_000_000
                result["frgn_net_buy"] = self.parse_price(
                    today.get("frgnr_invsr", "0")) * 1_000_000
                result["indv_net_buy"] = self.parse_price(
                    today.get("ind_invsr", "0")) * 1_000_000

                # 최근 5일 수급 현황 추출
                for item in items[:5]:
                    raw_dt = item.get("dt", "")
                    if len(raw_dt) == 8:
                        formatted_dt = f"{raw_dt[:4]}-{raw_dt[4:6]}-{raw_dt[6:]}"
                    else:
                        formatted_dt = raw_dt
                    result["supply_history"].append({
                        "date": formatted_dt,
                        "inst_net_buy": self.parse_price(item.get("orgn", "0")) * 1_000_000,
                        "frgn_net_buy": self.parse_price(item.get("frgnr_invsr", "0")) * 1_000_000,
                        "indv_net_buy": self.parse_price(item.get("ind_invsr", "0")) * 1_000_000,
                    })
            else:
                logger.debug(f"[{stk_cd}] ka10059 stk_invsr_orgn 비어있음")
        except Exception as e:
            logger.warning(f"장중투자자 조회 실패 [{stk_cd}]: {e}")

        # (b) 프로그램 매매 현황 (ka90004)
        try:
            prog_data = self.api.get_program_trade_by_stock()
            items = prog_data.get("stk_prm_trde_prst", [])
            for item in items:
                if item.get("stk_cd", "") == stk_cd:
                    result["prog_net_buy"] = self.parse_price(
                        item.get("netprps_prica", "0")) * 1_000_000
                    break
        except Exception as e:
            logger.warning(f"프로그램매매 조회 실패 [{stk_cd}]: {e}")

        # (c) 기관외국인 연속매매현황 (ka10131)
        try:
            consec_data = self.api.get_inst_foreign_consecutive()
            items = consec_data.get("orgn_frgnr_cont_trde_prst", [])
            for item in items:
                if item.get("stk_cd", "") == stk_cd:
                    result["supply_days"] = abs(self.parse_price(
                        item.get("tot_cont_netprps_dys", "0")))
                    break
        except Exception as e:
            logger.warning(f"연속매매현황 조회 실패 [{stk_cd}]: {e}")

        # (d) 거래원 체크 (ka10002) — 외국계 증권사 매수 우위
        FOREIGN_BROKERS = [
            "모간", "골드만", "메릴", "CS", "UBS", "JP모간",
            "씨티", "CLSA", "맥쿼리", "노무라", "BNP", "도이치",
            "바클레이", "크레디", "제이피"
        ]
        try:
            broker_data = self.api.get_stock_broker(stk_cd)
            buy_broker_names = [
                broker_data.get(f"buy_trde_ori_nm_{i}", "")
                for i in range(1, 6)
            ]
            foreign_count = sum(
                1 for name in buy_broker_names
                if any(fb in name for fb in FOREIGN_BROKERS)
            )
            result["foreign_brokers_buying"] = foreign_count >= 2
        except Exception as e:
            logger.warning(f"거래원 조회 실패 [{stk_cd}]: {e}")

        # (e) 수급 등급 판정
        inst_strong = abs(result["inst_net_buy"]) >= self.cfg.MIN_INST_NET_BUY_AMT \
                      and result["inst_net_buy"] > 0
        frgn_strong = (
            (abs(result["frgn_net_buy"]) >= self.cfg.MIN_FRGN_NET_BUY_AMT
             and result["frgn_net_buy"] > 0)
            or result["prog_net_buy"] > 0
            or result["foreign_brokers_buying"]
        )

        if inst_strong and frgn_strong:
            result["supply_grade"] = SupplyGrade.S
        elif inst_strong:
            result["supply_grade"] = SupplyGrade.A
        elif frgn_strong:
            result["supply_grade"] = SupplyGrade.B
        else:
            result["supply_grade"] = SupplyGrade.C

        return result

    # ── 섹터 대장주 판별 ──
    def identify_sector_leaders(self, candidates: list[StockCandidate]) -> list[StockCandidate]:
        sector_map: dict[str, list[StockCandidate]] = {}
        for c in candidates:
            sector_map.setdefault(c.sector, []).append(c)

        for sector, stocks in sector_map.items():
            stocks.sort(key=lambda s: s.change_pct, reverse=True)
            if stocks:
                stocks[0].is_leader = True
                logger.info(f"[{sector}] 대장주: {stocks[0].name} ({stocks[0].change_pct:+.2f}%)")

        return candidates

    # ── 종합 스코어링 ──
    def score_candidate(self, c: StockCandidate) -> float:
        score = 0.0

        # 수급 등급 (40점)
        grade_scores = {SupplyGrade.S: 40, SupplyGrade.A: 30,
                        SupplyGrade.B: 15, SupplyGrade.C: 0}
        score += grade_scores[c.supply_grade]

        # 정배열 + 신고가 (20점)
        if c.ma_aligned:
            score += 10
        if c.near_high:
            score += 10

        # 거래대금 (15점)
        if c.trading_value >= self.cfg.PREFERRED_TRADING_VALUE:
            score += 15
        elif c.trading_value >= self.cfg.MIN_TRADING_VALUE:
            score += 8

        # 대장주 (10점)
        if c.is_leader:
            score += 10

        # 오늘의 테마주 가산점
        if c.is_theme_stock:
            score += self.cfg.THEME_STOCK_BONUS

        # 연속 수급 (15점)
        score += min(c.supply_days, 5) * 3

        # 콘텐츠 분석 (10점): 언급 횟수 + 평균 감성 점수
        if c.content_count > 0:
            mention_bonus = min(c.content_count, 3) * 2  # max 6
            sentiment_bonus = (
                4 if c.content_avg_score >= 70
                else 2 if c.content_avg_score >= 50
                else 0
            )
            score += min(mention_bonus + sentiment_bonus, self.cfg.CONTENT_SCORE_MAX)

        c.score = score
        return score


# ============================================================
# 주문 실행기
# ============================================================

class OrderExecutor:
    def __init__(self, api: KiwoomRestAPI, config: StrategyConfig):
        self.api = api
        self.cfg = config
        self.positions: list[Position] = []

    def get_available_cash(self) -> int:
        data = self.api.get_deposit()
        return int(data.get("ord_alow_amt", "0").replace(",", ""))

    def execute_split_buy(self, candidate: StockCandidate) -> Optional[Position]:
        cash = self.get_available_cash()
        max_budget = int(cash * self.cfg.MAX_POSITION_RATIO)
        qty_per_split = max(1, (max_budget // self.cfg.SPLIT_COUNT) // candidate.current_price)

        if qty_per_split < 1:
            logger.warning(f"매수 자금 부족: {candidate.name}")
            return None

        total_qty = 0
        total_cost = 0

        for i in range(self.cfg.SPLIT_COUNT):
            now = datetime.now().strftime("%H:%M")
            if now > self.cfg.BUY_WINDOW_END:
                logger.info(f"매수 시간 종료, {i}회차까지 체결")
                break

            # 현재가 재확인
            try:
                info = self.api.get_stock_basic_info(candidate.code)
                price = AnalysisEngine.parse_price(info.get("cur_prc", "0"))
                if price <= 0:
                    price = candidate.current_price
            except Exception:
                price = candidate.current_price

            # 매수 주문 (kt10000)
            try:
                result = self.api.place_buy_order(
                    stk_cd=candidate.code,
                    qty=qty_per_split,
                    price=price,
                    trde_tp="0",
                )
                ord_no = result.get("ord_no", "N/A")
                logger.info(
                    f"[매수 {i+1}/{self.cfg.SPLIT_COUNT}] {candidate.name} "
                    f"{qty_per_split}주 @ {price:,}원 (주문번호: {ord_no})"
                )
                total_qty += qty_per_split
                total_cost += qty_per_split * price
            except Exception as e:
                logger.error(f"매수 주문 실패: {e}")
                break

            if i < self.cfg.SPLIT_COUNT - 1:
                time.sleep(self.cfg.SPLIT_INTERVAL_SEC)

        if total_qty > 0:
            pos = Position(
                code=candidate.code,
                name=candidate.name,
                sector=candidate.sector,
                avg_price=total_cost / total_qty,
                quantity=total_qty,
                bought_at=datetime.now().isoformat(),
                splits_done=min(i + 1, self.cfg.SPLIT_COUNT),
            )
            self.positions.append(pos)
            logger.info(f"매수 완료: {candidate.name} 총 {total_qty}주, 평단 {pos.avg_price:,.0f}원")
            return pos
        return None

    def execute_morning_sell(self):
        """익일 오전 매도 — 목표가/손절/시간마감"""
        for pos in list(self.positions):
            sold = False
            while not sold:
                now = datetime.now().strftime("%H:%M")

                try:
                    info = self.api.get_stock_basic_info(pos.code)
                    current = AnalysisEngine.parse_price(info.get("cur_prc", "0"))
                except Exception:
                    time.sleep(5)
                    continue

                if current <= 0:
                    time.sleep(5)
                    continue

                pnl_pct = (current - pos.avg_price) / pos.avg_price

                if pnl_pct >= self.cfg.PROFIT_TARGET:
                    logger.info(f"[목표달성] {pos.name} {pnl_pct:.2%} → 매도")
                    self._sell_all(pos, current)
                    sold = True
                elif pnl_pct <= self.cfg.STOP_LOSS:
                    logger.info(f"[손절] {pos.name} {pnl_pct:.2%} → 매도")
                    self._sell_all(pos, current)
                    sold = True
                elif now >= self.cfg.MORNING_SELL_DEADLINE:
                    logger.info(f"[시간마감] {pos.name} {pnl_pct:.2%} → 매도")
                    self._sell_all(pos, current, market=True)
                    sold = True
                else:
                    time.sleep(10)

    def _sell_all(self, pos: Position, price: int, market: bool = False):
        """전량 매도 (kt10001)"""
        try:
            result = self.api.place_sell_order(
                stk_cd=pos.code,
                qty=pos.quantity,
                price=price,
                trde_tp="3" if market else "0",
            )
            ord_no = result.get("ord_no", "N/A")
            logger.info(f"매도 완료: {pos.name} {pos.quantity}주 (주문번호: {ord_no})")
            self.positions.remove(pos)
        except Exception as e:
            logger.error(f"매도 실패 [{pos.name}]: {e}")
