import pyproj

__all__ = [
    "CRS_WGS84",
    "CRS_LV95",
    "P_LV95",
]

# https://epsg.io/4326
CRS_WGS84 = pyproj.CRS.from_authority("epsg", "4326")

# https://epsg.io/2056
CRS_LV95 = pyproj.CRS.from_authority("epsg", "2056")
P_LV95 = pyproj.Proj(CRS_LV95)
