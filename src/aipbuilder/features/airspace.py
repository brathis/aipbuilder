import logging
import re
from typing import Any, Dict, List, Protocol, Tuple

import geopandas
import shapely
from shapely import Polygon

from aipbuilder.country_borders import get_border_segment
from aipbuilder.crs import CRS_WGS84
from aipbuilder.curved_geometries import arc_around_point, circle_around_point
from aipbuilder.dms_to_decimal import (
    dms_match_to_decimal,
    dms_string_to_decimal,
    dms_to_decimal,
    is_valid_dms_format,
)
from aipbuilder.providers import BorderProvider, ProviderToken
from aipbuilder.util import get_csv_reader

__all__ = [
    "parse_airspaces",
]


log = logging.getLogger(__name__)


class InputGeometry(Protocol):
    @classmethod
    def matches(definition: str) -> re.Match | None: ...

    @classmethod
    def parse(
        match: re.Match, previous, subsequent, providers
    ) -> List[Tuple[float, float]]: ...

    @classmethod
    def can_process(previous, subsequent) -> bool: ...


class VertexInputGeometry:
    @classmethod
    def matches(cls, definition):
        return is_valid_dms_format(definition)

    @classmethod
    def parse(cls, match, previous, subsequent, providers):
        return [dms_match_to_decimal(match)]

    @classmethod
    def can_process(cls, previous, subsequent):
        return True


class ArcInputGeometry:
    REGEX = re.compile(
        r"^ARC\((?P<center>[\d NSEW/\.]+), (?P<radiusNm>[\d\.]+), (?P<direction>cw|ccw)\)$"
    )

    @classmethod
    def matches(cls, definition):
        return cls.REGEX.fullmatch(definition)

    @classmethod
    def parse(cls, match, previous, subsequent, providers):
        center = dms_string_to_decimal(match["center"])
        radius_nm = float(match["radiusNm"])
        direction = match["direction"]
        return arc_around_point(center, previous, subsequent, radius_nm, direction, 100)

    @classmethod
    def can_process(cls, previous, subsequent):
        return previous is not None and subsequent is not None


class CircleInputGeometry:
    REGEX = re.compile(r"^CIRCLE\((?P<center>[\d NSEW/]+), (?P<radiusNm>[\d\.]+)\)$")

    @classmethod
    def matches(cls, definition):
        return cls.REGEX.fullmatch(definition)

    @classmethod
    def parse(cls, match, previous, subsequent, providers):
        center = dms_string_to_decimal(match["center"])
        radius_nm = float(match["radiusNm"])
        return circle_around_point(center, radius_nm, 100)

    @classmethod
    def can_process(cls, previous, subsequent):
        return True


class BorderInputGeometry:
    REGEX = re.compile(r"^BORDER\((?P<borderName>[A-Z\+]+)(?P<invert>, I)?\)$")

    @classmethod
    def matches(cls, definition):
        return cls.REGEX.fullmatch(definition)

    @classmethod
    def parse(cls, match, previous, subsequent, providers):
        assert ProviderToken.BORDER_PROVIDER in providers, (
            f"error parsing {match}, missing BORDER_PROVIDER, providers: {providers}"
        )
        border_provider: BorderProvider = providers[ProviderToken.BORDER_PROVIDER]
        border = border_provider.get_border(match["borderName"])
        invert = match["invert"] is not None

        border_segment = get_border_segment(
            shapely.Point(previous),
            shapely.Point(subsequent),
            border,
            invert,
        )
        if border_segment is None:
            return []

        return border_segment.coords

    @classmethod
    def can_process(cls, previous, subsequent):
        return previous is not None and subsequent is not None


DEFAULT_INPUT_GEOMETRY_TYPES = {
    "vertex": VertexInputGeometry,
    "circle": CircleInputGeometry,
    "arc": ArcInputGeometry,
    "border": BorderInputGeometry,
}


def parse_airspaces(
    path: str,
    providers: Dict[ProviderToken, Any],
    input_geometry_overrides: Dict[str, InputGeometry] | None = None,
) -> geopandas.GeoDataFrame:
    airspace_names = []
    airspace_geometries = []
    with open(path, "r") as definition_file:
        reader = get_csv_reader(definition_file)
        for row in reader:
            log.info(f"Parsing airspace {row['name']}")
            airspace_names.append(row["name"])
            airspace_geometries.append(
                _parse_polygon_definition(
                    row["geometry"], providers, input_geometry_overrides
                )
            )
    return geopandas.GeoDataFrame(
        {"name": airspace_names, "geometry": airspace_geometries}, crs=CRS_WGS84
    )


def _parse_polygon_definition(
    geometry: str,
    providers: Dict[ProviderToken, Any],
    input_geometry_overrides: Dict[str, InputGeometry] | None,
):
    geometry_components = geometry.split(" - ")
    input_geometry_types = [None for _ in range(len(geometry_components))]
    vertices = [None for _ in range(len(geometry_components))]
    component_indices_to_process = list(range(len(geometry_components)))
    while len(component_indices_to_process):
        log.debug(
            f"{len(component_indices_to_process)} components remaining to be processed"
        )
        len_before_iteration = len(component_indices_to_process)
        for i in component_indices_to_process:
            component = geometry_components[i]
            previous_vertices = vertices[(i - 1) % len(geometry_components)]
            previous_vertex = previous_vertices[-1] if previous_vertices else None
            subsequent_vertices = vertices[(i + 1) % len(geometry_components)]
            subsequent_vertex = subsequent_vertices[0] if subsequent_vertices else None
            input_geometry_type, component_vertices = _parse_polygon_component(
                component,
                previous_vertex,
                subsequent_vertex,
                providers,
                input_geometry_overrides,
            )
            if component_vertices is not None:
                component_indices_to_process.remove(i)
                input_geometry_types[i] = input_geometry_type
                vertices[i] = component_vertices
        len_after_iteration = len(component_indices_to_process)
        if len_before_iteration == len_after_iteration:
            raise RuntimeError(
                f"no progress made with {len_before_iteration} components remaining"
            )
    return Polygon(shell=_flatten_vertices(vertices, input_geometry_types))


def _parse_polygon_component(
    component: str,
    previous,
    subsequent,
    providers,
    input_geometry_overrides: Dict[str, InputGeometry] | None,
) -> Tuple[str, List[Tuple[float, float]]]:
    log.debug(
        f'parsing component "{component}" with previous "{previous}" and subsequent "{subsequent}"'
    )
    for input_type_name, input_type in _get_input_geometry_types(
        input_geometry_overrides
    ).items():
        if match := input_type.matches(component):
            if not input_type.can_process(previous, subsequent):
                log.debug(
                    f"skipping processing of component {component} because it cannot be processed"
                )
                return None, None
            return input_type_name, input_type.parse(
                match, previous, subsequent, providers
            )
    raise ValueError(
        f'no input geometry type matches component "{component}", skipping'
    )


def _flatten_vertices(vertices, input_geometry_types):
    flattened = []
    border_entry_point_indices = _get_border_entry_point_indices(input_geometry_types)
    for i, v in enumerate(vertices):
        # border entry vertices are already part of the border segment linestring
        if i not in border_entry_point_indices:
            flattened.extend(v)
    return flattened


def _get_border_entry_point_indices(input_geometry_types):
    border_indices = [
        i
        for i in range(len(input_geometry_types))
        if input_geometry_types[i] == "border"
    ]
    border_entry_point_indices = set()
    for b in border_indices:
        border_entry_point_indices.add(b - 1)
        border_entry_point_indices.add(b + 1)
    for bi in border_entry_point_indices:
        assert input_geometry_types[bi] == "vertex"
    return border_entry_point_indices


def _get_input_geometry_types(
    input_geometry_overrides: Dict[str, InputGeometry] | None = None,
):
    if not input_geometry_overrides:
        return DEFAULT_INPUT_GEOMETRY_TYPES
    return {**DEFAULT_INPUT_GEOMETRY_TYPES, **input_geometry_overrides}
