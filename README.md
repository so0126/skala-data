# skala-data

> SKALA 데이터 수집·검증·저장 실습
> 2026-07-20

## 프로젝트 소개

서울의 3일 시간대별 날씨, 대한민국 국가 정보, 접속 IP의 위치 정보를 외부 API에서 비동기로 수집하는 프로젝트입니다. 수집한 응답은 Pydantic v2 모델로 검증한 뒤 API별 DataFrame으로 변환하고, CSV와 Parquet 형식으로 저장해 읽기·쓰기 시간을 비교합니다.

## 사용 API

| API | 수집 데이터 |
| --- | --- |
| Open-Meteo | 서울의 3일 시간대별 기온과 강수확률 |
| Countries.dev | 대한민국의 국가명, 국가 코드, 수도, 인구, 국기 PNG URL |
| ip-api | 접속 IP의 국가, 지역, 도시, 위도·경도, 시간대 |

ip-api의 위치는 GPS가 아닌 공인 IP 등록 정보를 기반으로 하므로 실제 접속 위치와 다를 수 있습니다.

## 처리 과정

```text
외부 API 3개
    ↓ asyncio.gather() 동시 수집
Pydantic v2 응답 검증
    ↓
API별 Pandas DataFrame 변환
    ↓
CSV / Parquet 저장 및 읽기·쓰기 시간 측정
```

세 API 요청은 `httpx.AsyncClient`와 `asyncio.gather()`를 사용해 동시에 처리합니다. 요청 자체가 실패(HTTP 오류, 타임아웃)하면 `ApiRequestError`, 응답 검증에 실패하면 `ApiValidationError`가 발생하며, 두 예외 모두 공통 베이스 `ApiError`를 통해 실패한 API의 `ApiSource`를 함께 기록합니다.

## 데이터 검증

- 위도: `-90~90`
- 경도: `-180~180`
- 기온: `-100~70°C`
- 강수확률: `0~100%`
- 시간, 기온, 강수확률 배열 길이 일치
- 국가 코드: ISO 2자리·3자리 형식
- 국기 PNG: HTTP URL 형식
- IP 주소: IPv4 또는 IPv6 형식
- 위치 API 상태: `success`

사용하지 않는 API 응답 필드는 `extra="ignore"` 설정으로 제외합니다.

## 프로젝트 구조

```text
.
├── collector.py          # 외부 API 비동기 수집 및 응답 검증
├── models.py             # Pydantic v2 데이터 모델
├── storage.py            # DataFrame 변환, CSV/Parquet 저장 및 성능 측정
├── main.py               # 전체 파이프라인 실행
├── tests/
│   └── test_collector.py # API별 검증 실패 테스트
├── requirements.txt
└── .pre-commit-config.yaml
```

## 실행 방법

Python 3.11 가상환경을 사용합니다.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

실행하면 API별 DataFrame과 CSV·Parquet 읽기/쓰기 시간 합계가 터미널에 출력되며 다음 파일이 생성됩니다.

```text
output/
├── weather.csv
├── weather.parquet
├── country.csv
├── country.parquet
├── location.csv
└── location.parquet
```

## 테스트

```bash
PYTHONPATH=. pytest
```

가짜 API 응답을 사용해 다음 검증 실패를 테스트합니다.

- 강수확률 `101%`
- 잘못된 2자리 국가 코드 `KOR`
- 범위를 벗어난 위도 `91.0`

각 경우 `ApiValidationError`가 발생하고 실패한 API 출처가 정확히 표시되는지 확인합니다.
