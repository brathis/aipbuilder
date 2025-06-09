import csv
import logging
from typing import Tuple

import shapely
import pyproj


log = logging.getLogger(__name__)


__all__ = ["get_csv_reader"]


def _filter_commented_rows(fp):
    for row in fp:
        if row.startswith("#"):
            log.info(f'skipping line "{row.strip()}"')
        else:
            log.debug(f'processing line "{row}')
            yield row


def get_csv_reader(file) -> csv.DictReader:
    return csv.DictReader(_filter_commented_rows(file))


def force_tuple(p: shapely.Point | Tuple[float, float]):
    if isinstance(p, shapely.Point):
        return (p.coords[0][0], p.coords[0][1])
    return p


def get_distance_m(
    p1: shapely.Point | Tuple[float, float], p2: shapely.Point | Tuple[float, float]
) -> float:
    p1 = force_tuple(p1)
    p2 = force_tuple(p2)
    _, _, d = pyproj.geod.Geod(ellps="WGS84").inv(*p1, *p2)
    return d
