# KML 2 GPX for Private Radar extractions

Converts KML files from Private Radar flights list to a GPX file usable with
[ayvri](https://ayvri.com/).

## Usage

1. Export a Private Radar flight in KML format. It will contain 2 layers:
`Altitude` and `Elevation`. We will only keep `Altitude` in the GPX file.
2. Note the total **start** and end times of the flight (not the block times)
3. Run the converter:
   ```bash
   python -m kml2gpx \
       --input ${INPUT_KML_FILE} \
       --output ${OUTPUT_GPX_FILE} \
       --start ${FLIGHT_START_DATETIME} \
       --end ${FLIGHT_END_DATETIME}
   ```

   * If multiple input files are given, there must be as many start and end
   times. The results will be stored in a single file.
   * If output is not given, it will be the (first) input file name with the
   `.gpx` extension.
   * Start and end date times must be in ISO format, for example:
   `2022-06-06T10:53:00+02:00`
   * As the time at each point is missing from the exported KML file, we
   consider all points being equally spread between the start and end time.
   (*I know it's not the case*)

For example:

```bash
python -m kml2gpx.main
    --input LFLG-LFLW.kml \
    --start 2022-06-06T08:47:00 \
    --end 2022-06-06T10:53:00
```

## Work in progress

* Try to connect Private Radar directly to be able to select a flight and
automatically get its details and extract its KML. This would also allow to
have the exact time of each point in the KML file instead of computing it.
* Prepare a basic UI supporting both Private Radar listings and drag & drop.
