import os
import joblib
import pandas as pd
from sqlalchemy import create_engine
from typing import Dict, List
from catboost import CatBoostClassifier
from sqlalchemy import text

model = CatBoostClassifier()
model.load_model('catboost_model.cbm')

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1111@localhost:5432/airlinepassenger")
engine = create_engine(DATABASE_URL)


LOW_THRESHOLD = 3.0
RATED_FEATURES = [
    "Inflight wifi service", "Departure/Arrival time convenient",
    "Ease of Online booking", "Gate location", "Food and drink",
    "Online boarding", "Seat comfort", "Inflight entertainment",
    "On-board service", "Leg room service", "Baggage handling",
    "Checkin service", "Inflight service", "Cleanliness"
]

def get_routes() -> List[str]:
    """Возвращает список уникальных маршрутов"""
    df = pd.read_sql("SELECT DISTINCT route FROM passenger_feedback ORDER BY route;", engine)
    return df["route"].dropna().tolist()

def _fetch_raw(route: str) -> pd.DataFrame:
    """Загружает сырые данные по маршруту"""
    query = text("SELECT * FROM passenger_feedback WHERE route = :route;")
    df = pd.read_sql(query, engine, params={"route": route})
    if df.empty:
        raise ValueError(f"Нет данных для маршрута: {route}")
    return df

def _preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Приводит данные к формату модели"""
    df = df.copy()
    df.drop(columns=['id', 'Gender', 'route'], errors="ignore", inplace=True)

    expected = getattr(model, "feature_names_in_", df.columns.tolist())
    return df[expected]


def _get_low_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """
    Находит показатели со средним баллом ниже порога.
    Исключает 0 из расчёта, так как 0 = "услуга не предоставлялась".
    """
    low = {}
    for col in RATED_FEATURES:
        if col not in df.columns:
            continue
        valid = df[col][(df[col] >= 1) & (df[col] <= 5)]
        if len(valid) == 0:
            continue
        avg = valid.mean()
        if avg < LOW_THRESHOLD:
            low[col] = round(float(avg), 2)
    return low

def predict(route: str):
    df_raw = _fetch_raw(route)
    df_clean = _preprocess(df_raw)
    preds = model.predict(df_clean)

    satisfied = int((preds == "satisfied").sum())
    dissatisfied = len(preds) - satisfied
    return {
        "satisfied": satisfied,
        "dissatisfied": dissatisfied,
        "total": len(preds),
        "low_metrics": _get_low_metrics(df_raw)
    }