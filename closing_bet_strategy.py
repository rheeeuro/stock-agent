
"""
종가베팅 알고리즘 v2.0 — 키움 REST API 공식 명세 기반
============================================================
도메인: api.kiwoom.com (운영) / mockapi.kiwoom.com (모의투자)
인증:   au10001 (OAuth2 토큰 발급)
헤더:   authorization, api-id, cont-yn, next-key

[타임라인]
  13:00~14:30  사전 스크리닝 & 시장 분위기 파악
  14:30~15:00  수급 정밀 체크 & 매수 후보 확정
  15:00~15:20  분할 매수 실행
  익일 09:00~10:30  매도 실행

[사용 TR 목록]
  au10001  접근토큰 발급          POST /oauth2/token
  au10002  접근토큰 폐기          POST /oauth2/token
  ka10001  주식기본정보요청        POST /api/dostk/stkinfo
  ka10002  주식거래원요청          POST /api/dostk/stkinfo
  ka10032  거래대금상위요청        POST /api/dostk/rkinfo
  ka10059  종목별투자자기관별요청  POST /api/dostk/stkinfo
  ka10063  장중투자자별매매요청    POST /api/dostk/mrktpr
  ka10081  주식일봉차트조회요청    POST /api/dostk/chart
  ka10131  기관외국인연속매매현황  POST /api/dostk/frgnistt
  ka90004  종목별프로그램매매현황  POST /api/dostk/stkinfo
  ka90008  종목시간별프로그램매매  POST /api/dostk/mrktpr
  ka90009  외국인기관매매상위요청  POST /api/dostk/rkinfo
  kt00001  예수금상세현황요청      POST /api/dostk/acnt
  kt00018  계좌평가잔고내역요청    POST /api/dostk/acnt
  kt10000  주식 매수주문           POST /api/dostk/ordr
  kt10001  주식 매도주문           POST /api/dostk/ordr
"""

import os
import requests
import time
import logging
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ClosingBet")


# ============================================================
# 1. 설정 & 상수
# ============================================================

class Config:
    # ---- 키움 REST API ----
    BASE_URL = "https://api.kiwoom.com"           # 운영 도메인
    MOCK_URL = "https://mockapi.kiwoom.com"        # 모의투자 (KRX만 지원)
    USE_MOCK = False                                # True면 모의투자 사용

    APP_KEY = os.getenv("KIWOOM_APP_KEY", "")
    SECRET_KEY = os.getenv("KIWOOM_SECRET_KEY", "")
    ACCESS_TOKEN = ""

    # ---- URL 패턴 (키움 REST API 공식 엔드포인트) ----
    URL_TOKEN  = "/oauth2/token"        # 토큰 발급
    URL_STKINFO = "/api/dostk/stkinfo"  # 종목정보 (ka10001, ka10002, ka90004 등)
    URL_MRKTPR  = "/api/dostk/mrktpr"   # 시세 (ka10005, ka10063, ka90008 등)
    URL_RKINFO  = "/api/dostk/rkinfo"   # 순위정보 (ka10032, ka90009 등)
    URL_FRINST  = "/api/dostk/frgnistt"  # 기관/외국인 (ka10008, ka10009, ka10131)
    URL_CHART   = "/api/dostk/chart"    # 차트 (ka10081 등)
    URL_ORDR    = "/api/dostk/ordr"     # 주문 (kt10000, kt10001 등)
    URL_ACNT    = "/api/dostk/acnt"     # 계좌 (kt00001, kt00018 등)

    # ---- 필터 임계값 ----
    MIN_TRADING_VALUE = 100_000_000_000      # 거래대금 최소 1,000억
    PREFERRED_TRADING_VALUE = 200_000_000_000
    MIN_MARKET_CAP = 200_000_000_000         # 시총 최소 2,000억
    TOP_N_BY_VALUE = 20

    # ---- 이동평균 정배열 기준 ----
    MA_PERIODS = [5, 20, 60, 120]

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
    EXCHANGE = "KRX"                          # KRX, NXT, SOR

    # ---- 매수/매도 시간대 ----
    SCREENING_START = "13:00"
    SUPPLY_CHECK_START = "14:30"
    BUY_WINDOW_START = "15:00"
    BUY_WINDOW_END = "15:20"

    # ---- 관심 섹터 (사용자 정의) ----
    WATCHLIST_SECTORS = {
        "반도체": ["005930", "000660", "042700", "058470"],
        "2차전지": ["373220", "006400", "051910", "003670"],
        "바이오": ["207940", "068270", "326030", "145020"],
        "AI/SW":  ["035420", "035720", "036570", "259960"],
        "방산":   ["012450", "047810", "084680", "299660"],
        "조선":   ["010140", "009540", "042660"],
        "로봇":   ["454910", "108320", "090460"],
    }

    EXCLUDE_KEYWORDS = ["ETF", "ETN", "KODEX", "TIGER", "KBSTAR",
                        "ARIRANG", "SOL", "HANARO", "RISE"]


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
    prog_net_buy: int = 0
    supply_days: int = 0
    score: float = 0.0
    is_leader: bool = False


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
# 2. 키움 REST API 클라이언트
# ============================================================

class KiwoomRestAPI:
    """
    키움증권 REST API 래퍼 — 공식 명세 기반
    모든 TR은 POST 방식, JSON Body로 요청
    """

    def __init__(self, config: Config):
        self.cfg = config
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json;charset=UTF-8"
        })

    @property
    def base_url(self) -> str:
        return self.cfg.MOCK_URL if self.cfg.USE_MOCK else self.cfg.BASE_URL

    # ────────────────────────────────────────────
    # 인증
    # ────────────────────────────────────────────
    def get_access_token(self):
        """au10001 — 접근토큰 발급"""
        url = f"{self.base_url}{self.cfg.URL_TOKEN}"
        body = {
            "grant_type": "client_credentials",
            "appkey": self.cfg.APP_KEY,
            "secretkey": self.cfg.SECRET_KEY,
        }
        resp = self.session.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()
        self.cfg.ACCESS_TOKEN = data["token"]
        logger.info(f"토큰 발급 완료 (만료: {data.get('expires_dt', 'N/A')})")

    def revoke_access_token(self):
        """au10002 — 접근토큰 폐기"""
        url = f"{self.base_url}{self.cfg.URL_TOKEN}"
        body = {
            "appkey": self.cfg.APP_KEY,
            "secretkey": self.cfg.SECRET_KEY,
            "token": self.cfg.ACCESS_TOKEN,
        }
        try:
            resp = self.session.post(url, json=body, headers={"api-id": "au10002"})
            resp.raise_for_status()
            self.cfg.ACCESS_TOKEN = ""
            logger.info("토큰 폐기 완료")
        except Exception as e:
            logger.warning(f"토큰 폐기 실패: {e}")

    # ────────────────────────────────────────────
    # 공통 요청 메서드
    # ────────────────────────────────────────────
    def _headers(self, api_id: str, cont_yn: str = "", next_key: str = "") -> dict:
        """키움 REST API 공통 헤더"""
        h = {
            "authorization": f"Bearer {self.cfg.ACCESS_TOKEN}",
            "api-id": api_id,
            "Content-Type": "application/json;charset=UTF-8",
        }
        if cont_yn:
            h["cont-yn"] = cont_yn
        if next_key:
            h["next-key"] = next_key
        return h

    def _post(self, url_path: str, api_id: str, body: dict,
              cont_yn: str = "", next_key: str = "",
              max_retries: int = 3) -> dict:
        """POST 요청 공통 (429 rate limit 자동 재시도)"""
        url = f"{self.base_url}{url_path}"
        headers = self._headers(api_id, cont_yn, next_key)
        for attempt in range(max_retries):
            resp = self.session.post(url, headers=headers, json=body)
            if resp.status_code == 429:
                wait = 1.0 * (attempt + 1)
                logger.warning(f"[{api_id}] 429 rate limit — {wait:.0f}초 대기 후 재시도 ({attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            if data.get("return_code", 0) != 0:
                logger.warning(f"[{api_id}] {data.get('return_msg', 'Unknown error')}")
            time.sleep(0.15)
            return data
        resp.raise_for_status()
        return {}

    # ────────────────────────────────────────────
    # 종목정보 (/api/dostk/stkinfo)
    # ────────────────────────────────────────────
    def get_stock_basic_info(self, stk_cd: str) -> dict:
        """
        ka10001 — 주식기본정보요청
        응답: stk_cd, stk_nm, cur_prc, pred_pre, pre_sig, mac(시가총액),
              trde_qty, flo_stk, oyr_hgst, oyr_lwst, 250hgst, 250lwst 등
        """
        return self._post(self.cfg.URL_STKINFO, "ka10001", {
            "stk_cd": stk_cd,
        })

    def get_stock_broker(self, stk_cd: str) -> dict:
        """
        ka10002 — 주식거래원요청
        응답: 매도상위5/매수상위5 거래원 정보
        """
        return self._post(self.cfg.URL_STKINFO, "ka10002", {
            "stk_cd": stk_cd,
        })

    def get_investor_by_stock(self, stk_cd: str) -> dict:
        """
        ka10059 — 종목별투자자기관별요청
        응답: 개인/외국인/기관 순매수 수량·금액
        """
        return self._post(self.cfg.URL_STKINFO, "ka10059", {
            "stk_cd": stk_cd,
            "dt": datetime.now().strftime("%Y%m%d"),
            "amt_qty_tp": "1",  # 1:금액, 2:수량
            "trde_tp": "0",     # 0:순매수, 1:매수, 2:매도
            "unit_tp": "1000",  # 1000:천주, 1:단주
        })

    def get_program_trade_by_stock(self, mrkt_tp: str = "P00101") -> dict:
        """
        ka90004 — 종목별프로그램매매현황요청
        시장 전체 종목별 프로그램 매매 현황 조회
        응답: stk_prm_trde_prst (LIST) — stk_cd, netprps_prica 등
        """
        return self._post(self.cfg.URL_STKINFO, "ka90004", {
            "dt": datetime.now().strftime("%Y%m%d"),
            "mrkt_tp": mrkt_tp,
            "stex_tp": "3",
        })

    # ────────────────────────────────────────────
    # 시세 (/api/dostk/mrktpr)
    # ────────────────────────────────────────────
    def get_intraday_investor(self, stk_cd: str) -> dict:
        """ka10059 — 종목별투자자기관별요청 (ka10063 대체)"""
        return self.get_investor_by_stock(stk_cd)

    def get_program_trade_hourly(self, stk_cd: str) -> dict:
        """
        ka90008 — 종목시간별프로그램매매추이요청
        시간대별 프로그램 매매 추이 (외국인 프로그램 확인)
        응답: stk_tm_prm_trde_trnsn (LIST)
        """
        return self._post(self.cfg.URL_MRKTPR, "ka90008", {
            "amt_qty_tp": "1",      # 1:금액, 2:수량
            "stk_cd": stk_cd,
            "date": datetime.now().strftime("%Y%m%d"),
        })

    # ────────────────────────────────────────────
    # 순위정보 (/api/dostk/rkinfo)
    # ────────────────────────────────────────────
    def get_trading_value_rank(self, mrkt_tp: str = "001") -> dict:
        """
        ka10032 — 거래대금상위요청
        mrkt_tp: 001=코스피, 101=코스닥
        """
        return self._post(self.cfg.URL_RKINFO, "ka10032", {
            "mrkt_tp": mrkt_tp,
            "mang_stk_incls": "0",  # 관리종목 미포함
            "stex_tp": "3",         # 1:KRX, 2:NXT 3.통합
        })

    def get_foreign_inst_top(self, mrkt_tp: str = "001") -> dict:
        """
        ka90009 — 외국인기관매매상위요청
        응답: frgnr_orgn_trde_upper (LIST)
        """
        return self._post(self.cfg.URL_RKINFO, "ka90009", {
            "mrkt_tp": mrkt_tp,
            "amt_qty_tp": "1",      # 1:금액(천만), 2:수량(천)
            "qry_dt_tp": "1",       # 1:조회일자 포함
            "date": datetime.now().strftime("%Y%m%d"),
            "stex_tp": "3",         # 통합
        })

    def get_foreign_broker_top(self, mrkt_tp: str = "001") -> dict:
        """
        ka10037 — 외국계창구매매상위요청
        외국계 증권사 창구 순매수 상위
        """
        return self._post(self.cfg.URL_RKINFO, "ka10037", {
            "mrkt_tp": mrkt_tp,
            "sort_tp": "1",
            "trde_qty_tp": "0000",
            "stk_cnd": "1",
            "crd_cnd": "0",
            "stex_tp": "1",
        })

    def get_foreign_consecutive_buy(self, mrkt_tp: str = "001") -> dict:
        """
        ka10035 — 외인연속순매매상위요청
        """
        return self._post(self.cfg.URL_RKINFO, "ka10035", {
            "mrkt_tp": mrkt_tp,
            "sort_tp": "1",
            "trde_qty_tp": "0000",
            "stk_cnd": "1",
            "crd_cnd": "0",
            "stex_tp": "1",
        })

    # ────────────────────────────────────────────
    # 기관/외국인 (/api/dostk/frinst)
    # ────────────────────────────────────────────
    def get_inst_foreign_consecutive(self, mrkt_tp: str = "001") -> dict:
        """
        ka10131 — 기관외국인연속매매현황요청
        시장 전체 기관/외국인 연속 순매수 랭킹 조회
        응답: orgn_frgnr_cont_trde_prst (LIST)
        """
        return self._post(self.cfg.URL_FRINST, "ka10131", {
            "dt": "5",
            "strt_dt": "",
            "end_dt": "",
            "mrkt_tp": mrkt_tp,
            "netslmt_tp": "2",       # 순매수 고정
            "stk_inds_tp": "0",      # 종목(주식)
            "amt_qty_tp": "0",       # 금액
            "stex_tp": "3",          # 통합
        })

    def get_foreign_trend(self, stk_cd: str) -> dict:
        """
        ka10008 — 주식외국인종목별매매동향
        """
        return self._post(self.cfg.URL_FRINST, "ka10008", {
            "stk_cd": stk_cd,
        })

    def get_institution_trend(self, stk_cd: str) -> dict:
        """
        ka10009 — 주식기관요청
        """
        return self._post(self.cfg.URL_FRINST, "ka10009", {
            "stk_cd": stk_cd,
        })

    # ────────────────────────────────────────────
    # 차트 (/api/dostk/chart)
    # ────────────────────────────────────────────
    def get_daily_chart(self, stk_cd: str, dt: str = "",
                        upd_stk_prc: str = "1") -> dict:
        """
        ka10081 — 주식일봉차트조회요청
        dt: 기준일자 (YYYYMMDD, 빈값=오늘)
        upd_stk_prc: 수정주가 사용 여부 (1:사용)
        응답: stk_dt_pole (LIST) — dt, open_prc, high_prc, low_prc,
              cur_prc, trde_qty 등
        """
        if not dt:
            dt = datetime.now().strftime("%Y%m%d")
        body = {"stk_cd": stk_cd, "base_dt": dt, "upd_stkpc_tp": upd_stk_prc}
        return self._post(self.cfg.URL_CHART, "ka10081", body)

    # ────────────────────────────────────────────
    # 주문 (/api/dostk/ordr)
    # ────────────────────────────────────────────
    def place_buy_order(self, stk_cd: str, qty: int, price: int,
                        trde_tp: str = "0") -> dict:
        """
        kt10000 — 주식 매수주문
        trde_tp: 0=보통(지정가), 3=시장가, 5=조건부지정가,
                 6=최유리, 7=최우선, 81=장마감후시간외
        """
        body = {
            "dmst_stex_tp": self.cfg.EXCHANGE,
            "stk_cd": stk_cd,
            "ord_qty": str(qty),
            "trde_tp": trde_tp,
        }
        if trde_tp == "0":  # 지정가일 때만 단가 필요
            body["ord_uv"] = str(price)
        return self._post(self.cfg.URL_ORDR, "kt10000", body)

    def place_sell_order(self, stk_cd: str, qty: int, price: int,
                         trde_tp: str = "0") -> dict:
        """
        kt10001 — 주식 매도주문
        """
        body = {
            "dmst_stex_tp": self.cfg.EXCHANGE,
            "stk_cd": stk_cd,
            "ord_qty": str(qty),
            "trde_tp": trde_tp,
        }
        if trde_tp == "0":
            body["ord_uv"] = str(price)
        return self._post(self.cfg.URL_ORDR, "kt10001", body)

    # ────────────────────────────────────────────
    # 계좌 (/api/dostk/acnt)
    # ────────────────────────────────────────────
    def get_deposit(self) -> dict:
        """kt00001 — 예수금상세현황요청"""
        return self._post(self.cfg.URL_ACNT, "kt00001", {
            "qry_tp": "3",  # 3:추정조회, 2:일반조회
        })

    def get_evaluation_balance(self) -> dict:
        """
        kt00018 — 계좌평가잔고내역요청
        응답: tot_evlt_amt, tot_pur_amt, tot_evlt_pl, acnt_evlt_remn_indv_tot (LIST) 등
        """
        return self._post(self.cfg.URL_ACNT, "kt00018", {
            "qry_tp": "1",              # 1:합산, 2:개별
            "dmst_stex_tp": "KRX",      # KRX:한국거래소, NXT:넥스트트레이드
        })

    # ────────────────────────────────────────────
    # 유틸: 연속조회 처리
    # ────────────────────────────────────────────
    def fetch_all_pages(self, url_path: str, api_id: str, body: dict,
                        list_key: str, max_pages: int = 5) -> list:
        """연속조회(cont-yn/next-key) 자동 처리"""
        all_items = []
        cont_yn = ""
        next_key = ""

        for _ in range(max_pages):
            url = f"{self.base_url}{url_path}"
            headers = self._headers(api_id, cont_yn, next_key)
            resp = self.session.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()

            items = data.get(list_key, [])
            all_items.extend(items)

            # 응답 헤더에서 연속조회 정보 확인
            resp_cont = resp.headers.get("cont-yn", "N")
            resp_next = resp.headers.get("next-key", "")

            if resp_cont != "Y" or not resp_next:
                break

            cont_yn = resp_cont
            next_key = resp_next
            time.sleep(0.3)

        return all_items


# ============================================================
# 3. 분석 엔진
# ============================================================

class AnalysisEngine:
    def __init__(self, api: KiwoomRestAPI, config: Config):
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

    # ── 3-1. 기본 필터 ──
    def filter_basic(self, name: str, trading_val: int, market_cap: int) -> bool:
        if any(kw in name for kw in self.cfg.EXCLUDE_KEYWORDS):
            return False
        if market_cap > 0 and market_cap < self.cfg.MIN_MARKET_CAP:
            return False
        if trading_val < self.cfg.MIN_TRADING_VALUE:
            return False
        return True

    # ── 3-2. 이동평균 정배열 판단 ──
    def check_ma_alignment(self, stk_cd: str) -> tuple[bool, bool]:
        """일봉 차트(ka10081)로 정배열 + 신고가 근처 판단"""
        try:
            data = self.api.get_daily_chart(stk_cd)
            candles = data.get("stk_dt_pole_chart_qry", [])
            logger.debug(f"[{stk_cd}] 일봉 {len(candles)}개 조회")
            if not candles or len(candles) < 120:
                return False, False

            closes = [self.parse_price(c.get("cur_prc", "0")) for c in candles]
            closes = [p for p in closes if p > 0]

            if len(closes) < 120:
                return False, False

            # 이동평균 계산
            mas = {}
            for period in self.cfg.MA_PERIODS:
                if len(closes) >= period:
                    mas[period] = sum(closes[:period]) / period

            # 정배열: 5MA > 20MA > 60MA > 120MA
            periods = [p for p in self.cfg.MA_PERIODS if p in mas]
            is_aligned = all(
                mas[periods[i]] > mas[periods[i + 1]]
                for i in range(len(periods) - 1)
            )

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

    # ── 3-3. 수급 분석 ──
    def analyze_supply_demand(self, stk_cd: str, current_price: int) -> dict:
        result = {
            "inst_net_buy": 0,
            "frgn_net_buy": 0,
            "prog_net_buy": 0,
            "supply_grade": SupplyGrade.C,
            "supply_days": 0,
            "foreign_brokers_buying": False,
        }

        # (a) 장중 투자자별 매매 (ka10063) — 14:30 이후 잠정치
        try:
            inv_data = self.api.get_intraday_investor(stk_cd)
            logger.debug(f"[{stk_cd}] ka10059 응답 키: {list(inv_data.keys())}")
            # stk_invsr_orgn 리스트의 첫 번째 항목(당일)에서 추출
            items = inv_data.get("stk_invsr_orgn", [])
            if items:
                today = items[0]
                logger.debug(f"[{stk_cd}] ka10059 항목 값: orgn={today.get('orgn')}, frgnr={today.get('frgnr_invsr')}")
                # ka10059 응답은 백만원 단위 → 원 단위로 변환
                result["inst_net_buy"] = self.parse_price(
                    today.get("orgn", "0")) * 1_000_000
                result["frgn_net_buy"] = self.parse_price(
                    today.get("frgnr_invsr", "0")) * 1_000_000
            else:
                logger.debug(f"[{stk_cd}] ka10059 stk_invsr_orgn 비어있음")
        except Exception as e:
            logger.warning(f"장중투자자 조회 실패 [{stk_cd}]: {e}")

        # (b) 프로그램 매매 현황 (ka90004) — 외국인 프로그램 매매 확인
        #     시장 전체 리스트에서 해당 종목 찾기
        try:
            prog_data = self.api.get_program_trade_by_stock()
            items = prog_data.get("stk_prm_trde_prst", [])
            for item in items:
                if item.get("stk_cd", "") == stk_cd:
                    # ka90004 응답도 백만원 단위 → 원 단위로 변환
                    result["prog_net_buy"] = self.parse_price(
                        item.get("netprps_prica", "0")) * 1_000_000
                    break
        except Exception as e:
            logger.warning(f"프로그램매매 조회 실패 [{stk_cd}]: {e}")

        # (c) 기관외국인 연속매매현황 (ka10131) — 연속 순매수 일수
        #     시장 전체 랭킹에서 해당 종목 찾기
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
            result["supply_grade"] = SupplyGrade.S  # 1순위: 양매수
        elif inst_strong:
            result["supply_grade"] = SupplyGrade.A  # 2순위: 기관수급
        elif frgn_strong:
            result["supply_grade"] = SupplyGrade.B  # 3순위: 외국인 단독
        else:
            result["supply_grade"] = SupplyGrade.C

        return result

    # ── 3-4. 섹터 대장주 판별 ──
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

    # ── 3-5. 종합 스코어링 ──
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

        # 연속 수급 (15점)
        score += min(c.supply_days, 5) * 3

        c.score = score
        return score


# ============================================================
# 4. 주문 실행기
# ============================================================

class OrderExecutor:
    def __init__(self, api: KiwoomRestAPI, config: Config):
        self.api = api
        self.cfg = config
        self.positions: list[Position] = []

    def get_available_cash(self) -> int:
        data = self.api.get_deposit()
        # kt00001 응답에서 주문가능금액 추출
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
                    trde_tp="0",  # 보통(지정가)
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
                trde_tp="3" if market else "0",  # 시간마감 시 시장가
            )
            ord_no = result.get("ord_no", "N/A")
            logger.info(f"매도 완료: {pos.name} {pos.quantity}주 (주문번호: {ord_no})")
            self.positions.remove(pos)
        except Exception as e:
            logger.error(f"매도 실패 [{pos.name}]: {e}")


# ============================================================
# 5. 메인 전략 오케스트레이터
# ============================================================

class ClosingBetStrategy:
    def __init__(self):
        self.cfg = Config()
        self.api = KiwoomRestAPI(self.cfg)
        self.engine = AnalysisEngine(self.api, self.cfg)
        self.executor = OrderExecutor(self.api, self.cfg)

    def run(self):
        logger.info("=" * 60)
        logger.info("종가베팅 알고리즘 v2.0 (키움 REST API)")
        logger.info("=" * 60)

        # 0. 인증 (au10001)
        self.api.get_access_token()

        try:
            # 1. Phase 1 — 사전 스크리닝 (13:00~)
            # self._wait_until(self.cfg.SCREENING_START)
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
            # self._wait_until(self.cfg.SUPPLY_CHECK_START)
            candidates = self._phase2_supply_analysis(candidates)
            logger.info(f"Phase 2 완료: {len(candidates)}개 후보")

            return  # Phase 3 매수 실행은 테스트를 위해 일단 보류

            # # 3. Phase 3 — 매수 실행 (15:00~15:20)
            # self._wait_until(self.cfg.BUY_WINDOW_START)
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
                for item in items[:self.cfg.TOP_N_BY_VALUE]:
                    code = item.get("stk_cd", "").split("_")[0]
                    name = item.get("stk_nm", "")
                    tv = abs(self.engine.parse_price(item.get("trde_prica", "0"))) * 1_000_000
                    cp = abs(self.engine.parse_price(item.get("cur_prc", "0")))
                    chg = self.engine.parse_float(item.get("flu_rt", "0"))
                    mc = 0  # ka10032에는 시총 없음, 이후 ka10001에서 보강

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

        # (b) 관심섹터 종목 보강 (ka10001로 개별 조회)
        for sector, codes in self.cfg.WATCHLIST_SECTORS.items():
            for code in codes:
                if code in seen_codes:
                    continue
                try:
                    info = self.api.get_stock_basic_info(code)
                    name = info.get("stk_nm", code)
                    cp = self.engine.parse_price(info.get("cur_prc", "0"))
                    # 시가총액: mac 필드 (억 단위) → 원 단위 변환
                    mc_raw = self.engine.parse_price(info.get("mac", "0"))
                    mc = mc_raw * 100_000_000  # 억 → 원
                    # 거래대금은 기본정보에 없으므로 별도 체크 필요
                    # 관심종목은 시총 기준만 우선 적용
                    if mc >= self.cfg.MIN_MARKET_CAP:
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
            # (a) 정배열 체크 (ka10081)
            is_aligned, near_high = self.engine.check_ma_alignment(c.code)
            if not is_aligned and not near_high:
                logger.debug(f"정배열 아님 → 제외: {c.name}")
                continue
            c.ma_aligned = is_aligned
            c.near_high = near_high

            # (b) 수급 분석 (ka10063 + ka90004 + ka10131 + ka10002)
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
            time.sleep(0.5)  # API 호출 제한 대응

        # 대장주 판별
        filtered = self.engine.identify_sector_leaders(filtered)

        # 스코어링
        for c in filtered:
            self.engine.score_candidate(c)

        filtered.sort(key=lambda x: x.score, reverse=True)

        # 결과 출력
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
            if len(buy_targets) >= self.cfg.MAX_POSITIONS:
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
        for sector, codes in self.cfg.WATCHLIST_SECTORS.items():
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


# ============================================================
# 6. 실행
# ============================================================

if __name__ == "__main__":
    strategy = ClosingBetStrategy()
    strategy.run()