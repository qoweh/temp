#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import shutil
import sqlite3
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent

IN_POINTS = ROOT / "previous_data" / "uiwang_road_icing_heatmap_points.geojson"
IN_BOUNDARY = ROOT / "_external_qgis_second_report" / "second report" / "gpt" / "this_uiwang_boundary.geojson"
BASE_GPKG = ROOT / "uiwang_road_icing_heatmap_points-clip-version.gpkg"

OUT_GPKG = OUT_DIR / "uiwang_road_icing_heatmap_points-clip-version_rebuilt_20260414.gpkg"
OUT_COMPARE_JSON = OUT_DIR / "uiwang_road_icing_heatmap_points_clip_compare_20260414.json"

TABLE_NAME = "uiwang_road_icing_heatmap_points-clip-version"
SRID = 4326


def is_point_on_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float, eps: float = 1e-12) -> bool:
    cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    if abs(cross) > eps:
        return False
    dot = (px - ax) * (bx - ax) + (py - ay) * (by - ay)
    if dot < -eps:
        return False
    seg_len_sq = (bx - ax) ** 2 + (by - ay) ** 2
    if dot - seg_len_sq > eps:
        return False
    return True


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    n = len(ring)
    if n < 3:
        return False

    j = n - 1
    for i in range(n):
        xi, yi = float(ring[i][0]), float(ring[i][1])
        xj, yj = float(ring[j][0]), float(ring[j][1])

        if is_point_on_segment(x, y, xi, yi, xj, yj):
            return True

        intersects = ((yi > y) != (yj > y))
        if intersects:
            x_inter = (xj - xi) * (y - yi) / (yj - yi + 1e-30) + xi
            if x < x_inter:
                inside = not inside
        j = i

    return inside


def point_in_polygon(x: float, y: float, outer: list[list[float]], holes: list[list[list[float]]]) -> bool:
    if not point_in_ring(x, y, outer):
        return False
    for hole in holes:
        if point_in_ring(x, y, hole):
            return False
    return True


def extract_polygons(geom: dict) -> list[tuple[list[list[float]], list[list[list[float]]]]]:
    gtype = (geom or {}).get("type")
    coords = (geom or {}).get("coordinates") or []
    out: list[tuple[list[list[float]], list[list[list[float]]]]] = []

    if gtype == "Polygon":
        if coords:
            outer = coords[0]
            holes = coords[1:] if len(coords) > 1 else []
            out.append((outer, holes))
    elif gtype == "MultiPolygon":
        for poly in coords:
            if poly:
                outer = poly[0]
                holes = poly[1:] if len(poly) > 1 else []
                out.append((outer, holes))

    return out


def load_boundary_polygons(path: Path) -> list[tuple[list[list[float]], list[list[list[float]]]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = payload.get("features", [])

    polygons: list[tuple[list[list[float]], list[list[list[float]]]]] = []
    for ft in features:
        polygons.extend(extract_polygons(ft.get("geometry", {})))
    return polygons


def clip_points_to_boundary(points_path: Path, boundary_polygons: list[tuple[list[list[float]], list[list[list[float]]]]]) -> list[dict]:
    payload = json.loads(points_path.read_text(encoding="utf-8"))
    features = payload.get("features", [])

    kept: list[dict] = []
    for ft in features:
        geom = ft.get("geometry", {})
        if geom.get("type") != "Point":
            continue

        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        x, y = float(coords[0]), float(coords[1])

        inside_any = False
        for outer, holes in boundary_polygons:
            if point_in_polygon(x, y, outer, holes):
                inside_any = True
                break

        if inside_any:
            kept.append(ft)

    return kept


def gpkg_point_blob(x: float, y: float, srid: int = SRID) -> bytes:
    # GPKG geometry header (8 bytes): magic 'GP', version 0, flags 1(little-endian, no envelope), srid(int32 LE)
    header = b"GP" + bytes([0, 1]) + struct.pack("<i", srid)
    # WKB Point LE: byteOrder(1) + geomType(1) + x + y
    wkb = struct.pack("<BIdd", 1, 1, x, y)
    return header + wkb


def rebuild_gpkg(base_gpkg: Path, out_gpkg: Path, clipped_features: list[dict]) -> dict:
    shutil.copy2(base_gpkg, out_gpkg)

    con = sqlite3.connect(out_gpkg)
    cur = con.cursor()

    # qgis/ogr가 만든 rtree 트리거는 ST_IsEmpty 같은 공간함수를 요구하는데,
    # 현재 sqlite 런타임에는 해당 함수가 없어 insert 시 오류가 난다.
    # 따라서 rtree를 제거하고 일반 feature table만 갱신한다.
    rtree_triggers = [
        name
        for (name,) in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'rtree_%' ORDER BY name"
        ).fetchall()
    ]
    for trig in rtree_triggers:
        cur.execute(f'DROP TRIGGER IF EXISTS "{trig}"')

    rtree_tables = [
        name
        for (name,) in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'rtree_%' ORDER BY name"
        ).fetchall()
    ]
    for tbl in rtree_tables:
        cur.execute(f'DROP TABLE IF EXISTS "{tbl}"')

    cur.execute(
        "DELETE FROM gpkg_extensions WHERE table_name = ? AND extension_name = 'gpkg_rtree_index'",
        (TABLE_NAME,),
    )

    cur.execute(f'DELETE FROM "{TABLE_NAME}"')
    con.commit()

    insert_sql = (
        f'INSERT INTO "{TABLE_NAME}" '
        '(geom, way_id, highway, name, traffic_match, vol_mean, segment_len_m, kde_weight) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
    )

    xs: list[float] = []
    ys: list[float] = []

    for ft in clipped_features:
        geom = ft.get("geometry", {})
        props = ft.get("properties", {}) or {}
        coords = geom.get("coordinates") or []
        x, y = float(coords[0]), float(coords[1])
        xs.append(x)
        ys.append(y)

        blob = gpkg_point_blob(x, y)
        cur.execute(
            insert_sql,
            (
                sqlite3.Binary(blob),
                str(props.get("way_id", "")),
                str(props.get("highway", "")),
                str(props.get("name", "")),
                str(props.get("traffic_match", "")),
                float(props.get("vol_mean", 0.0) or 0.0),
                float(props.get("segment_len_m", 0.0) or 0.0),
                float(props.get("kde_weight", 0.0) or 0.0),
            ),
        )

    if xs and ys:
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        cur.execute(
            'UPDATE gpkg_contents SET min_x=?, min_y=?, max_x=?, max_y=?, srs_id=? WHERE table_name=?',
            (min_x, min_y, max_x, max_y, SRID, TABLE_NAME),
        )

    con.commit()
    con.close()

    return {
        "rows_inserted": len(clipped_features),
        "min_x": min(xs) if xs else None,
        "min_y": min(ys) if ys else None,
        "max_x": max(xs) if xs else None,
        "max_y": max(ys) if ys else None,
    }


def parse_point_from_blob(blob: bytes) -> tuple[float, float]:
    # skip 8-byte gpkg header, parse wkb point
    wkb = blob[8:]
    # wkb: [byte_order(1)][geom_type(4)][x(8)][y(8)]
    x = struct.unpack("<d", wkb[5:13])[0]
    y = struct.unpack("<d", wkb[13:21])[0]
    return x, y


def read_table_rows_for_compare(gpkg_path: Path) -> tuple[int, set[tuple], dict[str, float]]:
    con = sqlite3.connect(gpkg_path)
    cur = con.cursor()
    rows = cur.execute(
        f'SELECT geom, way_id, highway, name, traffic_match, vol_mean, segment_len_m, kde_weight FROM "{TABLE_NAME}"'
    ).fetchall()
    con.close()

    key_set: set[tuple] = set()
    vol_vals: list[float] = []
    kde_vals: list[float] = []

    for geom, way_id, highway, name, traffic_match, vol_mean, segment_len_m, kde_weight in rows:
        x, y = parse_point_from_blob(geom)
        key = (
            round(x, 7),
            round(y, 7),
            str(way_id or ""),
            str(highway or ""),
            str(name or ""),
            str(traffic_match or ""),
            round(float(vol_mean or 0.0), 6),
            round(float(segment_len_m or 0.0), 3),
            round(float(kde_weight or 0.0), 6),
        )
        key_set.add(key)
        vol_vals.append(float(vol_mean or 0.0))
        kde_vals.append(float(kde_weight or 0.0))

    summary = {
        "mean_vol": round(sum(vol_vals) / len(vol_vals), 6) if vol_vals else 0.0,
        "mean_kde_weight": round(sum(kde_vals) / len(kde_vals), 6) if kde_vals else 0.0,
    }
    return len(rows), key_set, summary


def main() -> None:
    boundary_polygons = load_boundary_polygons(IN_BOUNDARY)
    clipped_features = clip_points_to_boundary(IN_POINTS, boundary_polygons)

    rebuild_info = rebuild_gpkg(BASE_GPKG, OUT_GPKG, clipped_features)

    old_count, old_keys, old_summary = read_table_rows_for_compare(BASE_GPKG)
    new_count, new_keys, new_summary = read_table_rows_for_compare(OUT_GPKG)

    only_old = len(old_keys - new_keys)
    only_new = len(new_keys - old_keys)
    common = len(old_keys & new_keys)

    report = {
        "input_points": str(IN_POINTS),
        "input_boundary": str(IN_BOUNDARY),
        "base_gpkg": str(BASE_GPKG),
        "rebuilt_gpkg": str(OUT_GPKG),
        "rebuild_info": rebuild_info,
        "compare": {
            "old_row_count": old_count,
            "new_row_count": new_count,
            "common_feature_keys": common,
            "only_in_old": only_old,
            "only_in_new": only_new,
            "old_summary": old_summary,
            "new_summary": new_summary,
        },
    }

    OUT_COMPARE_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
