# airspace_renderer

A Python library for turning textual description of airspace geometries into machine-readable geospatial data.

## What this library does

It allows you to turn textual description of aeronautical data into machine-readable geo data.
This is not always straightforward, as the textual descriptions are not always just a list of polygon vertices. For example, the following is an excerpt from an airspace definition found
in the Swiss AIP referencing a geographical border:

    47 14 34 N 006 57 19 E - National border with France, Germany to - 47 34 03 N 007 41 13 E - 47 53 00 N 008 51 00 E

In the same publication, one also encounters airspace definitions consisting of circular geometries, such as arcs

    45 55 41 N 005 54 39 E - Arc of circle centred on 46 03 03 N 005 47 12 E, Radius 9.017 NM, clockwise 46 10 24 N 005 39 42 E - 46 10 59 N 005 40 52 E

or circles

    Circle of 10 km (5.4 NM) radius: Centre 46 45 33 N / 009 05 17 E

airspace_renderer defines a format which allows you to express these geometries and then turns
these expressions into a `shapely.Polygon`.

## Why?

I have been wanting to build my own EFB/flight planning app for Switzerland for a while. However, obtaining the official aeronautical information
for Switzerland (i.e. airspaces, VFR reporting points, navaids, frequencies, etc.) in a machine-readable format has turned out to be nearly impossible.
So, out of frustration, I decided to build my own dataset, which is where this tool comes into play.

## Getting started

This library uses [uv](https://docs.astral.sh/uv/) for packaging and dependency management.

An example dataset is provided. Check out [example.ipynb](./example.ipynb)
for a working example of how to use the library.

## Dependencies

The library has two dependencies: [shapely](https://shapely.readthedocs.io/en/stable/) for working with geometries
and [pyproj](https://pyproj4.github.io/pyproj/stable/) for performing geodetic calculations.

Additional dependencies are required for running the example. They are automatically installed when using uv.

## Documentation

### Airspace Geometry Types

An airspace is a `shapely.Polygon`. It is defined by a string consisting of several components, separated by `-`.
Each component can be one of several input geometry types, of which vertices are the simplest.

Check out the following example files:

- [airspaces.csv](./example-data/airspaces.csv)
- [danger_areas.csv](./example-data/danger_areas.csv)
- [fir.csv](./example-data/fir.csv)
- [restricted_areas.csv](./example-data/restricted_areas.csv)

#### Vertices

A vertex is defined as a WGS-84 coordinate in DMS format and lat/lon order. The following syntaxes are supported:

- `47 08 00 N 007 23 01 E`
- `46 51 23 N / 007 29 47 E`

Note that the longitude degrees require zero-padding to three digits.

#### Arcs

An arc is defined by a center point (in vertex format), a radius in nautical miles and a direction, either clockwise or counter-clockwise.
For example:

- `ARC(47 03 32 N 007 19 41 E, 5.02, cw)`: An arc of radius 5.02 nautical miles, centered around the vertex `47 03 32 N 007 19 41 E` in clockwise direction.
- `ARC(47 47 30 N / 009 14 00 E, 5.02, ccw)`: An arc of radius 5.02 nautical miles, centered around the vertex `47 47 30 N 009 14 00 E` in counter-clockwise direction.

**The geometry immediately before and after an arc component must be a vertex**.

#### Circles

A circle is defined by a center point (in vertex format) and a radius in nautical miles. For example:

- `CIRCLE(46 45 33 N / 009 05 17 E, 5.4)`: A circle of radius 5.4 nautical miles, centered around the vertex `46 45 33 N / 009 05 17 E`.

As it is a closed geometry, it does not connect to any other components, and it only makes sense to use it alone.

#### Border References

Arguably the most complex and frustrating topic of airspace definitions. The geometry immediately before and after a border component
must be a vertex. These vertices are the border entry points and they are used to determine, which segment of border is to be included
in the rendered geometry. Using border geometries requires passing a _border provider_ to the `parse_polygon` method.
A border provider is an object containing a method `get_border()` which accepts a single string argument containing the border name
and returns a `shapely.LineString` which defines the border.

By convention, a border is considered to be a closed contour. The first and last vertex of the line string are implicitly connected.
For any pair of entry points, there are two possible border segments between them. By default, the segment which results from starting
at the vertex before the border segment and traversing along the border in increasing vertex order until the vertex after the border
component is returned. The inverse of this selection which is the result of traversing the border in reverse order can be obtained
by specifying the optional `I` (for _inverse_) parameter to the border geometry. For example:

- `46 27 18 N 006 37 35 E - BORDER(CH) - 46 26 45 N 006 43 33 E`: A segment of vertices starting at `46 27 18 N 006 37 35 E` and following the border named `CH` in forward order until the point `46 26 45 N 006 43 33 E`.
- `47 39 24 N 009 14 00 E - BORDER(CH, I) - 47 34 03 N 007 41 13 E`: A segment of vertices starting at the point `47 39 24 N 009 14 00 E` and following the border named `CH` in _reverse_ order until the point `47 34 03 N 007 41 13 E`.

Note that the border must contain both border entry points (with an accuracy of 30m on the WGS-84 ellipsoid).
