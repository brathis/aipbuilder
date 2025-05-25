# AIP Builder

A tool for building geospatial datasets from textual aeronautical information publications (AIPs).

## Why?

I have been wanting to build my own EFB/flight planning app for Switzerland for a while. However, obtaining the official aeronautical information
for Switzerland (i.e. airspaces, VFR reporting points, navaids, frequencies, etc.) in a machine-readable format has turned out to be nearly impossible.
So, out of frustration, I decided to build my own dataset, which is where this tool comes into play.

## Usage

Often, airspace boundaries are defined with respect to territorial boundaries of countries. For now, I have decided not to draw my own boundaries,
but instead use datasets from swisstopo and the European Union. As this data is copyrighted, you need to download your own copy in order to run
the tool locally:

- [swissBOUNDARIES3D](https://www.swisstopo.admin.ch/de/landschaftsmodell-swissboundaries3d)
- [EU Administrative Units Dataset](https://ec.europa.eu/eurostat/web/gisco/geodata/administrative-units/countries)

`aipbuilder.ipynb` is the main entrypoint into the tool. It invokes the different modules of the tool and presents an interactive visualization
of the generated dataset.

## TODO

- Figure out a way to georeference all VACs from VFR Manual. Possibly by auto-generating ".points" files which can then be imported into QGIS?
  Or even better, by generating GeoTIFF? Either way, it shouldn't be too hard, as all VACs are in 1:100'000 and show a square area of 12 km by 12 km.
  Since they are also north-oriented, all we need is a single pixel coordinate per chart.
  Use this to add approach sectors for uncontrolled fields.
- Add CTA and FIR boundaries. Even though they are supposed to follow the Swiss border for the most part, sometimes they do not.
  If we're lucky, we can get some info on this from BAZL.
- Add VFR reporting points for controlled fields.
- Add airports.
- Add navaids.
- Add VFR routes.
- Add restricted glider areas.
- Add upper and lower limits, frequencies, and other metadata to airspaces.
- Export functionality.

## License & Copyright Information

- Swiss border: © swisstopo
- German border: © EuroGeographics for the administrative boundaries
