"""
서울 날씨, 국가, 접속 위치 정보를 외부 API에서 비동기로 수집하는 모듈

작성자: 박소영
변경 이력:
 - 2026-07-20: 외부 API 비동기 데이터 수집 기능 생성
 - 2026-07-20: API 응답을 Pydantic 모델로 즉시 검증하도록 변경
 - 2026-07-20: 어느 API에서 검증이 실패했는지 태그(ApiSource)하는 전용 예외(ApiValidationError) 추가
"""

import asyncio
from enum import Enum
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from models import CollectedData, Country, Location, Weather

T = TypeVar("T", bound=BaseModel)


class ApiSource(Enum):
    WEATHER = "weather"
    COUNTRY = "country"
    LOCATION = "location"


class ApiValidationError(Exception):
    """어느 API 응답에서 검증이 실패했는지 태그(ApiSource)로 표시하는 예외"""

    def __init__(self, source: ApiSource, error: ValidationError) -> None:
        self.source = source
        self.error = error
        super().__init__(f"[{source.value}] 데이터 검증 실패:\n{error}")


# API URL
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
COUNTRIES_URL = "https://countries.dev/alpha/KOR"
IP_API_URL = "http://ip-api.com/json/"

# 서울 3일 시간대별 기온,강수확률 쿼리용 파라미터
WEATHER_PARAMS = httpx.QueryParams(
    {
        "latitude": 37.5665,
        "longitude": 126.9780,
        "hourly": "temperature_2m,precipitation_probability",
        "forecast_days": 3,
        "timezone": "Asia/Seoul",
    }
)


# 비동기 응답 받기
async def fetch_response(
    client: httpx.AsyncClient,
    url: str,
    params: httpx.QueryParams | None = None,
) -> httpx.Response:
    response = await client.get(url, params=params)
    response.raise_for_status()
    return response


# 어느 API(source) 응답인지 태그를 붙여 검증, 실패 시 ApiValidationError로 래핑
def validate_response(source: ApiSource, model: type[T], data: object) -> T:
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise ApiValidationError(source, e) from e


# api 3개의 데이터 gather로 모으기
async def collect_data() -> CollectedData:
    async with httpx.AsyncClient(timeout=10.0) as client:
        weather_response, country_response, location_response = await asyncio.gather(
            fetch_response(client, OPEN_METEO_URL, WEATHER_PARAMS),
            fetch_response(client, COUNTRIES_URL),
            fetch_response(client, IP_API_URL),
        )

    return CollectedData(
        weather=validate_response(ApiSource.WEATHER, Weather, weather_response.json()),
        country=validate_response(ApiSource.COUNTRY, Country, country_response.json()),
        location=validate_response(
            ApiSource.LOCATION, Location, location_response.json()
        ),
    )
