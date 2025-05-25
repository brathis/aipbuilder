import csv
import enum
import logging
import re
from typing import Any, Dict, List, Protocol, Tuple

import geopandas
import shapely
import shapely.ops
from shapely import MultiLineString, LineString, Polygon

from country_borders import get_border_segment
from curved_geometries import arc_around_point, circle_around_point
from dms_to_decimal import dms_string_to_decimal, dms_to_decimal, is_valid_dms_format


log = logging.getLogger(__name__)


class ProviderToken(enum.Enum):
    BORDER_PROVIDER = 0


class BorderProvider(Protocol):
    def get_border(border_name: str) -> MultiLineString: ...


class InputGeometry:
    @classmethod
    def matches(definition: str) -> re.Match | None: ...

    @classmethod
    def parse(
        match: re.Match, previous, subsequent, providers
    ) -> List[Tuple[float, float]]: ...

    @classmethod
    def can_process(previous, subsequent) -> bool: ...


class VertexInputGeometry(InputGeometry):
    @classmethod
    def matches(cls, definition):
        return is_valid_dms_format(definition)

    @classmethod
    def parse(cls, match, previous, subsequent, providers):
        return [dms_to_decimal(match)]

    @classmethod
    def can_process(cls, previous, subsequent):
        return True


class ArcInputGeometry(InputGeometry):
    PATTERN = r"^ARC\((?P<center>[\d NSEW/\.]+), (?P<radiusNm>[\d\.]+), (?P<direction>cw|ccw)\)$"
    REGEX = re.compile(PATTERN)

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


class CircleInputGeometry(InputGeometry):
    PATTERN = r"^CIRCLE\((?P<center>[\d NSEW/]+), (?P<radiusNm>[\d\.]+)\)$"
    REGEX = re.compile(PATTERN)

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


class BorderInputGeometry(InputGeometry):
    PATTERN = r"^BORDER\((?P<borderName>[A-Z]+)(?P<invert>, I)?(?P<reverse>, R)?\)$"
    REGEX = re.compile(PATTERN)

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
        reverse = match["reverse"] is not None

        border_segment = get_border_segment(
            shapely.Point(previous), shapely.Point(subsequent), border, invert, reverse
        )

        return border_segment.coords

    @classmethod
    def can_process(cls, previous, subsequent):
        return previous is not None and subsequent is not None

    @classmethod
    def _find_segment_along_border(
        cls,
        entry_point: shapely.Point,
        exit_point: shapely.Point,
        border: shapely.MultiLineString,
    ) -> LineString:
        log.info(f"splitting {border} at {entry_point} and {exit_point}")
        split_border = shapely.ops.split(border, entry_point)
        assert len(split_border.geoms) == 2, (
            f"failed to split {border} at {entry_point}"
        )
        return []


INPUT_GEOMETRY_TYPES = [
    VertexInputGeometry,
    ArcInputGeometry,
    CircleInputGeometry,
    BorderInputGeometry,
]


def row_filter(fp):
    for row in fp:
        if row.startswith("#"):
            log.info(f'skipping line "{row}"')
        else:
            log.debug(f'processing line "{row}')
            yield row


def parse_geometry_definition_file(path: str, providers: Dict[ProviderToken, Any]):
    airspace_names = []
    airspace_geometries = []
    with open(path, "r") as definition_file:
        reader = csv.DictReader(row_filter(definition_file))
        for row in reader:
            airspace_names.append(row["name"])
            airspace_geometries.append(_parse_polygon(row["geometry"], providers))
    return geopandas.GeoDataFrame(
        {"name": airspace_names, "geometry": airspace_geometries}, crs="EPSG:4326"
    )


def _parse_polygon(geometry: str, providers: Dict[ProviderToken, Any]):
    geometry_components = geometry.split(" - ")
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
            component_vertices = _parse_geometry_component(
                component, previous_vertex, subsequent_vertex, providers
            )
            if component_vertices is not None:
                component_indices_to_process.remove(i)
                vertices[i] = component_vertices
        len_after_iteration = len(component_indices_to_process)
        if len_before_iteration == len_after_iteration:
            raise RuntimeError(
                f"no progress made with {len_before_iteration} components remaining"
            )
    return Polygon(shell=_flatten_vertices(vertices))


def _parse_geometry_component(component: str, previous, subsequent, providers):
    log.debug(
        f'parsing component "{component}" with previous "{previous}" and subsequent "{subsequent}"'
    )
    for input_type in INPUT_GEOMETRY_TYPES:
        if match := input_type.matches(component):
            if not input_type.can_process(previous, subsequent):
                log.debug(
                    f"skipping processing of component {component} because it cannot be processed"
                )
                return None
            return input_type.parse(match, previous, subsequent, providers)
    raise ValueError(
        f'no input geometry type matches component "{component}", skipping'
    )


def _flatten_vertices(vertices):
    flattened = []
    for v in vertices:
        flattened.extend(v)
    return flattened
