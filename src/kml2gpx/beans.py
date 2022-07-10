#!/usr/bin/env python3
"""
Definition of beans used across the project

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
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import gpxpy.gpx

from . import __docformat__, __version__, __version_info__

__all__ = ["TrackPoint", "AbstractInputHandler"]


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


class AbstractInputHandler:
    """
    Abstract class of input handlers
    """

    def get_id(self) -> str:
        """
        Returns the ID of the handler, used as sub-parser name
        """
        raise NotImplementedError

    def get_description(self) -> str:
        """
        One-line description of the handler
        """
        return ""

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Register CLI arguments
        """

    def check_arguments(self, options: argparse.Namespace) -> Optional[int]:
        """
        Checks input arguments

        :return: None if all good, an exit code if an argument was handled
        :raise ValueError: Invalid argument
        """

    def get_default_output_path(self) -> Optional[pathlib.Path]:
        """
        Returns the name of the default output path, if any
        """
        return None

    def to_gpx(self) -> gpxpy.gpx.GPXTrack:
        """
        Converts the input to a GPX Track
        """
        raise NotImplementedError
