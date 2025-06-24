# Circulo de Conductores Red Fleet Gas Stations MyMaps Updater

This project provides a solution to generate and update a Google My Maps map representing the gas stations of the Red Fleet from the Circulo de Conductores association. The map displays the latest fuel prices for each station, using open data from the Spanish Government's Ministry for Digital Transformation and Public Function: [Open Data Catalog - Fuel Prices](https://datos.gob.es/es/catalogo/e05068001-precio-de-carburantes-en-las-gasolineras-espanolas).

## Features
- Downloads and processes the latest fuel prices for all Spanish gas stations.
- Filters and highlights the Red Fleet stations from Circulo de Conductores.
- Generates KML, CSV, and GPX files with updated information for use in Google My Maps and other platforms.
- Updates a Google My Maps map with the latest data, including station details and prices.

## Why Playwright?
Google does not provide a public API for programmatically updating My Maps. This project uses [Playwright](https://playwright.dev/python/) to automate browser interactions and perform the necessary updates. Playwright is used to:
- Log in to Google accounts securely.
- Upload and replace map layers in My Maps.
- Simulate user actions that cannot be performed via API.

This approach is currently the only reliable way to automate updates to Google My Maps.

### Using Playwright Codegen

The use of Playwright's [codegen](https://playwright.dev/python/docs/codegen) tool, which records browser actions and generates Python code for automation,  greatly simplifies scripting complex interactions with Google My Maps.

For example, you can launch codegen for your map with:
```sh
playwright codegen https://www.google.com/maps/d/edit?mid=1AQbfmHl05PCE0mPfnUkGLy2VqFBR_ts
```
This will open a browser window where your actions are recorded and translated into Playwright Python code, which you can then adapt for your automation scripts.

## How to operate
To avoid potential issues or risks, it is recommended to use an alternative Google account (not your main or official account). Google may temporarily block accounts due to unusual or automated activity.

1. First, create a new map in your Google account, give it any name, and import the generated KML file. Currently, the script only supports updating a single map layer.
2. Share the map in "Edit" mode with an alternative Google account that you will use for automation and updates. Enter the credentials for this alternative account in your configuration.
3. The automation process will first authenticate with Google, then access the shared map to perform updates. 

This approach helps generalize the workflow and reduces the risk to your main account.

<!-- ## Requirements
- Python 3.8+
- Playwright (Python)
- pandas, requests, geopy, python-dotenv -->

## Usage
1. Clone the repository and install dependencies:
   ```sh
   pip install -r requirements.txt
   playwright install chromium
   ```
2. Configure your `.env` file with the required credentials and file paths.

| Variable Name                        | Description                                                                                                   | Example Value                                                                                   |
|---------------------------------------|---------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| `USERNAME`                           | Google account email used to log in and update My Maps.                                                       | `your.email@gmail.com`                                                                          |
| `PASSWORD`                           | Password for the Google account.                                                                              | `your_password`                                                                                 |
| `MAP_URL`                            | URL of the Google My Maps map to be updated.                                                                  | `https://www.google.com/maps/d/edit?mid=<YOUR_MAP_ID_HERE>`                                    |
| `STATIONS_PRICE_FILE`                | Path to the generated KML file containing updated gas station prices.                                         | `gasolineras_red_fleet_precio.kml`                                       |
| `LOG_MYMAPS_FILE`                    | Path to the log file for My Maps update operations.                                                           | `mymaps.log`                                                                                    |
| `USER_SESSION_DATA_DIR`              | Directory to store Playwright browser session data for Google login.                                          | `google_session`                                                                                |
| `CIRCULO_CONDUCTORES_CSV_FILE`       | Path to the CSV file listing Red Fleet stations from Circulo de Conductores.                                  | `gasolineras_circulo_conductores.csv`                                                          |
| `CIRCULO_CONDUCTORES_SHEET_URL`      | URL of the Google Sheet with the Circulo de Conductores Red Fleet station list.                               | `https://docs.google.com/spreadsheets/d/1N1GeJAJjegM58kpIU-R6JtXkOXI5mM7t/edit?gid=834431412`  |
| `MINISTRY_PRICE_URL`                 | API endpoint for downloading the latest official fuel prices from the Spanish Government.                     | `https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/` |
| `LOG_STATIONS_FILE`                  | Path to the log file for gas station price processing operations.                                              | `stations_price.log`                                                                            |

3. Run the script to generate the updated files:
   ```sh
   python retrieve_stations.py
   ```

4. To update only the Google My Maps map (assuming you already have the KML file), run the following script using Playwright automation:
   ```sh
   python update_mymaps.py
   ```


## Data Sources
<!-- Ministerio para la Transformación Digital y de la Función Pública -->
<!-- Precio de carburantes en las gasolineras españolas  -->
- [Open Data Catalog - Fuel Prices](https://datos.gob.es/es/catalogo/e05068001-precio-de-carburantes-en-las-gasolineras-espanolas)
- [Circulo de Conductores Red Fleet station list](https://docs.google.com/spreadsheets/d/1N1GeJAJjegM58kpIU-R6JtXkOXI5mM7t/edit?gid=834431412)

## Disclaimer
This project is not affiliated with Google or the Spanish Government. It is provided as a community solution for automating My Maps updates where no official API exists.
