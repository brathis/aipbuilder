import geopandas
import shapely


class ExampleBorderProvider:
    def __init__(self, path: str) -> None:
        self._gdf = geopandas.GeoDataFrame.from_file(path)
        pass

    def get_border(self, border_name: str) -> shapely.LineString:
        df = self._gdf.loc[self._gdf.name == border_name]
        if not len(df):
            raise KeyError(border_name)
        geom = df.iloc[0].geometry
        if isinstance(geom, shapely.MultiLineString):
            return geom.geoms[0]
        assert isinstance(geom, shapely.LineString)
        return geom


border_provider = ExampleBorderProvider("./example-data/borders/example_borders.gpkg")
