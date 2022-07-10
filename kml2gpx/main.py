#!/usr/bin/env python3
"""
Converts Private-Radar KML files to GPX files usable in Ayvri

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
import logging
import pathlib
import sys
from typing import List, Optional, cast

import gpxpy
import gpxpy.gpx

from . import __docformat__, __version__, __version_info__
from .beans import AbstractInputHandler
from .kml import KmlInputHandler
from .private_radar import PrivateRadarHandler


def main(args: Optional[List[str]] = None) -> int:
    """
    Script entry point
    """
    # Known handlers
    input_handlers: List[AbstractInputHandler] = [
        KmlInputHandler(),
        PrivateRadarHandler(),
    ]

    # Setup the arguments parser
    parser = argparse.ArgumentParser("kml2gpx")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Set logger to DEBUG level"
    )
    parser.add_argument(
        "-o", "--output", type=pathlib.Path, help="Output GPX file"
    )

    subparsers = parser.add_subparsers(
        description="Input-based arguments", required=True
    )
    for handler in input_handlers:
        sub_parser = subparsers.add_parser(
            handler.get_id(), description=handler.get_description()
        )
        sub_parser.set_defaults(handler=handler)
        handler.register_arguments(sub_parser)

    # Parse arguments
    options = parser.parse_args(args)

    logging.basicConfig(
        level=logging.DEBUG if options.verbose else logging.ERROR
    )

    # Get the handler
    handler: AbstractInputHandler = options.handler
    try:
        rc = handler.check_arguments(options)
        if rc is not None:
            return rc
    except (ValueError, TypeError) as ex:
        print(ex, file=sys.stderr)
        return 1

    # Compute output file
    output = cast(Optional[pathlib.Path], options.output)
    if output is None:
        output = handler.get_default_output_path()

    if output is None:
        output = pathlib.Path("output.gpx")

    # Prepare the root GPX structure
    gpx = gpxpy.gpx.GPX()
    gpx.tracks.append(handler.to_gpx())

    # Write the GPX file
    with open(output, "w", encoding="utf-8") as gpx_fd:
        gpx_fd.write(gpx.to_xml())

    print(output, "written successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
