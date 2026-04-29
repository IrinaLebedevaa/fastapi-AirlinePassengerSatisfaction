from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
from sqlalchemy import create_engine
from fastapi.staticfiles import StaticFiles
import os

import service


app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1111@localhost:5432/airlinepassenger")
engine = create_engine(DATABASE_URL)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})

@app.get("/api/routes")
async def get_routes():
    return {"routes": service.get_routes()}

@app.get("/api/chart-data")
async def get_chart_data(route: str = Query(...)):
    return service.predict(route)



