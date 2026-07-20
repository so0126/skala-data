"""
서울 날씨, 국가, 접속 위치 정보를 수집해 CSV/Parquet으로 저장하는 메인 모듈
파이프라인: collector(수집+검증) -> main(오케스트레이션) -> storage(DataFrame 변환/저장/시간측정)

작성자: 박소영
변경 이력:
 - 2026-07-20: 데이터 수집 후 JSON으로 출력하는 메인 함수 생성
 - 2026-07-20: API 검증 실패 시 로그 남기고 종료하도록 예외 처리 추가
 - 2026-07-20: 수집 결과를 API별 DataFrame으로 출력하도록 변경
 - 2026-07-20: CSV/Parquet 저장 및 API별 읽기/쓰기 시간 합계 측정 기능 추가

"""

import asyncio
import logging
import sys
from pathlib import Path

from collector import ApiValidationError, collect_data
from storage import (
    country_dataframe,
    location_dataframe,
    save_csv,
    save_parquet,
    weather_dataframe,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    # API 데이터가 모델과 맞지 않을 경우 종료
    try:
        collected = await collect_data()
    except ApiValidationError as e:
        logger.error("[%s] 데이터 검증 실패: %s", e.source.value, e.error)
        sys.exit(1)

    # 각 API 응답을 dataframe으로 출력
    dataframes = {
        "weather": weather_dataframe(collected),
        "country": country_dataframe(collected),
        "location": location_dataframe(collected),
    }

    for name, df in dataframes.items():
        print(df.to_string(index=False))
        print("==============================================================")

    # api별로 csv/parquet 저장하며 읽기/쓰기 시간 합계 누적
    csv_total = {"write": 0.0, "read": 0.0}
    parquet_total = {"write": 0.0, "read": 0.0}

    for name, df in dataframes.items():
        csv_times = save_csv(df, Path(f"output/{name}.csv"))
        parquet_times = save_parquet(df, Path(f"output/{name}.parquet"))
        for key in csv_total:
            csv_total[key] += csv_times[key]
            parquet_total[key] += parquet_times[key]

    print(f"csv 시간 측정 합계: {csv_total}")
    print(f"parquet 시간 측정 합계: {parquet_total}")


if __name__ == "__main__":
    asyncio.run(main())
