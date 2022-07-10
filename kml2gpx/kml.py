#!/usr/bin/env python3
"""
Utility module to parse KML files

:author: Thomas Calmant
:copyright: Copyright 2022, Thomas Calmant
:license: Apache License 2.0
:version: 0.0.1
..
    Copyright 2022 Thomas Calmant
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at
        http://www.apache.org/licenses/LICENSE-2.0
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

import argparse
import pathlib
from datetime import datetime
from typing import Dict, List, Optional, Union, cast

import gpxpy
import gpxpy.gpx
import lxml.etree

from . import __docformat__, __version__, __version_info__
from .beans import AbstractInputHandler, TrackPoint


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


class KmlInputHandler(AbstractInputHandler):
    """
    Handles KML file input
    """

    def __init__(self) -> None:
        self.in_files: List[pathlib.Path] = []
        self.layer: str = "Altitude"
        self.start_times: Union[List[None], List[datetime]] = []
        self.end_times: Union[List[None], List[datetime]] = []

    def get_id(self) -> str:
        """
        Returns the ID of the handler, used as sub-parser name
        """
        return "kml"

    def get_description(self) -> str:
        """
        One-line description of the handler
        """
        return "KML input handler"

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Register CLI arguments
        """
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
            "--start",
            action="extend",
            nargs="*",
            help="Start time of the files",
        )
        parser.add_argument(
            "--end", action="extend", nargs="*", help="End time of the files"
        )
        parser.add_argument(
            "--layer",
            default="Altitude",
            help="KML layer to extract (Altitude by default)",
        )

    def check_arguments(self, options: argparse.Namespace) -> None:
        """
        Checks input arguments

        :raise ValueError: Invalid argument
        """
        # Cast arguments
        self.layer = cast(str, options.layer)
        if not self.layer:
            raise ValueError("No KML layer given.")

        self.in_files = cast(List[pathlib.Path], options.input)
        raw_start_times = cast(List[str], options.start or [])
        raw_end_times = cast(List[str], options.end or [])

        # Check files
        if not self.in_files:
            raise ValueError("No input file given.")

        for file in self.in_files:
            if not file.exists():
                raise ValueError(f"File not found: {file}")

        # Check times
        if len(raw_start_times) != len(raw_end_times):
            raise ValueError(
                "There must be the same number of start and end times"
            )

        nb_files = len(self.in_files)
        if (
            len(raw_start_times) != nb_files
            and len(raw_start_times) != nb_files
        ):
            raise ValueError("There must be as many start times as input files")

        if not raw_start_times:
            # No times given
            self.start_times = [None] * nb_files
            self.end_times = [None] * nb_files
        else:
            # Parse times
            self.start_times = [
                datetime.fromisoformat(raw) for raw in raw_start_times
            ]
            self.end_times = [
                datetime.fromisoformat(raw) for raw in raw_end_times
            ]

    def get_default_output_path(self) -> Optional[pathlib.Path]:
        """
        Returns the name of the default output path, if any
        """
        return self.in_files[0].with_suffix(".gpx")

    def to_gpx(self) -> gpxpy.gpx.GPXTrack:
        """
        Converts the input to a GPX Track
        """
        gpx_track = gpxpy.gpx.GPXTrack()

        # Parse files
        for in_file, start_time, end_time in zip(
            self.in_files, self.start_times, self.end_times
        ):
            # Parse the KML file
            kml = KmlParser()
            kml.load(in_file)
            file_coords = kml.get_coordinates(self.layer)

            # Update times
            if start_time is not None and end_time is not None:
                self.set_times(file_coords, start_time, end_time)

            # Create the GPX segment
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            gpx_segment.points = [trk.to_gpx() for trk in file_coords]
            gpx_track.segments.append(gpx_segment)

        return gpx_track

    @staticmethod
    def set_times(
        coords: List[TrackPoint], start_time: datetime, end_time: datetime
    ):
        """
        Forces the update of the time field in the given track points, evenly
        spread between the start and end time
        """
        time = start_time
        time_delta = (end_time - start_time) / len(coords)
        for coord in coords:
            coord.time = time
            time += time_delta
