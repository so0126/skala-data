"""
서울 날씨, 국가, 접속 위치 정보를 검증하는 Pydantic 모델 모듈

작성자: 박소영
변경 이력:
 - 2026-07-20: API 수집 데이터의 타입 및 범위 검증 모델 생성
"""

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    IPvAnyAddress,
    model_validator,
)


# 공통 타입 및 범위 검증
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]
Temperature = Annotated[float, Field(ge=-100, le=70)]
PrecipitationProbability = Annotated[int, Field(ge=0, le=100)]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# Open-Meteo 날씨 API 모델
class HourlyWeather(ApiModel):
    time: list[datetime] = Field(min_length=1)
    temperature_2m: list[Temperature] = Field(min_length=1)
    precipitation_probability: list[PrecipitationProbability] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_hourly_lengths(self) -> Self:
        lengths = {
            len(self.time),
            len(self.temperature_2m),
            len(self.precipitation_probability),
        }
        if len(lengths) != 1:
            raise ValueError("시간, 기온, 강수확률의 개수가 같아야 합니다")
        return self


class Weather(ApiModel):
    latitude: Latitude
    longitude: Longitude
    generationtime_ms: Annotated[float, Field(ge=0)]
    timezone: str = Field(min_length=1)
    hourly: HourlyWeather


# Countries.dev 국가 정보 API 모델
class Flags(ApiModel):
    png: HttpUrl


class Country(ApiModel):
    name: str = Field(min_length=1)
    native_name: str = Field(alias="nativeName", min_length=1)
    alpha2_code: str = Field(alias="alpha2Code", pattern=r"^[A-Z]{2}$")
    alpha3_code: str = Field(alias="alpha3Code", pattern=r"^[A-Z]{3}$")
    capital: str = Field(min_length=1)
    population: int = Field(ge=0)
    flags: Flags


# ip-api 위치 정보 API 모델
class Location(ApiModel):
    status: Literal["success"]
    country: str = Field(min_length=1)
    country_code: str = Field(
        alias="countryCode",
        pattern=r"^[A-Z]{2}$",
    )
    region_name: str = Field(alias="regionName", min_length=1)
    city: str = Field(min_length=1)
    latitude: Latitude = Field(alias="lat")
    longitude: Longitude = Field(alias="lon")
    timezone: str = Field(min_length=1)
    query: IPvAnyAddress


# 전체 API 수집 결과 모델
class CollectedData(ApiModel):
    weather: Weather
    country: Country
    location: Location
