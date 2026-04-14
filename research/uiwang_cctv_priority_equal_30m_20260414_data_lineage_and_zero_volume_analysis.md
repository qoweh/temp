# 의왕 CCTV 우선순위(equal 30m, 2026-04-14) 데이터 계보 및 교통량 0 분석

## 1) 문서 목적
이 문서는 다음을 한 번에 설명하기 위한 정리본이다.

1. 결과 파일 uiwang_cctv_priority_equal_30m_20260414.gpkg가 어떤 입력 데이터로 생성되었는지
2. 단계별(원천 -> 가공 -> 최종) 데이터 경로가 무엇인지
3. 교통량(vol_mean)=0 값이 왜 많이 나타나는지, 분석에 어떤 영향을 주는지
4. 도로/교통량 데이터를 별첨할 때 "교통량은 0인데 속도/혼잡도는 0이 아님"을 어떻게 설명할지


## 2) 최종 결과 파일 구조

- 대상 파일: result/20260414_reanalysis/qgis_final/uiwang_cctv_priority_equal_30m_20260414.gpkg
- 생성 스크립트: qgis-second-report/second report/gpt/build_uiwang_grid_candidates_with_roads.py
- 중간 산출물 동일성: 아래 파일과 SHA256 완전 동일
  - qgis-second-report/second report/gpt/this_uiwang_grid_score_30m_equal_20260414.gpkg

### 레이어/건수

| 레이어 | Geometry | 행 수 | 설명 |
|---|---|---:|---|
| grid_score | MULTIPOLYGON | 60,417 | 30m 격자 점수 본체 |
| score_points | POINT | 60,417 | IDW 등 보간용 포인트 |


## 3) 단계별 데이터 계보 (Pipeline)

### Stage A. 비도로 원천 입력(요소 데이터)

| 요소 | 파일 | 레이어 | 건수 |
|---|---|---|---:|
| CCTV | qgis-second-report/this/무인교통단속카메라.gpkg | 무인교통단속카메라 | 79 |
| 버스정류장 | qgis-second-report/this/버스정류소.gpkg | 버스정류소 | 388 |
| 사고다발 | qgis-second-report/this/사고다발지.gpkg | 사고다발지_내보내기 | 7 |
| 사망사고 | qgis-second-report/this/사망교통사고.gpkg | 사망교통사고_내보내기 | 62 |
| 학교 | qgis-second-report/this/초중고등학교.gpkg | 초중고등학교_내보내기 | 28 |
| 경계 | qgis-second-report/second report/gpt/this_uiwang_boundary.geojson | Polygon | 1 |

### Stage B. 도로/교통 입력(비교 2종)

| 구분 | 파일 | Geometry | 건수 |
|---|---|---|---:|
| baseline(20260407) | uiwang_all_roads_with_traffic_lines_in_boundary.geojson | MultiLineString | 2,642 |
| target(20260414) | uiwang_all_roads_with_traffic_lines_in_boundary2.geojson | Point | 18,806 |

### Stage C. 점수 산정 및 GPKG 생성

- 실행 스크립트: qgis-second-report/second report/gpt/build_uiwang_grid_candidates_with_roads.py
- 로직 요약:
  1. 경계 내 30m 격자 생성
  2. 각 격자 중심점에서 5개 비도로 요소 + 도로 최근접 거리 계산
  3. 최근접 도로의 vol_mean 기반 traffic score 계산
  4. equal / weighted 점수 파일 생성

### Stage D. 중간 산출물

- qgis-second-report/second report/gpt/this_uiwang_grid_score_30m_equal_20260414.gpkg
- qgis-second-report/second report/gpt/this_uiwang_grid_score_30m_weighted_20260414.gpkg

### Stage E. 최종 배포 산출물

- result/20260414_reanalysis/qgis_final/uiwang_cctv_priority_equal_30m_20260414.gpkg
- result/20260414_reanalysis/qgis_final/uiwang_cctv_priority_weighted_30m_20260414.gpkg
- result/20260414_reanalysis/qgis_final/uiwang_roads_traffic_20260414_source.geojson
- result/20260414_reanalysis/qgis_final/uiwang_roads_traffic_20260407_source.geojson
- result/20260414_reanalysis/qgis_final/uiwang_boundary.geojson

### Stage F. 보고/검증 산출물

- result/20260414_reanalysis/reports/run_summary_20260414_reanalysis.json
- result/20260414_reanalysis/reports/comparison_20260407_vs_20260414.json
- result/20260414_reanalysis/intermediate/top200_grid_score_shift_weighted_20260407_vs_20260414.csv


## 4) 상위(업스트림) 도로/교통 데이터 생성 체인

아래는 최종 점수 입력 도로 데이터까지의 대표 생성 체인이다.

1. OSM 도로 필터링
   - 스크립트: qgis-second-report/plus/build_uiwang_osm_road_inventory.py
   - 출력: qgis-second-report/plus/uiwang_osm_roads_filtered.geojson, uiwang_osm_roads_segments.csv

2. 경기도 API 수집
   - 스크립트: qgis-second-report/plus/build_gg_road_inventory.py, build_gg_road_traffic_recollect.py
   - 출력: qgis-second-report/plus/gg_road_info_list.csv, gg_road_traffic_info_list.csv

3. 도로-교통 매칭 통합
   - 스크립트: qgis-second-report/plus/build_uiwang_road_traffic_merge.py
   - 출력: qgis-second-report/plus/uiwang_all_roads_with_traffic.csv

4. 라인 레이어 결합
   - 스크립트: qgis-second-report/plus/build_uiwang_qgis_line_layer.py
   - 출력: qgis-second-report/plus/uiwang_all_roads_with_traffic_lines.geojson

5. 추론 보강
   - 스크립트: qgis-second-report/plus/build_uiwang_road_traffic_infer.py
   - 출력: qgis-second-report/plus/uiwang_all_roads_with_traffic_inferred.csv, uiwang_all_roads_with_traffic_lines_in_boundary_inferred.geojson

6. 포인트화(결빙/교통 heatmap용)
   - 스크립트: qgis-second-report/plus/build_uiwang_icing_heatmap_points.py
   - 출력: qgis-second-report/plus/uiwang_road_icing_heatmap_points.geojson


## 5) 교통량 0 현황 (실측)

### A. baseline 도로 라인(20260407 입력)

- 파일: uiwang_all_roads_with_traffic_lines_in_boundary.geojson
- 총 2,642개 중
  - vol_mean = 0: 153개 (5.79%)
  - vol_mean > 0: 114개 (4.31%)
  - vol_mean 결측/빈값: 2,375개 (89.90%)
  - vol=0 이면서 spd_mean>0: 153개
  - vol=0 이면서 trvlTime_mean>0: 153개

### B. 추론 통합 CSV(도로 단위)

- 파일: qgis-second-report/plus/uiwang_all_roads_with_traffic_inferred.csv
- 총 2,665개 중
  - vol_mean = 0: 1,722개 (64.62%)
  - vol_mean > 0: 197개 (7.39%)
  - vol_mean 결측: 746개 (27.99%)
  - vol=0 이면서 spd_mean>0: 1,722개
  - vol=0 이면서 trvlTime_mean>0: 1,722개

### C. 20260414 타깃 입력 포인트

- 파일: uiwang_all_roads_with_traffic_lines_in_boundary2.geojson
- 총 18,806개 중
  - vol_mean = 0: 17,788개 (94.59%)
  - vol_mean > 0: 1,018개 (5.41%)
  - 결측: 0


## 6) "vol=0인데 speed/혼잡도는 0이 아님"의 원인 분석

### 원인 1. 원천 관측 자체에서 vol 중앙값이 0

- 관측(match original=matched) 305개 기준 중앙값
  - median(vol_mean) = 0.0
  - median(spd_mean) = 57.511
  - median(trvlTime_mean) = 25.275
- 관측 집단에서 vol=0 비율: 61.97% (189/305)

즉, 원천 관측 데이터 자체가 "교통량 0이 자주 나오지만 속도/통행시간 값은 존재"하는 특성을 가진다.

### 원인 2. 추론 스크립트가 vol/spd/trvl을 독립 통계로 보간

- 스크립트: previous_data/build_uiwang_road_traffic_infer.py
- 보강 방식: name median -> nearest family -> highway median -> family median -> global median
- method_breakdown:
  - inferred_global_median: 1,146
  - inferred_nearest_family: 195
  - inferred_highway_median: 226
  - inferred_family_median: 43
  - inferred_name_median: 4

global median 단계에서 vol 중앙값이 0인 상태로 spd/trvl 중앙값은 양수이면, 결과적으로 vol=0 & spd>0 조합이 대량으로 생긴다.

### 원인 3. 혼잡도(congGrade_proxy)는 vol에서 직접 계산한 값이 아님

- 파일: analyse/20260414/build_uiwang_prediction_datasets_20260414.py
- congGrade_proxy는 raw API의 congGrade 평균(raw_obs_mean_congGrade)에서 가져온 프록시다.
- 따라서 vol=0이어도 congGrade_proxy>0 가능.

실측(예측 피처 CSV 기준):

- 파일: analyse/20260414/uiwang_all_roads_prediction_features_20260414.csv
- vol=0 & spd>0: 1,722건
- vol=0 & congGrade_proxy>0: 318건


## 7) 교통량 0이 결과 점수에 미치는 영향

### 점수식에서 traffic 요소 비중

- equal: 7개 요소 평균 -> traffic 최대 영향폭은 셀당 14.29점(0~1 전체 변화 가정)
- weighted: (2,3,3,5,5,5)/23 구조 -> traffic 최대 영향폭은 셀당 21.74점

### 실제 산출물 기반 민감도 점검 (20260414)

- 분석 파일:
  - result/20260414_reanalysis/qgis_final/uiwang_grid_score_30m_20260414_equal.csv
  - result/20260414_reanalysis/qgis_final/uiwang_grid_score_30m_20260414_weighted.csv

- 결과:
  - 최근접 도로 vol=0 셀: 56,958 / 60,417 (94.27%)
  - score_traffic 평균: 0.2824
  - score_traffic = 0 비율: 49.21%

- 가정 실험(민감도): "vol=0 케이스 traffic score를 중립 0.5로 일괄 치환"
  - equal 평균 점수 이동: +3.52점
  - weighted 평균 점수 이동: +5.35점
  - 셀당 최대 절대 이동폭:
    - equal: 7.14점
    - weighted: 10.87점

해석:

- 교통량 0은 분명 영향이 크다(특히 weighted에서 더 큼).
- 다만 현재 로직은 no_match 도로에 대해 traffic score를 중립(0.5) 처리하므로, 모든 vol=0이 동일하게 패널티를 받는 구조는 아니다.


## 8) 별첨(도로/교통 데이터) 설명 문구 제안

아래 문구를 보고서/부록에 그대로 써도 된다.

### A안(짧은 버전)

"본 데이터의 교통량(vol_mean)은 구간별 관측값 평균이며, 원천 데이터 특성상 vol=0이 다수 존재합니다. 반면 속도(spd_mean)와 통행시간(trvlTime_mean), 혼잡도 프록시(congGrade_proxy)는 별도 관측/집계 항목으로 계산되어 vol=0과 동시에 양수로 나타날 수 있습니다. 따라서 vol=0은 반드시 '교통 없음'을 의미하지 않으며, 관측 범위/집계 기준 차이에 따른 값으로 해석해야 합니다."

### B안(기술 부록 버전)

"교통량 보강 단계는 vol_mean, spd_mean, trvlTime_mean을 독립적으로 보간(도로명/근접/도로등급/전역 중앙값)합니다. 이때 관측 집단의 vol 중앙값이 0인 반면 spd/trvl 중앙값은 양수이므로, 보강 결과에서 vol=0 & spd>0 조합이 자연스럽게 발생합니다. 또한 congGrade_proxy는 raw API의 congGrade 평균값을 연결한 프록시로, vol_mean에서 직접 유도한 값이 아닙니다."


## 9) 별첨 권장 파일 세트

### 필수(재현용)

1. result/20260414_reanalysis/qgis_final/uiwang_cctv_priority_equal_30m_20260414.gpkg
2. result/20260414_reanalysis/qgis_final/uiwang_cctv_priority_weighted_30m_20260414.gpkg
3. result/20260414_reanalysis/qgis_final/uiwang_roads_traffic_20260414_source.geojson
4. result/20260414_reanalysis/qgis_final/uiwang_boundary.geojson
5. result/20260414_reanalysis/reports/run_summary_20260414_reanalysis.json

### 교통량 0 설명 보강용

1. qgis-second-report/plus/uiwang_all_roads_with_traffic_inferred.csv
2. qgis-second-report/plus/uiwang_traffic_data_coverage_inferred.json
3. analyse/20260414/uiwang_all_roads_prediction_features_20260414.csv
4. analyse/20260414/build_uiwang_prediction_datasets_20260414.py
5. previous_data/build_uiwang_road_traffic_infer.py


## 10) 주의사항

- uiwang_all_roads_with_traffic_lines_in_boundary2.geojson 자체 생성 스크립트(정확한 실행 로그)는 워크스페이스에서 직접 확인되지 않았다.
- 다만 run_summary_20260414_reanalysis.json에 본 파일이 20260414 road 입력으로 명시되어 있고, 최종 산출물과의 연결은 해시/스키마/건수로 검증되었다.
