"""
collector 모듈의 정상 API 수집과 응답 검증 실패 처리를 확인하는 테스트
작성자: 박소영
변경 이력:
  - 2026-07-20: API별 유효하지 않은 응답의 검증 실패 출처 테스트 생성
  - 2026-07-20: 정상 응답 및 시간대별 배열 길이 검증 테스트 추가
  - 2026-07-20: API 타임아웃, HTTP 500 응답의 ApiRequestError 래핑 테스트 추가

"""

import asyncio

import httpx
import pytest

from collector import (
    COUNTRIES_URL,
    IP_API_URL,
    OPEN_METEO_URL,
    ApiRequestError,
    ApiSource,
    ApiValidationError,
    collect_data,
    fetch_response,
    validate_response,
)
from models import Weather

# 유효한 샘플 응답
VALID_RESPONSES: dict[str, dict[str, object]] = {
    OPEN_METEO_URL: {
        "latitude": 37.55,
        "longitude": 127.0,
        "generationtime_ms": 0.04,
        "timezone": "Asia/Seoul",
        "hourly": {
            "time": ["2026-07-20T00:00"],
            "temperature_2m": [25.0],
            "precipitation_probability": [30],
        },
    },
    COUNTRIES_URL: {
        "name": "Korea (Republic of)",
        "nativeName": "대한민국",
        "alpha2Code": "KR",
        "alpha3Code": "KOR",
        "capital": "Seoul",
        "population": 51_780_579,
        "flags": {"png": "https://flagcdn.com/w320/kr.png"},
    },
    IP_API_URL: {
        "status": "success",
        "country": "South Korea",
        "countryCode": "KR",
        "regionName": "Seoul",
        "city": "Gangnam-gu",
        "lat": 37.4909,
        "lon": 127.0452,
        "timezone": "Asia/Seoul",
        "query": "180.66.108.50",
    },
}
# 유효하지 않은 샘플 응답
INVALID_RESPONSES: dict[ApiSource, tuple[str, dict[str, object]]] = {
    ApiSource.WEATHER: (
        OPEN_METEO_URL,
        {
            **VALID_RESPONSES[OPEN_METEO_URL],
            "hourly": {
                "time": ["2026-07-20T00:00"],
                "temperature_2m": [25.0],
                "precipitation_probability": [101],
            },
        },
    ),
    ApiSource.COUNTRY: (
        COUNTRIES_URL,
        {
            **VALID_RESPONSES[COUNTRIES_URL],
            "alpha2Code": "KOR",
        },
    ),
    ApiSource.LOCATION: (
        IP_API_URL,
        {
            **VALID_RESPONSES[IP_API_URL],
            "lat": 91.0,
        },
    ),
}


@pytest.mark.parametrize("expected_source", list(ApiSource))
def test_collect_data_rejects_invalid_api_response(
    monkeypatch: pytest.MonkeyPatch,
    expected_source: ApiSource,
) -> None:
    invalid_url, invalid_data = INVALID_RESPONSES[expected_source]

    # 대상 API에는 유효하지 않은 응답을, 나머지 API에는 유효한 응답을 반환
    async def fake_fetch_response(
        client: httpx.AsyncClient,
        source: ApiSource,
        url: str,
        params: httpx.QueryParams | None = None,
    ) -> httpx.Response:
        del client, source, params
        data = invalid_data if url == invalid_url else VALID_RESPONSES[url]
        request = httpx.Request("GET", url)
        return httpx.Response(200, json=data, request=request)

    monkeypatch.setattr("collector.fetch_response", fake_fetch_response)

    with pytest.raises(ApiValidationError) as error_info:
        asyncio.run(collect_data())

    assert error_info.value.source is expected_source


# 정상 API 응답시 CollectedData 생성 확인 및 날씨 위도, 국가 코드, 위치 국가 코드 확인
def test_collect_data_accepts_valid_api_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_response(
        client: httpx.AsyncClient,
        source: ApiSource,
        url: str,
        params: httpx.QueryParams | None = None,
    ) -> httpx.Response:
        del client, source, params
        request = httpx.Request("GET", url)
        return httpx.Response(200, json=VALID_RESPONSES[url], request=request)

    monkeypatch.setattr("collector.fetch_response", fake_fetch_response)

    collected = asyncio.run(collect_data())

    assert collected.weather.latitude == 37.55
    assert collected.country.alpha2_code == "KR"
    assert collected.location.country_code == "KR"


# API 타임아웃 발생 시 ApiRequestError로 래핑되는지 확인
def test_fetch_response_wraps_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("요청 시간 초과", request=request)

    transport = httpx.MockTransport(handler)

    async def run() -> httpx.Response:
        async with httpx.AsyncClient(transport=transport) as client:
            return await fetch_response(client, ApiSource.WEATHER, OPEN_METEO_URL)

    with pytest.raises(ApiRequestError) as error_info:
        asyncio.run(run())

    assert error_info.value.source is ApiSource.WEATHER
    assert isinstance(error_info.value.error, httpx.TimeoutException)


# HTTP 500 응답 시 ApiRequestError로 래핑되는지 확인
def test_fetch_response_wraps_http_500() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request)

    transport = httpx.MockTransport(handler)

    async def run() -> httpx.Response:
        async with httpx.AsyncClient(transport=transport) as client:
            return await fetch_response(client, ApiSource.COUNTRY, COUNTRIES_URL)

    with pytest.raises(ApiRequestError) as error_info:
        asyncio.run(run())

    assert error_info.value.source is ApiSource.COUNTRY
    assert isinstance(error_info.value.error, httpx.HTTPStatusError)


# 시간대별 배열 길이 검증 테스트
def test_weather_rejects_different_hourly_lengths() -> None:
    invalid_weather = {
        **VALID_RESPONSES[OPEN_METEO_URL],
        "hourly": {
            "time": ["2026-07-20T00:00", "2026-07-20T01:00"],
            "temperature_2m": [25.0],
            "precipitation_probability": [30],
        },
    }

    with pytest.raises(ApiValidationError) as error_info:
        validate_response(ApiSource.WEATHER, Weather, invalid_weather)

    assert error_info.value.source is ApiSource.WEATHER
    assert "시간, 기온, 강수확률의 개수가 같아야 합니다" in str(error_info.value)
