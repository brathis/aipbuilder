import logging
from typing import Tuple

import pyproj
import shapely

log = logging.getLogger(__name__)


__all__ = ["force_tuple", "get_distance_m"]


def force_tuple(p: shapely.Point | Tuple[float, float]) -> Tuple[float, float]:
    if isinstance(p, shapely.Point):
        return (p.coords[0][0], p.coords[0][1])
    return p


def get_distance_m(
    p1_wgs84: shapely.Point | Tuple[float, float],
    p2_wgs84: shapely.Point | Tuple[float, float],
) -> float:
    p1_wgs84 = force_tuple(p1_wgs84)
    p2_wgs84 = force_tuple(p2_wgs84)
    _, _, d = pyproj.geod.Geod(ellps="WGS84").inv(*p1_wgs84, *p2_wgs84)
    return d
