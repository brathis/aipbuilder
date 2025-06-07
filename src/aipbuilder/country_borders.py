import shapely

import functools
import logging
from typing import List


__all__ = ["get_border_segment"]


log = logging.getLogger(__name__)


def get_border_segment(
    start: shapely.Point,
    end: shapely.Point,
    border: shapely.LineString,
    invert: bool,
    reverse: bool,
) -> shapely.LineString | None:
    assert isinstance(start, shapely.Point)
    assert isinstance(end, shapely.Point)
    assert isinstance(border, shapely.LineString)

    border_points = _get_border_points(border)
    border_point_index = _get_border_point_index(border)
    start_point_index = border_point_index.nearest(start)
    end_point_index = border_point_index.nearest(end)
    if start_point_index == end_point_index:
        return None
    segment_point_coords = (
        _extract_points_in_range(start_point_index, end_point_index, border_points)
        if not invert
        else _extract_points_outside_range(
            start_point_index, end_point_index, border_points
        )
    )
    if reverse:
        segment_point_coords.reverse()
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
    return selected_points


@functools.lru_cache
def _get_border_point_index(border: shapely.LineString) -> shapely.STRtree:
    border_points = _get_border_points(border)
    return shapely.STRtree(border_points)


def _get_border_points(border: shapely.LineString) -> List[shapely.Point]:
    return [shapely.Point(*c) for c in border.coords]
