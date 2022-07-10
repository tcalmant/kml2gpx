#!/usr/bin/env python3
"""
Utility module to access Private Radar flights information

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
import configparser
import logging
import pathlib
from configparser import SafeConfigParser
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, cast
from urllib.parse import urljoin

import gpxpy.gpx
import requests

from . import __docformat__, __version__, __version_info__
from .beans import AbstractInputHandler, TrackPoint


@dataclass
class PRFlight:
    """
    Description of a Private Radar flight
    """

    id: int
    """ Private Radar ID of the flight """

    registration: str
    """ Airplane registration number """

    from_icao: str
    """ ICAO code of the departure airport """

    to_icao: str
    """ ICAO code of the arrival airport """

    flight_type: str
    """ Kind of flight: solo, solo_sup, instr, ... """

    start: datetime
    """ Engine start time """

    end: datetime
    """ Engine shut down time """

    crew: List[str]
    """ List of names of crew members """

    starred: bool = False
    """ Starred flight """

    @classmethod
    def parse(cls, data: Dict[str, Any]) -> "PRFlight":
        """
        Constructs a Private Radar flight from its JSON description
        """
        # Parse dates
        start = datetime.fromisoformat(data["dt_start"])
        end = datetime.fromisoformat(data["dt_terminated"])

        # Parse the crew
        crew = [
            f"{member['firstname']} {member['lastname']}"
            for member in data["crew"]
        ]

        # Get the rest of details as is
        return cls(
            data["id"],
            data["registration"],
            data["from"],
            data["to"],
            data["flight_type"],
            start,
            end,
            crew,
            data["starred"],
        )


class PrivateRadar:
    """
    API to get Private Radar data
    """

    def __init__(self, base_url: str, auth: str) -> None:
        """
        :param base_url: Private Radar base URL
        :param auth: Private Radar authentication token
        """
        self.base_url = base_url
        self.auth = auth
        self.logger = logging.getLogger(__name__)

    def list_flights(
        self, nb_flights: int = 100, flight_id: Optional[int] = None
    ) -> List[PRFlight]:
        """
        Lists flights from Private Radar

        :param nb_flights: Maximum number of flights to return
        :param flight_id: Return details for that specific flight
        """
        filter_flight_id: str = ""
        filter_type: int = 1

        if flight_id is not None:
            # Select a specific flight
            filter_flight_id = str(flight_id)
            filter_type = 5

        # Get last flights
        params = {
            "filter6": {
                "type": filter_type,
                "page": 1,
                "unit": 0,
                "nbFlights": nb_flights,
                "flightTypes": "solo,solo_sup,solo_only,instr,mcc,exam,tourist,discovery,check,ferry,trip,rental,tow,aoc",
                "aircraft": 0,
                "crew": 0,
                "showRoute": True,
                "showTotalTime": True,
                "showBlockTime": True,
                "showAirtime": True,
                "showCrew": True,
                "showMap": True,
                "hideTaxi": True,
                "flightIds": filter_flight_id,
                "nbUnits": nb_flights,
                "date": 0,
                "dateFrom": 0,
                "dateTo": 0,
            }
        }

        # Query the list
        response = requests.post(
            urljoin(self.base_url, "/prwsw/flight/getFlightsFilter6"),
            headers={
                "Authorization": self.auth,
                "Accept": "application/json, text/plain, */*",
            },
            json=params,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as ex:
            self.logger.error("Error getting the list of flights: %s", ex)
            raise ex

        # Parse flights
        result = cast(Dict[str, Any], response.json())

        if result["status"] != "success":
            error = result.get("error", "n/a")
            self.logger.error(f"Error retrieving flights: {error}")
            raise IOError(f"Error retrieving flights: {error}")

        with open("out.json", "w") as fd:
            fd.write(response.text)
        flights_json: List[Dict[str, Any]] = response.json()["flight_list"]
        return [PRFlight.parse(flight) for flight in flights_json]

    def get_flight(self, flight_id: int) -> PRFlight:
        """
        Returns the description of the given flight

        :param flight_id: Private Radar flight ID
        :return: The description of the flight
        """
        if flight_id >= 0:
            return self.list_flights(100, flight_id=flight_id)[0]
        else:
            nb_flights = abs(flight_id)
            return self.list_flights(nb_flights)[abs(flight_id) - 1]

    def flight_path(self, flight: Union[int, PRFlight]) -> List[TrackPoint]:
        """
        Retrieves the path of the given Private Radar path
        """
        if isinstance(flight, PRFlight):
            flight_id = flight.id
        elif isinstance(flight, int):
            flight_id = flight
        else:
            raise TypeError(f"Invalid flight ID: {type(flight).__name__}")

        # Get the flight
        response = requests.post(
            urljoin(self.base_url, "/prwsw/flight/get_path"),
            headers={
                "Authorization": self.auth,
                "Accept": "application/json, text/plain, */*",
            },
            json={"id": flight_id},
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as ex:
            self.logger.error(
                "Error getting path for flight %d: %s", flight_id, ex
            )
            raise ex

        # Check its content
        flight_details: Dict[str, Any] = response.json()
        if flight_details.get("status") != "success":
            self.logger.error("Error getting flight %d", flight_id)
            self.logger.debug("Flight details:\n%s", flight_details)
            raise ValueError("Server-side error getting the flight")

        # Parse the flight track
        path: List[Dict[str, Any]] = flight_details["flight_profile"]
        return [
            TrackPoint(
                node["lon"],
                node["lat"],
                node["alt_m"],
                # Convert Private Radar timestamps
                datetime.fromtimestamp(node["time"] * 10 ** -3),
            )
            for node in path
        ]


class PrivateRadarHandler(AbstractInputHandler):
    """
    Handles flights from PrivateRadar
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.api: Optional[PrivateRadar] = None
        self.flight: Optional[PRFlight] = None

    def get_id(self) -> str:
        """
        Returns the ID of the handler, used as sub-parser name
        """
        return "private-radar"

    def get_description(self) -> str:
        """
        One-line description of the handler
        """
        return "Load flights from Private Radar"

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Register CLI arguments
        """
        group = parser.add_argument_group("Configuration")
        group.add_argument(
            "-c",
            "--conf",
            type=pathlib.Path,
            help="Path to the configuration file",
        )
        group.add_argument("--url", help="Base URL of Private Radar")
        group.add_argument("--auth", help="Authentication token")

        group = parser.add_argument_group("Flights list")
        group.add_argument(
            "-l",
            "--list",
            action="store_true",
            help="List available flights and exit.",
        )
        group.add_argument(
            "-n",
            "--nb",
            default=50,
            type=int,
            help="Number of available flights to list",
        )

        parser.add_argument(
            "-f",
            "--flight",
            type=int,
            help="ID of the flight to extract (or -1 for last flight, ...)",
        )

    def _find_conf(self) -> Optional[pathlib.Path]:
        """
        Tries to find a path for the configuration file in well-known folders
        """
        for folder in (
            pathlib.Path("."),
            pathlib.Path("~"),
            pathlib.Path("~/.conf"),
        ):
            folder = folder.expanduser()
            for name in ("kml2gpx.ini", "private_radar.ini"):
                conf_path = folder / name
                if conf_path.exists():
                    return conf_path

        return None

    def check_arguments(self, options: argparse.Namespace) -> Optional[int]:
        """
        Checks input arguments

        :raise ValueError: Invalid argument
        """
        url: Optional[str] = None
        token: Optional[str] = None

        # Try to load the configuration from a file
        conf_path = cast(Optional[pathlib.Path], options.conf)
        if conf_path is None:
            conf_path = self._find_conf()

        if conf_path is not None:
            if not conf_path.exists():
                raise ValueError(f"Configuration file not found: {conf_path}")

            conf_path = conf_path.absolute()
            config = SafeConfigParser()
            with open(conf_path, "r") as fd:
                self.logger.debug("Reading configuration file: %s", conf_path)
                config.read_file(fd)

            try:
                url = config.get("PRIVATE_RADAR", "url")
                token = config.get("PRIVATE_RADAR", "token")
            except configparser.NoSectionError as ex:
                raise ValueError(f"Invalid configuration file: {ex}")

        # Override with arguments, if any
        if options.url:
            url = cast(Optional[str], options.url)

        if options.auth:
            token = cast(Optional[str], options.auth)

        if not url:
            raise ValueError("Missing Private Radar URL configuration")

        if not token:
            raise ValueError(
                "Missing Private Radar authentication configuration"
            )

        # Prepare the API
        self.logger.debug("Using Private Radar URL: %s", url)
        self.api = PrivateRadar(url, token)

        if options.list:
            # List flights and exit
            return self.print_flights(options.nb)
        else:
            flight_id = cast(Optional[int], options.flight)
            if flight_id is None:
                raise ValueError("A flight ID is required")

            # Load the flight
            self.flight = self.api.get_flight(flight_id)
            print("Loaded flight:")
            self.print_flight(self.flight)

    def get_default_output_path(self) -> Optional[pathlib.Path]:
        """
        Returns a default name for the output GPX file
        """
        if self.flight is None:
            return None

        return pathlib.Path(
            f"{self.flight.start.strftime('%Y-%m-%d')}-"
            f"{self.flight.from_icao}-"
            f"{self.flight.to_icao}.gpx"
        )

    def to_gpx(self) -> gpxpy.gpx.GPXTrack:
        """
        Converts the input to a GPX Track
        """
        if self.api is None:
            raise ValueError("Private Radar API not set up")

        if self.flight is None:
            raise ValueError("Flight not loaded.")

        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_segment.points = [
            point.to_gpx() for point in self.api.flight_path(self.flight)
        ]

        gpx_track = gpxpy.gpx.GPXTrack()
        gpx_track.segments.append(gpx_segment)
        return gpx_track

    def print_flights(self, nb_flights: int) -> int:
        """
        Prints out flights visible in Private Radar

        :param nb_flights: Number of flights to show
        :return: 0 on success, 1 on error
        """
        if self.api is None:
            self.logger.error("Private Radar API not set up")
            return 1

        for flight in self.api.list_flights(nb_flights):
            self.print_flight(flight)

        return 0

    @staticmethod
    def print_flight(flight):
        start = flight.start.isoformat(" ") if flight.start else "n/a"
        end = flight.end.isoformat(" ") if flight.end else "n/a"

        sep = "---" if not flight.starred else "==="
        star = " (*)" if flight.starred else ""

        print(f"{sep} Flight #{flight.id}{star} {sep}")
        print("* From.:", flight.from_icao)
        print("* To...:", flight.to_icao)
        print("* Crew.:", ", ".join(flight.crew))
        print("* Type.:", flight.flight_type)
        print("* Start:", start)
        print("* End..:", end)
        print()
