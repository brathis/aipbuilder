import functools
import logging
from typing import Dict, List, Tuple

from aipbuilder.crs import CRS_WGS84
from aipbuilder.util import force_tuple, get_distance_m
import geopandas
import shapely

__all__ = ["get_border_segment", "compose_borders_from_gdf"]


log = logging.getLogger(__name__)


def get_border_segment(
    start: shapely.Point,
    end: shapely.Point,
    border: shapely.LineString,
    invert: bool,
    tolerance_m: int = 30,
) -> shapely.LineString | None:
    assert isinstance(start, shapely.Point)
    assert isinstance(end, shapely.Point)
    assert isinstance(border, shapely.LineString)

    border_points = _get_border_points(border)
    border_point_tree = _get_border_point_tree(border)
    start_point_index = border_point_tree.nearest(start)
    end_point_index = border_point_tree.nearest(end)
    if start_point_index == end_point_index:
        return None
    border_start_point = border_points[start_point_index]
    border_end_point = border_points[end_point_index]
    _assert_points_close_enough(start, border_start_point, tolerance_m)
    _assert_points_close_enough(end, border_end_point, tolerance_m)
    segment_point_coords = (
        _extract_points_in_range(start_point_index, end_point_index, border_points)
        if not invert
        else _extract_points_outside_range(
            start_point_index, end_point_index, border_points
        )
    )
    assert _points_equal(segment_point_coords[0], border_points[start_point_index]), (
        f"{segment_point_coords[0]=} {border_points[start_point_index]}="
    )
    assert _points_equal(segment_point_coords[-1], border_points[end_point_index]), (
        f"{segment_point_coords[-1]=} {border_points[end_point_index]}="
    )
    assert len(segment_point_coords), "border segment must not be empty"
    return shapely.LineString(segment_point_coords)


def _extract_points_in_range(start_index, end_index, points):
    selected_points = []
    if end_index >= start_index:
        selected_points = [
            list(points[i].coords)[0] for i in range(start_index, end_index + 1)
        ]
    else:
        selected_points = [
            list(points[i].coords)[0] for i in range(start_index, len(points))
        ]
        selected_points.extend(
            [list(points[i].coords)[0] for i in range(end_index + 1)]
        )
    return selected_points


def _extract_points_outside_range(start_index, end_index, points):
    selected_points = []
    if start_index >= end_index:
        selected_points = [
            list(points[i].coords)[0] for i in range(end_index, start_index + 1)
        ]
    else:
        selected_points = [
            list(points[i].coords)[0] for i in range(end_index, len(points))
        ]
        selected_points.extend(
            [list(points[i].coords)[0] for i in range(start_index + 1)]
        )
    selected_points.reverse()
    return selected_points


@functools.lru_cache
def _get_border_point_tree(border: shapely.LineString) -> shapely.STRtree:
    border_points = _get_border_points(border)
    return shapely.STRtree(border_points)


def _get_border_points(border: shapely.LineString) -> List[shapely.Point]:
    return [shapely.Point(*c) for c in border.coords]


def _points_equal(p1, p2, tol=1e-9) -> bool:
    if isinstance(p1, shapely.Point):
        p1 = p1.coords[0]
    if isinstance(p2, shapely.Point):
        p2 = p2.coords[0]
    return abs(p1[0] - p2[0]) < tol and abs(p1[1] - p2[1]) < tol


def _assert_points_close_enough(
    entry_point: shapely.Point | Tuple[float, float],
    border_point: shapely.Point | Tuple[float, float],
    tolerance_m: float,
) -> None:
    entry_point = force_tuple(entry_point)
    border_point = force_tuple(border_point)
    d = get_distance_m(entry_point, border_point)
    if d > tolerance_m:
        raise ValueError(
            f"entry point {entry_point} is too far from closest border point {border_point}, dist={d:.1f}m, tolerance={tolerance_m:.1f}m"
        )


def _join_coords_to_linestring(coords):
    all_coords = []
    for coord in coords:
        all_coords.extend(coord)
    return shapely.LineString(all_coords)


def compose_borders_from_gdf(
    gdf: geopandas.GeoDataFrame, compositions: Dict[str, List[Tuple[str, slice]]]
):
    out = {}
    for composition_name, composition in compositions.items():
        out[composition_name] = []
        for composition_item in composition:
            segment_name, segment_slice = composition_item
            segment = gdf.loc[gdf.name == segment_name].iloc[0].geometry
            out[composition_name].append(segment.coords[segment_slice])
        out[composition_name] = _join_coords_to_linestring(out[composition_name])
    return geopandas.GeoDataFrame(
        {"name": out.keys(), "geometry": out.values()}, crs=CRS_WGS84
    )
