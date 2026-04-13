# API 주소 -> 생성 파일 정리 (2026-04-07 기준)

## 1) 경기도교통정보센터 OpenAPI
- URL: `https://openapigits.gg.go.kr/api/rest/getRoadInfoList`
- 생성 파일: `gg_road_info_list.csv`
- 코드 근거: `build_gg_road_inventory.py` 호출(143), 저장(160)

- URL: `https://openapigits.gg.go.kr/api/rest/getRoadTrafficInfoList`
- 생성 파일: `gg_road_traffic_info_list.csv`
- 코드 근거: `build_gg_road_inventory.py` 호출(214), 저장(244)

## 2) OpenStreetMap Overpass
- URL: `https://overpass-api.de/api/interpreter`
- 원시 파일: `osm_uiwang_bbox_highways.json`
- 후처리 산출물:
  - `uiwang_osm_roads_filtered.geojson`
  - `uiwang_osm_roads_segments.csv`
  - `uiwang_osm_road_type_summary.csv`
  - `uiwang_osm_named_roads_summary.csv`
  - `uiwang_osm_stats.json`
- 코드 근거: `build_uiwang_osm_road_inventory.py` 입출력 정의(12 부근), 저장(252 이후)

## 3) OSM + 경기교통 결합 파생 파일
- 산출물:
  - `uiwang_gg_route_traffic_stats.csv`
  - `uiwang_gg_routeno_traffic_stats.csv`
  - `uiwang_named_roads_with_traffic_summary.csv`
  - `uiwang_all_roads_with_traffic.csv`
  - `uiwang_traffic_data_coverage.json`
- 코드 근거: `build_uiwang_road_traffic_merge.py` 출력 정의(18~22), 소스 엔드포인트 기록(563~564)

## 4) 출처 요약 로그
- 파일: `uiwang_investigation_sources.csv`
