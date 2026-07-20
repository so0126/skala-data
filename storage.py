"""
CollectedData를 API별 DataFrame으로 변환해 CSV/Parquet으로 저장하고 읽기/쓰기 시간을 재는 모듈

작성자: 박소영
변경 이력:
 - 2026-07-20: CSV/Parquet 저장 및 읽기/쓰기 성능 비교 기능 생성
 - 2026-07-20: 저장 직전 상위 폴더가 없으면 생성하도록 변경
 - 2026-07-20: weather/country/location DataFrame을 분리하고 save_csv/save_parquet가 DataFrame을 직접 받도록 변경
"""

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pandas as pd

from models import CollectedData


# 시간대별 날씨만 담은 DataFrame (한 시간=한 행)
def weather_dataframe(data: CollectedData) -> pd.DataFrame:
    hourly = data.weather.hourly
    return pd.DataFrame(
        {
            "time": hourly.time,
            "temperature_2m": hourly.temperature_2m,
            "precipitation_probability": hourly.precipitation_probability,
        }
    )


# 국가 정보(국기 포함)만 담은 1행짜리 DataFrame
def country_dataframe(data: CollectedData) -> pd.DataFrame:
    country = data.country
    return pd.DataFrame(
        [
            {
                "name": country.name,
                "native_name": country.native_name,
                "alpha2_code": country.alpha2_code,
                "alpha3_code": country.alpha3_code,
                "capital": country.capital,
                "population": country.population,
                "flag_png": str(country.flags.png),
            }
        ]
    )


# 접속 위치 정보만 담은 1행짜리 DataFrame
def location_dataframe(data: CollectedData) -> pd.DataFrame:
    location = data.location
    return pd.DataFrame(
        [
            {
                "country": location.country,
                "country_code": location.country_code,
                "region_name": location.region_name,
                "city": location.city,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "timezone": location.timezone,
                "query": str(location.query),
            }
        ]
    )


# with 블록 안 코드의 소요 시간(초)을 재서 times[key]에 기록
@contextmanager
def measure_time(times: dict[str, float], key: str) -> Iterator[None]:
    start = time.perf_counter()
    yield
    times[key] = time.perf_counter() - start


def save_csv(df: pd.DataFrame, path: Path) -> dict[str, float]:
    times: dict[str, float] = {}
    path.parent.mkdir(parents=True, exist_ok=True)

    with measure_time(times, "write"):
        df.to_csv(path, index=False)
    with measure_time(times, "read"):
        pd.read_csv(path)

    return times


def save_parquet(df: pd.DataFrame, path: Path) -> dict[str, float]:
    times: dict[str, float] = {}
    path.parent.mkdir(parents=True, exist_ok=True)

    with measure_time(times, "write"):
        df.to_parquet(path, index=False)
    with measure_time(times, "read"):
        pd.read_parquet(path)

    return times
