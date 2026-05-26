from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
import os, logging
from dotenv import load_dotenv
load_dotenv()

import service

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s", force=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Flight Satisfaction Analyzer")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.get("/api/flights")
async def get_flights():
    try:
        return await run_in_threadpool(service.get_all_flights)
    except Exception as _:
        logger.exception("Error loading flights")
        return []


@app.get("/api/flight/{flight_id}")
async def get_flight_analysis(flight_id: str):
    try:
        result = await run_in_threadpool(service.get_flight_analysis, flight_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Flight not found")
        return result
    except HTTPException:
        raise
    except Exception as _:
        logger.exception(f"Error analyzing flight {flight_id}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/result", response_class=HTMLResponse)
async def result_page(request: Request, flight_id: str = Query(None)):
    return templates.TemplateResponse(request, "result.html", {
        "request": request,
        "flight_id": flight_id
    })