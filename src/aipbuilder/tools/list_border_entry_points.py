import argparse
import importlib
import logging
from typing import List

from aipbuilder.crs import CRS_WGS84
from aipbuilder.features.airspace import BorderInputGeometry, parse_airspaces
import geopandas
import shapely

from aipbuilder.providers import BorderProvider, ProviderToken
from aipbuilder.util import get_distance_m

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class EntryPointReportingBorderInputGeometry(BorderInputGeometry):
    def __init__(self, out_points, out_borders, out_distances, max_distance_m):
        super()
        self._out_points = out_points
        self._out_borders = out_borders
        self._out_distances = out_distances
        self._max_distance_m = max_distance_m

    def parse(self, match, previous, subsequent, providers):
        border_provider = providers.get(ProviderToken.BORDER_PROVIDER, None)
        border = match.group("borderName")
        self._process_point(border_provider, border, previous)
        self._process_point(border_provider, border, subsequent)
        return []

    def _process_point(self, border_provider, border_name, entry_point):
        if border_provider:
            distance = self._get_distance(border_provider, border_name, entry_point)
            if self._max_distance_m is not None and distance <= self._max_distance_m:
                return
            self._out_points.append(entry_point)
            self._out_borders.append(border_name)
            self._out_distances.append(distance)
        else:
            self._out_points.append(entry_point)
            self._out_borders.append(border_name)
            self._out_distances.append(None)

    def _get_distance(
        self, border_provider: BorderProvider, border_name, entry_point
    ) -> float:
        border = border_provider.get_border(border_name)
        assert isinstance(border, shapely.LineString)
        border_tree = shapely.STRtree([shapely.Point(*c) for c in border.coords])
        nearest_border_index = border_tree.nearest(shapely.Point(entry_point))
        nearest_border_point = [c for c in border.coords][nearest_border_index]
        return get_distance_m(entry_point, nearest_border_point)


def list_border_entry_points(
    airspace_definition_file_paths: List[str],
    out_file_path: str,
    border_provider_module: str | None,
    max_distance_m: float | None,
) -> None:
    border_provider = (
        load_border_provider(border_provider_module) if border_provider_module else None
    )
    providers = (
        {ProviderToken.BORDER_PROVIDER: border_provider} if border_provider else {}
    )
    entry_points = []
    borders = []
    distances = []
    for path in airspace_definition_file_paths:
        parse_airspaces(
            path,
            providers,
            {
                "border": EntryPointReportingBorderInputGeometry(
                    entry_points, borders, distances, max_distance_m
                )
            },
        )
    geopandas.GeoDataFrame(
        {
            "border": borders,
            "distance": distances,
            "geometry": [shapely.Point(p) for p in entry_points],
        },
        crs=CRS_WGS84,
    ).to_file(out_file_path)
    log.info(f"Wrote {len(entry_points)} border entry points to {out_file_path}")


def load_border_provider(border_provider_module_name: str) -> BorderProvider:
    mod = importlib.import_module(border_provider_module_name)
    border_providers = []
    for attribute_name in dir(mod):
        attribute = getattr(mod, attribute_name)
        if isinstance(attribute, BorderProvider) and not isinstance(attribute, type):
            border_providers.append(attribute)
    if not border_providers:
        raise RuntimeError(
            f"no border provider was found in module {border_provider_module_name}"
        )
    if len(border_providers) > 1:
        log.warning(
            f"found {len(border_providers)} border providers in module {border_provider_module_name}, picking {border_providers[0]}"
        )
    border_provider = border_providers[0]
    log.info(f"loaded border provider {border_provider}")
    return border_provider


def entrypoint():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "airspace-files", nargs="+", help="Path(s) to airspace definition CSV file(s)"
    )
    parser.add_argument(
        "entrypoint-file",
        help="Path where to write shapefile containing border entry points",
    )
    parser.add_argument(
        "--border-provider-module",
        help="Python module containing a border provider, if the entry points should also be validated against a source of geographical borders. The border provider must be named 'border_provider'.",
    )
    parser.add_argument(
        "--max-distance",
        type=float,
        help="Only include border entry points that are further than this distance (in meters) from the border",
    )
    args = parser.parse_args()
    list_border_entry_points(
        getattr(args, "airspace-files"),
        getattr(args, "entrypoint-file"),
        getattr(args, "border_provider_module"),
        getattr(args, "max_distance"),
    )


if __name__ == "__main__":
    entrypoint()
