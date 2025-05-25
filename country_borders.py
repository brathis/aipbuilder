import geopandas
import shapely

import dataclasses
import functools
import logging
from typing import List

from crs import CRS_WGS84

log = logging.getLogger(__name__)


@dataclasses.dataclass
class CountryBordersConfig:
    swissboundaries_path: str
    eu_boundaries_path: str


def get_country_borders(config: CountryBordersConfig) -> geopandas.GeoDataFrame:
    gdf = geopandas.GeoDataFrame(
        {
            "country": ["CH", "LI", "CH+LI", "DE"],
            "geometry": [
                _get_country_border_ch(config),
                _get_country_border_li(config),
                _get_country_border_ch_li(config),
                _get_country_border_de(config),
            ],
        },
        crs=CRS_WGS84,
    )
    return gdf


def get_border_segment(
    start: shapely.Point,
    end: shapely.Point,
    border: shapely.LineString,
    invert: bool,
    reverse: bool,
) -> shapely.LineString:
    assert isinstance(start, shapely.Point)
    assert isinstance(end, shapely.Point)
    assert isinstance(border, shapely.LineString)

    border_points = _get_border_points(border)
    border_point_index = _get_border_point_index(border)
    start_point_index = border_point_index.nearest(start)
    end_point_index = border_point_index.nearest(end)
    segment_point_coords = (
        _extract_points_in_range(start_point_index, end_point_index, border_points)
        if not invert
        else _extract_points_outside_range(
            start_point_index, end_point_index, border_points
        )
    )
    if reverse:
        segment_point_coords.reverse()
    return shapely.linestrings(segment_point_coords)


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
def _get_border_point_index(border: shapely.MultiLineString) -> shapely.STRtree:
    border_points = _get_border_points(border)
    return shapely.STRtree(border_points)


def _get_border_points(border: shapely.LineString) -> List[shapely.Point]:
    return [shapely.Point(*c) for c in border.coords]


def _get_country_border_ch(config: CountryBordersConfig) -> shapely.LineString:
    gdf_swissboundaries = _load_swissboundaries(config.swissboundaries_path)
    multi_polygon_ch = (
        gdf_swissboundaries.loc[gdf_swissboundaries.icc == "CH"].iloc[0].geometry
    )
    assert len(multi_polygon_ch.geoms) == 1
    polygon_ch = multi_polygon_ch.geoms[0]
    boundaries = polygon_ch.boundary
    # We only care about the outer boundary, so we ignore the enclaves
    return shapely.force_2d(boundaries.geoms[0])


def _get_country_border_li(config: CountryBordersConfig) -> shapely.LineString:
    gdf_swissboundaries = _load_swissboundaries(config.swissboundaries_path)
    multi_polygon_li = (
        gdf_swissboundaries.loc[gdf_swissboundaries.icc == "LI"].iloc[0].geometry
    )
    assert len(multi_polygon_li.geoms) == 1
    polygon_li = multi_polygon_li.geoms[0]
    return shapely.force_2d(polygon_li.boundary)


def _get_country_border_ch_li(config: CountryBordersConfig) -> shapely.LineString:
    # The outer border of the union of Switzerland and Liechtenstein (needed for CTA/FIR boundaries)
    border_ch = _get_country_border_ch(config)
    border_li = _get_country_border_li(config)
    inner_border = shapely.intersection(border_ch, border_li)
    outer_and_inner_border = shapely.union(border_ch, border_li)
    outer_border = shapely.difference(outer_and_inner_border, inner_border)
    return _flatten_multi_linestring(outer_border)


def _get_country_border_de(config: CountryBordersConfig) -> shapely.LineString:
    gdf_country_borders_eu = _load_eu_boundaries(config.eu_boundaries_path)
    return (
        gdf_country_borders_eu.loc[gdf_country_borders_eu.CNTR_ID == "DE"]
        .iloc[0]
        .geometry.geoms[0]
        .boundary.geoms[0]
    )


@functools.lru_cache
def _load_swissboundaries(path: str) -> geopandas.GeoDataFrame:
    return geopandas.read_file(
        path,
        layer="tlm_landesgebiet",
    ).to_crs(CRS_WGS84)


@functools.lru_cache
def _load_eu_boundaries(path: str) -> geopandas.GeoDataFrame:
    return geopandas.read_file(path)


def _flatten_multi_linestring(mls: shapely.MultiLineString) -> shapely.LineString:
    coords = []
    for linestring in mls.geoms:
        coords.extend(linestring.coords)
    return shapely.LineString(coords)
