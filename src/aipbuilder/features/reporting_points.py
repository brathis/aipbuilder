import geopandas
import shapely

from aipbuilder.dms_to_decimal import dms_string_to_decimal
from aipbuilder.util import get_csv_reader


__all__ = ["parse_reporting_points"]


def parse_reporting_points(path: str) -> geopandas.GeoDataFrame:
    field_aerodrome = []
    field_designator = []
    field_geometry = []
    field_compulsory = []
    field_altitude_restriction = []
    field_provenance = []
    with open(path, "r") as reporting_points_file:
        reader = get_csv_reader(reporting_points_file)
        for row in reader:
            field_aerodrome.append(row["aerodrome"])
            field_designator.append(row["designator"])
            field_geometry.append(_parse_point(row["geometry"]))
            field_compulsory.append(row["compulsory"])
            field_altitude_restriction.append(
                _parse_altitude_restriction(row["altitude_restriction"])
            )
            field_provenance.append(row["provenance"])
    return geopandas.GeoDataFrame(
        {
            "aerodrome": field_aerodrome,
            "designator": field_designator,
            "geometry": field_geometry,
            "compulsory": field_compulsory,
            "altitude_restriction": field_altitude_restriction,
            "provenance": field_provenance,
        }
    )


def _parse_point(geometry: str) -> shapely.Point:
    return shapely.Point(dms_string_to_decimal(geometry))


def _parse_altitude_restriction(value: str) -> str:
    # FIXME: Come up with a data model to properly represent restrictions.
    return value
