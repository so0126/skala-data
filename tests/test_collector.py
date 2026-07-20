"""
API별 유효하지 않은 응답이 ApiValidationError를 발생시키고,
실패 출처가 정확한 ApiSource로 표시되는지 확인하는 테스트
작성자: 박소영
변경 이력:
  - 2026-07-20: API별 유효하지 않은 응답의 검증 실패 출처 테스트 생성

"""

import asyncio

import httpx
import pytest

from collector import (
    COUNTRIES_URL,
    IP_API_URL,
    OPEN_METEO_URL,
    ApiSource,
    ApiValidationError,
    collect_data,
)

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
