# 의왕 Stage E 산출물 재검토 가이드

## 1) 목적
아래 Stage E 최종 배포 산출물이 나오기 전까지의 데이터를, 요청하신 두 관점으로 분리해 다시 볼 수 있게 정리했다.

- result/20260414_reanalysis/qgis_final/uiwang_cctv_priority_equal_30m_20260414.gpkg
- result/20260414_reanalysis/qgis_final/uiwang_cctv_priority_weighted_30m_20260414.gpkg
- result/20260414_reanalysis/qgis_final/uiwang_roads_traffic_20260414_source.geojson
- result/20260414_reanalysis/qgis_final/uiwang_roads_traffic_20260407_source.geojson
- result/20260414_reanalysis/qgis_final/uiwang_boundary.geojson

분리 기준:

1. API 응답을 합치기 전, 엔드포인트별 원본 파싱 CSV
2. API 파싱만으로 교통량 커버리지가 부족해 추가 조사/보강한 데이터


## 2) 연구 폴더 구조 (이번 정리 결과)

- research/01_api_raw_parsed
  - 01_getRoadInfoList_parsed.csv
  - 02_getRoadTrafficInfoList_parsed.csv
  - api_raw_parsed_index.csv

- research/02_supplementary_research_for_missing_traffic
  - 01_investigation_sources.csv
  - 02_roadre_uiwang_route_stats.csv
  - 03_roadre_uiwang_spots_selected.csv
  - 04_uiwang_all_roads_with_traffic_roadre_retry.csv
  - 05_uiwang_all_roads_with_traffic_inferred.csv
  - 06_uiwang_gg_route_traffic_stats.csv
  - 07_uiwang_gg_routeno_traffic_stats.csv
  - supplementary_research_index.csv


## 3) 관점 1: API별(비통합) 원본 파싱 데이터

위치: research/01_api_raw_parsed

### A. getRoadInfoList 원본 파싱

- 파일: research/01_api_raw_parsed/01_getRoadInfoList_parsed.csv
- 성격: 경기도 OpenAPI 노선 마스터(노선 메타)
- 행 수: 152 (헤더 제외)
- 핵심 컬럼: roadRank, routeId, routeNm, routeNo, routeTp

### B. getRoadTrafficInfoList 원본 파싱

- 파일: research/01_api_raw_parsed/02_getRoadTrafficInfoList_parsed.csv
- 성격: 노선별 교통 관측 원본(시각별/구간별)
- 행 수: 24,413 (헤더 제외)
- 핵심 컬럼: collDate, vol, spd, trvlTime, congGrade, routeId, routeId_query, linkId

### C. 보완 메모

- getRoadLinkInfoList는 수집 스크립트에 구현되어 있으나, 현재 워크스페이스에는 결과 CSV가 보관되어 있지 않다.
- 해당 정보는 인덱스 파일에 결측 상태로 명시했다.
  - research/01_api_raw_parsed/api_raw_parsed_index.csv


## 4) 관점 2: 교통량 공백으로 인한 추가 조사/보강 데이터

위치: research/02_supplementary_research_for_missing_traffic

### A. 조사 이력/소스 총괄

- 파일: research/02_supplementary_research_for_missing_traffic/01_investigation_sources.csv
- 용도: 어떤 대체 소스/재시도를 했는지, 성공/실패와 결과 수치 기록

### B. 대체 소스 road.re 재시도 계열

- 파일: research/02_supplementary_research_for_missing_traffic/02_roadre_uiwang_route_stats.csv
- 파일: research/02_supplementary_research_for_missing_traffic/03_roadre_uiwang_spots_selected.csv
- 파일: research/02_supplementary_research_for_missing_traffic/04_uiwang_all_roads_with_traffic_roadre_retry.csv
- 용도: 경기도 API 공백을 대체 소스로 보강 가능한지 검증

### C. 통계/추론 보강 계열

- 파일: research/02_supplementary_research_for_missing_traffic/05_uiwang_all_roads_with_traffic_inferred.csv
- 파일: research/02_supplementary_research_for_missing_traffic/06_uiwang_gg_route_traffic_stats.csv
- 파일: research/02_supplementary_research_for_missing_traffic/07_uiwang_gg_routeno_traffic_stats.csv
- 용도: 관측 공백(no_match/vol 결측) 구간을 통계/근접 기반으로 보강하고 근거 통계 제공


## 5) Stage E 산출물과의 연결 방식

요약 흐름:

1. API별 원본 파싱
   - getRoadInfoList / getRoadTrafficInfoList
2. 도로-교통 매칭/집계
   - route명/routeNo 기반 통계 활용
3. 공백 구간에 대한 추가 조사 및 보강
   - road.re 재시도 검증
   - inferred 보강 적용
4. 최종 도로 소스(20260407/20260414 계열) 입력으로 30m 격자 점수 산출
   - equal/weighted GPKG 생성


## 6) 빠른 재검토 순서 (권장)

1. API 원본 품질 확인
   - research/01_api_raw_parsed/api_raw_parsed_index.csv
   - research/01_api_raw_parsed/02_getRoadTrafficInfoList_parsed.csv

2. 교통량 공백 대응 확인
   - research/02_supplementary_research_for_missing_traffic/supplementary_research_index.csv
   - research/02_supplementary_research_for_missing_traffic/01_investigation_sources.csv
   - research/02_supplementary_research_for_missing_traffic/05_uiwang_all_roads_with_traffic_inferred.csv

3. 최종 산출물 대조
   - result/20260414_reanalysis/qgis_final/uiwang_cctv_priority_equal_30m_20260414.gpkg
   - result/20260414_reanalysis/qgis_final/uiwang_cctv_priority_weighted_30m_20260414.gpkg


## 7) 참고

- 기존 상세 계보/교통량 0 영향 분석 문서:
  - research/uiwang_cctv_priority_equal_30m_20260414_data_lineage_and_zero_volume_analysis.md
