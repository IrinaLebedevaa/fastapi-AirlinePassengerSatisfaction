import os, logging, pandas as pd
from sqlalchemy import create_engine, text
from typing import Dict, List, Optional
from catboost import CatBoostClassifier
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s", force=True)
logger = logging.getLogger(__name__)

model = CatBoostClassifier()
model.load_model('catboost_model.cbm')

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

LOW_THRESHOLD = 3.0
RATED_FEATURES = [
    "Inflight wifi service", "Departure/Arrival time convenient",
    "Ease of Online booking", "Gate location", "Food and drink",
    "Online boarding", "Seat comfort", "Inflight entertainment",
    "On-board service", "Leg room service", "Baggage handling",
    "Checkin service", "Inflight service", "Cleanliness"
]

def _fetch_raw(route: str) -> pd.DataFrame:
    """Загружает сырые данные по маршруту"""
    query = text("SELECT * FROM passenger_feedback WHERE route = :route;")
    df = pd.read_sql(query, engine, params={"route": route})
    if df.empty:
        raise ValueError(f"There is no data for the route: {route}")
    return df


def _preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Приводит данные к формату модели"""
    df = df.copy()
    df.drop(columns=['id', 'Gender', 'route', 'routename', 'departuretime', 'arrivaltime'], errors="ignore", inplace=True)

    expected = getattr(model, "feature_names_in_", df.columns.tolist())
    return df[expected]


def _get_low_metrics(df: pd.DataFrame) -> Dict[str, float]:
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


def _analyze_flight_data(df_raw: pd.DataFrame) -> Dict:
    """Общая логика: предсказание + статистика"""
    df_clean = _preprocess(df_raw)
    preds = model.predict(df_clean)
    satisfied = int((preds == "satisfied").sum())
    return {
        "satisfied": satisfied,
        "dissatisfied": len(preds) - satisfied,
        "total": len(preds),
        "low_metrics": _get_low_metrics(df_raw)
    }


def _parse_route_name(route_name: str):
    if not route_name or pd.isna(route_name):
        return "Unknown", "Unknown"
    if '-' in str(route_name):
        parts = str(route_name).split('-')
        return parts[0].strip(), parts[1].strip()
    return str(route_name), "Unknown"


def _format_time(time_value):
    if time_value is None or pd.isna(time_value):
        return "Not specified"
    return str(time_value) if not isinstance(time_value, str) else time_value


def get_all_flights() -> List[Dict]:
    """Список рейсов для выпадающего списка"""
    try:
        query = text("""
            SELECT DISTINCT route as flight_id, routename
            FROM passenger_feedback
            WHERE route IS NOT NULL AND route != ''
            ORDER BY route
        """)
        df = pd.read_sql(query, engine)
        result = []
        for _, row in df.iterrows():
            origin, destination = _parse_route_name(row.get('routename', ''))
            result.append({
                "flight_id": row['flight_id'],
                "origin": origin,
                "destination": destination
            })
        return result
    except Exception as e:
        logger.exception("Error in get_all_flights")
        return []


def get_flight_analysis(flight_id: str) -> Optional[Dict]:
    """Полный анализ рейса: мета + статистика + низкие оценки"""
    try:
        df = pd.read_sql(
            text("SELECT * FROM passenger_feedback WHERE route = :id"),
            engine, params={"id": flight_id}
        )
        if df.empty:
            return None

        first = df.iloc[0]
        routename = first.get('routename', '')
        origin, destination = _parse_route_name(routename)

        analysis = _analyze_flight_data(df)

        return {
            "flight_number": flight_id,
            "origin": origin,
            "destination": destination,
            "departure_time": _format_time(first.get('departuretime')),
            "arrival_time": _format_time(first.get('arrivaltime')),
            "satisfaction_data": {
                "satisfied": analysis["satisfied"],
                "neutral": 0,
                "unsatisfied": analysis["dissatisfied"]
            },
            "critical_marks": {
                "minimum": [{"name": k, "value": v} for k, v in analysis["low_metrics"].items()]
            }
        }
    except Exception as e:
        logger.exception(f"Error in get_flight_analysis for {flight_id}")
        return None