#!/usr/bin/env python3
"""
Converts Private-Radar KML files to GPX files usable in Ayvri
"""

import argparse
import pathlib
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Union, cast

import gpxpy
import gpxpy.gpx
import lxml.etree


@dataclass
class TrackPoint:
    longitude: float
    latitude: float
    altitude: float
    time: Optional[datetime] = None

    def to_gpx(self):
        return gpxpy.gpx.GPXTrackPoint(
            self.latitude, self.longitude, self.altitude, self.time
        )


class KmlParser:
    def __init__(self) -> None:
        self.kml: Optional[lxml.etree._Element] = None

    def load(self, in_path: pathlib.Path) -> None:
        with open(in_path, "rb") as fd:
            kml: lxml.etree._Element = lxml.etree.parse(fd, None).getroot()

            root_ns = kml.nsmap[kml.prefix]
            if root_ns != "http://www.opengis.net/kml/2.2":
                raise TypeError("Not a valid/supported KML file")

            self.kml = kml

    def get_coordinates(
        self, layer_name: str = "Altitude",
    ) -> List[TrackPoint]:
        if self.kml is None:
            raise IOError("KML data not loaded yet")

        nsmap: Dict[str, str] = self.kml.nsmap
        for placemark in self.kml.findall("Placemark", nsmap):
            placemark = cast(lxml.etree._Element, placemark)
            name = placemark.findtext("name", None, nsmap)
            if name == layer_name:
                break
        else:
            raise KeyError(layer_name)

        alt_mode = placemark.findtext("LineString/altitudeMode", None, nsmap)
        if alt_mode != "absolute":
            raise ValueError(f"Altitude mode is not absolute: {alt_mode}")

        nodes = placemark.findall("LineString/coordinates", nsmap)
        if not nodes:
            raise ValueError(f"No nodes found in layer {layer_name}")

        coords_list_raw: str = nodes[0].text
        coords: List[TrackPoint] = []
        for row in coords_list_raw.split(None):
            row = row.strip()
            if not row:
                # Empty line
                continue

            str_values = row.strip().split(",")
            if len(str_values) != 3:
                raise ValueError("Not a lon,lat,alt row: ", row)

            lon = float(str_values[0])
            lat = float(str_values[1])
            alt = float(str_values[2])
            trk_pt = TrackPoint(lon, lat, alt)
            coords.append(trk_pt)

        return coords


def set_times(
    coords: List[TrackPoint], start_time: datetime, end_time: datetime
):
    time = start_time
    time_delta = (end_time - start_time) / len(coords)
    for coord in coords:
        coord.time = time
        time += time_delta


def load_from_files(
    in_files: List[pathlib.Path],
    start_times: Union[List[None], List[datetime]],
    end_times: Union[List[None], List[datetime]],
    layer: str = "Altitude",
) -> gpxpy.gpx.GPXTrack:
    """
    Constructs a GPX track from the given files

    :param in_files: List of input files
    :param start_times: List of file start times (same size as `in_files`)
    :param end_times: List of file end times (same size as `in_files`)
    :param layer: Layer to use in the KML file
    :return: A GPX track object
    """
    if len(start_times) != len(in_files) or len(end_times) != len(in_files):
        raise ValueError("Invalid number of start/end times.")

    if not layer:
        raise ValueError("No KML layer given.")

    gpx_track = gpxpy.gpx.GPXTrack()

    # Parse files
    for in_file, start_time, end_time in zip(in_files, start_times, end_times):
        # Parse the KML file
        kml = KmlParser()
        kml.load(in_file)
        file_coords = kml.get_coordinates(layer)

        # Update times
        if start_time is not None and end_time is not None:
            set_times(file_coords, start_time, end_time)

        # Create the GPX segment
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_segment.points = [trk.to_gpx() for trk in file_coords]
        gpx_track.segments.append(gpx_segment)

    return gpx_track


def main(args: Optional[List[str]] = None) -> int:
    """
    Script entry point
    """
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=pathlib.Path,
        action="extend",
        nargs="+",
        help="Input KML file(s)",
    )
    parser.add_argument(
        "--start", action="extend", nargs="*", help="Start time of the files"
    )
    parser.add_argument(
        "--end", action="extend", nargs="*", help="End time of the files"
    )
    parser.add_argument(
        "--layer",
        default="Altitude",
        help="KML layer to extract (Altitude by default)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        type=pathlib.Path,
        help="Path to the output GPX",
    )
    options = parser.parse_args(args)

    # Cast arguments
    in_files = cast(List[pathlib.Path], options.input)
    output = cast(Optional[pathlib.Path], options.output)
    layer = cast(str, options.layer)
    raw_start_times = cast(List[str], options.start or [])
    raw_end_times = cast(List[str], options.end or [])

    # Check'em
    if not in_files:
        print("No input file given.", file=sys.stderr)
        return 1

    for file in in_files:
        if not file.exists():
            print("File not found:", file, file=sys.stderr)
            return 1

    if len(raw_start_times) != len(raw_end_times):
        print(
            "There must be the same number of start and end times",
            file=sys.stderr,
        )
        return 1

    if len(raw_start_times) != 0 and len(in_files) != len(raw_start_times):
        print("There must be as many start times as input files")
        return 1

    if not raw_start_times:
        # No times given
        start_times = [None] * len(in_files)
        end_times = [None] * len(in_files)
    else:
        # Parse times
        start_times = [datetime.fromisoformat(raw) for raw in raw_start_times]
        end_times = [datetime.fromisoformat(raw) for raw in raw_end_times]

    if output is None:
        output = in_files[0].with_suffix(".gpx")

    # Parse the files
    gpx_track = load_from_files(in_files, start_times, end_times, layer)

    # Prepare the root GPX structure
    gpx = gpxpy.gpx.GPX()
    gpx.tracks.append(gpx_track)

    # Write the GPX file
    with open(output, "w", encoding="utf-8") as gpx_fd:
        gpx_fd.write(gpx.to_xml())

    return 0


if __name__ == "__main__":
    sys.exit(main())
