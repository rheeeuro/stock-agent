"""
Stock Agent API — FastAPI 진입점
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers.admin import router as admin_router
from routers.contents import router as contents_router
from routers.daily_summary import router as daily_summary_router
from routers.market import router as market_router
from routers.source import router as source_router
from routers.stock_report import router as stock_report_router
from routers.strategy_config import router as strategy_config_router
from routers.telegram_user import router as telegram_user_router
from routers.ticker import router as ticker_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(contents_router)
app.include_router(daily_summary_router)
app.include_router(market_router)
app.include_router(source_router)
app.include_router(stock_report_router)
app.include_router(strategy_config_router)
app.include_router(telegram_user_router)
app.include_router(ticker_router)


@app.get("/")
def read_root():
    return {"status": "ok", "service": "Stock Agent API"}
