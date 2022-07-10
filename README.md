# KML 2 GPX for Private Radar extractions

Converts KML files from [Private Radar](https://www.private-radar.com/)
flights list to a GPX file usable with, for example,
[ayvri](https://ayvri.com/).

## KML input

1. Export a Private Radar flight in KML format. It will contain 2 layers:
`Altitude` and `Elevation`. We will only keep `Altitude` in the GPX file.
2. Note the total **start** and end times of the flight (not the block times)
3. Run the converter:
   ```bash
   python -m kml2gpx \
       kml \
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
python -m kml2gpx.main \
    kml \
    --input LFLG-LFLW.kml \
    --start 2022-06-06T08:47:00 \
    --end 2022-06-06T10:53:00
```


## Private Radar input

This requires to know how to extract a token from your browser.

1. Get the details to connect Private Radar instance:

   * The base URL is, for example, `https://xxx.private-radar.com/`
   where `xxx` is the name of your aero club.

   * To get your authentication token:

     1. Log into your Private Radar instance
     2. Open the developer web console in your browser (F12 on Windows)
     3. Open the `Network` tab in the web console
     4. Refresh the Private Radar page
     5. In the `Network` tab, click on any line where the first column starts
     with `get` (`get`, `get_aircraft`, ...)
     6. In the `Headers` of that query, look at the `Request headers` and copy
     the value of `Authorization` field

2. Create a file named `kml2gpx.ini` with the following content:

   ```ini
   [PRIVATE_RADAR]
   url = <base URL to Private Radar>
   token = <Authorization token>
   ```

   For example:

   ```ini
   [PRIVATE_RADAR]
   url = https://xxx.private-radar.com/
   token = XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```

   The file can be stored in your home directory or in the working directory of
   the converter.

3. You can then:
   * List the last flights using:
     ```bash
     python -m kml2gpx private-radar --list --nb 50
     ```

   * Extract the GPX of a specific flight, using its ID
     ```bash
     python -m kml2gpx private-radar --flight XXXXXX
     ```

   * Extract the GPX of one of last flights, using a negative ID:
     -1 for the last flight, -2 for the flight before, ...

     ```bash
     python -m kml2gpx private-radar --flight -1
     ```

## Work in progress

* Prepare a basic UI supporting both Private Radar listings and drag & drop.
* Use an authentication process to get the authorization token automatically
