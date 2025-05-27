import math
from typing import Literal

import pyproj
import pyproj.enums

from crs import P_LV95

__all__ = [
    "arc_around_point",
    "circle_around_point",
]


def arc_around_point(
    center_wgs84,
    start_wgs84,
    end_wgs84,
    radius_nm,
    direction: Literal["cw", "ccw"],
    intermediate_points,
):
    center_lv95 = P_LV95(*center_wgs84)
    start_lv95 = P_LV95(*start_wgs84)
    end_lv95 = P_LV95(*end_wgs84)
    radius_m = _nm_to_m(radius_nm)
    points_metric = _arc_around_point_grid_metric(
        center_lv95,
        start_lv95,
        end_lv95,
        radius_m,
        direction,
        intermediate_points,
    )
    return [
        P_LV95.transform(*point, direction=pyproj.enums.TransformDirection.INVERSE)
        for point in points_metric
    ]


def _arc_around_point_grid_metric(
    center_lv95,
    start_lv95,
    end_lv95,
    radius_m,
    direction,
    intermediate_points,
):
    azimuth_start_rad = _get_azimuth_rad(center_lv95, start_lv95)
    azimuth_end_rad = _get_azimuth_rad(center_lv95, end_lv95)
    points = []
    points.append(_get_edge_point(center_lv95, azimuth_start_rad, radius_m))
    total_angle_rad = _get_total_angle_rad(
        azimuth_start_rad, azimuth_end_rad, direction
    )
    angle_increment_rad = total_angle_rad / (1 + intermediate_points)
    angle_rad = azimuth_start_rad
    for _ in range(intermediate_points):
        angle_rad += angle_increment_rad * (1 if direction == "ccw" else -1)
        points.append(_get_edge_point(center_lv95, angle_rad, radius_m))
    points.append(_get_edge_point(center_lv95, azimuth_end_rad, radius_m))
    return points


def circle_around_point(center_wgs84, radius_nm, intermediate_points):
    center_lv95 = P_LV95(*center_wgs84)
    radius_m = _nm_to_m(radius_nm)
    points_metric = _circle_around_point_grid_metric(
        center_lv95, radius_m, intermediate_points
    )
    return [
        P_LV95.transform(*point, direction=pyproj.enums.TransformDirection.INVERSE)
        for point in points_metric
    ]


def _circle_around_point_grid_metric(center_lv95, radius_m, intermediate_points):
    azimuth_increment_rad = 2 * math.pi / intermediate_points
    azimuth_rad = 0
    points = []
    for _ in range(intermediate_points):
        points.append(_get_edge_point(center_lv95, azimuth_rad, radius_m))
        azimuth_rad += azimuth_increment_rad
    return points


def _get_total_angle_rad(start, end, direction):
    angle = end - start if direction == "ccw" else start - end
    if angle < 0:
        angle += 2 * math.pi
    assert angle >= 0
    return angle


def _get_azimuth_rad(center, edge):
    dx = edge[0] - center[0]
    dy = edge[1] - center[1]
    return math.atan2(dy, dx)


def _get_edge_point(center_lv95, azimuth_rad, radius_m):
    cx, cy = center_lv95
    ux, uy = _get_unit_vector(azimuth_rad)
    dx, dy = ux * radius_m, uy * radius_m
    return cx + dx, cy + dy


def _get_unit_vector(azimuth_rad):
    return (math.cos(azimuth_rad), math.sin(azimuth_rad))


def _nm_to_m(value_nm):
    return value_nm * 1852
