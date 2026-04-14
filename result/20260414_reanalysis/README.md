# 20260414 재분석 결과

## 개요
- 동일 스크립트로 20260407과 20260414 road 입력을 각각 실행해 비교했습니다.
- 스코어 산정 로직(요소/가중치)은 변경하지 않았고 road 입력만 변경했습니다.

## QGIS 최종 사용 파일
- qgis_final/uiwang_cctv_priority_weighted_30m_20260414.gpkg
- qgis_final/uiwang_roads_traffic_20260414_source.geojson
- qgis_final/uiwang_boundary.geojson

## 비교/검증 파일
- reports/run_summary_20260414_reanalysis.json
- reports/comparison_20260407_vs_20260414.json
- intermediate/top200_grid_score_shift_weighted_20260407_vs_20260414.csv

## 참고
- 20260414 입력 파일은 Point(18806행), 20260407은 MultiLineString(2642행)으로 구조가 크게 다릅니다.