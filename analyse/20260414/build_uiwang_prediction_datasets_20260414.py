#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "previous_data"
OUT_DIR = Path(__file__).resolve().parent

IN_NAMED = DATA / "uiwang_named_roads_with_traffic_summary.csv"
IN_ALL = DATA / "uiwang_all_roads_with_traffic_inferred.csv"
IN_ROUTE_INFO = DATA / "gg_road_info_list.csv"
IN_ROUTE_NAME_STATS = DATA / "uiwang_gg_route_traffic_stats.csv"
IN_ROUTE_NO_STATS = DATA / "uiwang_gg_routeno_traffic_stats.csv"
IN_RAW_TRAFFIC = DATA / "gg_road_traffic_info_list.csv"

OUT_MAJOR = OUT_DIR / "uiwang_major_12_roads_prediction_features_20260414.csv"
OUT_ALL = OUT_DIR / "uiwang_all_roads_prediction_features_20260414.csv"

MAJOR_ROADS_ORDER = [
    "봉담과천로",
    "수도권제1순환고속도로",
    "안양판교로",
    "제2경인고속도로",
    "경수대로",
    "덕영대로",
    "영동고속도로",
    "수원문산고속도로",
    "오봉로",
    "하오개로",
    "흥안대로",
    "고천지하차도",
]

ROAD_GRADE_LABEL = {
    "봉담과천로": "광역 주간선도로",
    "수도권제1순환고속도로": "고속도로",
    "안양판교로": "1차 간선도로",
    "제2경인고속도로": "고속도로",
    "경수대로": "1차 간선도로",
    "덕영대로": "보조 간선도로",
    "영동고속도로": "고속도로",
    "수원문산고속도로": "고속도로",
    "오봉로": "보조 간선도로",
    "하오개로": "보조 간선도로",
    "흥안대로": "1차 간선도로",
    "고천지하차도": "1차 간선도로",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def normalize_text(value: str) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", "", str(value)).strip()


def extract_first_number(value: str) -> str:
    text = str(value or "")
    m = re.search(r"\d+", text)
    return m.group(0) if m else ""


def to_float(value: str) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def numeric_sort_key(row: dict[str, str]) -> tuple[float, float]:
    total_len = to_float(row.get("total_length_m", ""))
    seg_cnt = to_float(row.get("segment_count", ""))
    return (total_len or -1.0, seg_cnt or -1.0)


def summarize_raw_rows(rows: list[dict[str, str]]) -> dict[str, object]:
    vols: list[float] = []
    spds: list[float] = []
    trvls: list[float] = []
    congs: list[float] = []
    coll_dates: set[str] = set()

    for row in rows:
        v = to_float(row.get("vol", ""))
        s = to_float(row.get("spd", ""))
        t = to_float(row.get("trvlTime", ""))
        c = to_float(row.get("congGrade", ""))
        if v is not None:
            vols.append(v)
        if s is not None:
            spds.append(s)
        if t is not None:
            trvls.append(t)
        if c is not None:
            congs.append(c)
        coll = str(row.get("collDate", "")).strip()
        if coll:
            coll_dates.add(coll)

    row_count = len(rows)
    zero_count = sum(1 for x in vols if x == 0.0)
    return {
        "raw_obs_rows": row_count,
        "raw_obs_zero_vol_ratio": round((zero_count / row_count), 6) if row_count else "",
        "raw_obs_mean_vol": round(mean(vols), 6) if vols else "",
        "raw_obs_mean_spd": round(mean(spds), 6) if spds else "",
        "raw_obs_mean_trvlTime": round(mean(trvls), 6) if trvls else "",
        "raw_obs_mean_congGrade": round(mean(congs), 6) if congs else "",
        "raw_obs_unique_collDate_count": len(coll_dates),
    }


def build_major_12_csv(named_rows: list[dict[str, str]]) -> None:
    out_rows: list[dict[str, object]] = []

    for road_name in MAJOR_ROADS_ORDER:
        norm = normalize_text(road_name)
        candidates = [r for r in named_rows if normalize_text(r.get("road_name", "")) == norm]

        if not candidates:
            out_rows.append(
                {
                    "road_name": road_name,
                    "road_grade_label": ROAD_GRADE_LABEL.get(road_name, ""),
                    "match_found": "no",
                    "match_candidate_count": 0,
                    "highway": "",
                    "segment_count": "",
                    "total_length_km": "",
                    "vol_mean": "",
                    "spd_mean": "",
                    "trvlTime_mean": "",
                    "traffic_match": "",
                    "traffic_match_method": "",
                    "matched_route_name_norm": "",
                    "matched_route_no": "",
                    "traffic_rows_used": "",
                    "source_traffic": "",
                }
            )
            continue

        best = sorted(candidates, key=numeric_sort_key, reverse=True)[0]
        out_rows.append(
            {
                "road_name": best.get("road_name", road_name),
                "road_grade_label": ROAD_GRADE_LABEL.get(road_name, ""),
                "match_found": "yes",
                "match_candidate_count": len(candidates),
                "highway": best.get("highway", ""),
                "segment_count": best.get("segment_count", ""),
                "total_length_km": best.get("total_length_km", ""),
                "vol_mean": best.get("vol_mean", ""),
                "spd_mean": best.get("spd_mean", ""),
                "trvlTime_mean": best.get("trvlTime_mean", ""),
                "traffic_match": best.get("traffic_match", ""),
                "traffic_match_method": best.get("traffic_match_method", ""),
                "matched_route_name_norm": best.get("matched_route_name_norm", ""),
                "matched_route_no": best.get("matched_route_no", ""),
                "traffic_rows_used": best.get("traffic_rows_used", ""),
                "source_traffic": best.get("source_traffic", ""),
            }
        )

    fieldnames = [
        "road_name",
        "road_grade_label",
        "match_found",
        "match_candidate_count",
        "highway",
        "segment_count",
        "total_length_km",
        "vol_mean",
        "spd_mean",
        "trvlTime_mean",
        "traffic_match",
        "traffic_match_method",
        "matched_route_name_norm",
        "matched_route_no",
        "traffic_rows_used",
        "source_traffic",
    ]
    write_csv(OUT_MAJOR, out_rows, fieldnames)


def build_all_roads_csv(
    base_rows: list[dict[str, str]],
    route_info_rows: list[dict[str, str]],
    route_name_stats_rows: list[dict[str, str]],
    route_no_stats_rows: list[dict[str, str]],
    raw_rows: list[dict[str, str]],
) -> None:
    route_info_by_no: dict[str, dict[str, str]] = {}
    route_info_by_name: dict[str, dict[str, str]] = {}
    route_id_to_info: dict[str, dict[str, str]] = {}

    for row in route_info_rows:
        route_id = str(row.get("routeId", "")).strip()
        route_no_num = extract_first_number(row.get("routeNo", ""))
        route_nm_norm = normalize_text(row.get("routeNm", ""))

        if route_id:
            route_id_to_info[route_id] = row
        if route_no_num and route_no_num not in route_info_by_no:
            route_info_by_no[route_no_num] = row
        if route_nm_norm and route_nm_norm not in route_info_by_name:
            route_info_by_name[route_nm_norm] = row

    route_no_stats_by_no = {str(r.get("route_no", "")).strip(): r for r in route_no_stats_rows}
    route_name_stats_by_name = {
        normalize_text(r.get("route_name_norm", "")): r for r in route_name_stats_rows if normalize_text(r.get("route_name_norm", ""))
    }

    raw_by_route_no: dict[str, list[dict[str, str]]] = defaultdict(list)
    raw_by_route_name: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in raw_rows:
        route_id = str(row.get("routeId", "")).strip()
        route_name_norm = normalize_text(row.get("routeNm", ""))

        route_info = route_id_to_info.get(route_id, {})
        route_no_num = extract_first_number(route_info.get("routeNo", ""))

        if route_no_num:
            raw_by_route_no[route_no_num].append(row)
        if route_name_norm:
            raw_by_route_name[route_name_norm].append(row)

    raw_stats_by_no = {k: summarize_raw_rows(v) for k, v in raw_by_route_no.items()}
    raw_stats_by_name = {k: summarize_raw_rows(v) for k, v in raw_by_route_name.items()}

    out_rows: list[dict[str, object]] = []
    for row in base_rows:
        matched_no = str(row.get("matched_route_no", "")).strip()
        matched_name = normalize_text(row.get("matched_route_name_norm", ""))

        no_stats = route_no_stats_by_no.get(matched_no, {})
        name_stats = route_name_stats_by_name.get(matched_name, {})

        route_info = route_info_by_no.get(matched_no)
        if route_info is None:
            route_info = route_info_by_name.get(matched_name, {})

        raw_stats = raw_stats_by_no.get(matched_no)
        if raw_stats is None:
            raw_stats = raw_stats_by_name.get(matched_name, {})

        out_rows.append(
            {
                "way_id": row.get("way_id", ""),
                "name": row.get("name", ""),
                "highway": row.get("highway", ""),
                "ref": row.get("ref", ""),
                "lanes": row.get("lanes", ""),
                "maxspeed": row.get("maxspeed", ""),
                "oneway": row.get("oneway", ""),
                "bridge": row.get("bridge", ""),
                "tunnel": row.get("tunnel", ""),
                "length_m": row.get("length_m", ""),
                "traffic_match": row.get("traffic_match", ""),
                "traffic_match_method": row.get("traffic_match_method", ""),
                "traffic_match_original": row.get("traffic_match_original", ""),
                "traffic_observed_match": row.get("traffic_observed_match", ""),
                "traffic_inferred": row.get("traffic_inferred", ""),
                "inferred_distance_m": row.get("inferred_distance_m", ""),
                "vol_mean": row.get("vol_mean", ""),
                "vol_min": row.get("vol_min", ""),
                "vol_max": row.get("vol_max", ""),
                "spd_mean": row.get("spd_mean", ""),
                "trvlTime_mean": row.get("trvlTime_mean", ""),
                "traffic_rows_used": row.get("traffic_rows_used", ""),
                "congGrade_proxy": raw_stats.get("raw_obs_mean_congGrade", ""),
                "matched_route_name_norm": row.get("matched_route_name_norm", ""),
                "matched_route_no": matched_no,
                "boundary_validation_status": row.get("boundary_validation_status", ""),
                "boundary_inside_vertex_count": row.get("boundary_inside_vertex_count", ""),
                "boundary_outside_vertex_count": row.get("boundary_outside_vertex_count", ""),
                "boundary_intersects": row.get("boundary_intersects", ""),
                "source_road": row.get("source_road", ""),
                "source_traffic": row.get("source_traffic", ""),
                "routeno_row_count": no_stats.get("row_count", ""),
                "routeno_vol_mean": no_stats.get("vol_mean", ""),
                "routeno_spd_mean": no_stats.get("spd_mean", ""),
                "routeno_trvlTime_mean": no_stats.get("trvlTime_mean", ""),
                "routename_row_count": name_stats.get("row_count", ""),
                "routename_vol_mean": name_stats.get("vol_mean", ""),
                "routename_spd_mean": name_stats.get("spd_mean", ""),
                "routename_trvlTime_mean": name_stats.get("trvlTime_mean", ""),
                "route_info_routeId": route_info.get("routeId", ""),
                "route_info_routeNm": route_info.get("routeNm", ""),
                "route_info_routeNo": route_info.get("routeNo", ""),
                "route_info_roadRank": route_info.get("roadRank", ""),
                "route_info_routeTp": route_info.get("routeTp", ""),
                "raw_obs_rows": raw_stats.get("raw_obs_rows", ""),
                "raw_obs_zero_vol_ratio": raw_stats.get("raw_obs_zero_vol_ratio", ""),
                "raw_obs_mean_vol": raw_stats.get("raw_obs_mean_vol", ""),
                "raw_obs_mean_spd": raw_stats.get("raw_obs_mean_spd", ""),
                "raw_obs_mean_trvlTime": raw_stats.get("raw_obs_mean_trvlTime", ""),
                "raw_obs_mean_congGrade": raw_stats.get("raw_obs_mean_congGrade", ""),
                "raw_obs_unique_collDate_count": raw_stats.get("raw_obs_unique_collDate_count", ""),
            }
        )

    fieldnames = [
        "way_id",
        "name",
        "highway",
        "ref",
        "lanes",
        "maxspeed",
        "oneway",
        "bridge",
        "tunnel",
        "length_m",
        "traffic_match",
        "traffic_match_method",
        "traffic_match_original",
        "traffic_observed_match",
        "traffic_inferred",
        "inferred_distance_m",
        "vol_mean",
        "vol_min",
        "vol_max",
        "spd_mean",
        "trvlTime_mean",
        "traffic_rows_used",
        "congGrade_proxy",
        "matched_route_name_norm",
        "matched_route_no",
        "boundary_validation_status",
        "boundary_inside_vertex_count",
        "boundary_outside_vertex_count",
        "boundary_intersects",
        "source_road",
        "source_traffic",
        "routeno_row_count",
        "routeno_vol_mean",
        "routeno_spd_mean",
        "routeno_trvlTime_mean",
        "routename_row_count",
        "routename_vol_mean",
        "routename_spd_mean",
        "routename_trvlTime_mean",
        "route_info_routeId",
        "route_info_routeNm",
        "route_info_routeNo",
        "route_info_roadRank",
        "route_info_routeTp",
        "raw_obs_rows",
        "raw_obs_zero_vol_ratio",
        "raw_obs_mean_vol",
        "raw_obs_mean_spd",
        "raw_obs_mean_trvlTime",
        "raw_obs_mean_congGrade",
        "raw_obs_unique_collDate_count",
    ]

    write_csv(OUT_ALL, out_rows, fieldnames)


def main() -> None:
    named_rows = read_csv(IN_NAMED)
    base_rows = read_csv(IN_ALL)
    route_info_rows = read_csv(IN_ROUTE_INFO)
    route_name_stats_rows = read_csv(IN_ROUTE_NAME_STATS)
    route_no_stats_rows = read_csv(IN_ROUTE_NO_STATS)
    raw_rows = read_csv(IN_RAW_TRAFFIC)

    build_major_12_csv(named_rows)
    build_all_roads_csv(base_rows, route_info_rows, route_name_stats_rows, route_no_stats_rows, raw_rows)

    print(f"wrote: {OUT_MAJOR}")
    print(f"wrote: {OUT_ALL}")


if __name__ == "__main__":
    main()
