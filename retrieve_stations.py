import logging
from logging.handlers import RotatingFileHandler
import pandas as pd
import requests
import json
from geopy.distance import geodesic
import unicodedata
from xml.sax.saxutils import escape
import os
from datetime import datetime
import argparse
from dotenv import load_dotenv

DEFAULT_LOG_FILE="stations.log"

DEFAULT_STATIONS_PRICE_FILE="gasolineras_red_fleet_precio.kml"

DEFAULT_CIRCULO_CONDUCTORES_CSV_FILENAME = "gasolineras_circulo_conductores.csv"
DEFAULT_CIRCULO_CONDUCTORES_SHEET_URL = "https://docs.google.com/spreadsheets/d/1N1GeJAJjegM58kpIU-R6JtXkOXI5mM7t/edit?gid=834431412"

DEFAULT_MINISTRY_PRICE_URL= "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"

def get_circulo_conductores_dataframe(cc_csv_filename, sheet_url):
    if not os.path.exists(cc_csv_filename):

        # Convert to CSV export URL
        csv_url = sheet_url.replace("/edit?gid=", "/export?format=csv&gid=")

        # Read the content as DataFrame
        df_cc = pd.read_csv(csv_url)

        # Set row 3 as column names
        df_cc.columns = df_cc.iloc[3]

        # Drop rows 0 to 3
        df_cc = df_cc.drop(index=[0, 1, 2, 3])
        # Drop column 13
        df_cc = df_cc.drop(columns=df_cc.columns[13])

        # Reset index if desired
        df_cc = df_cc.reset_index(drop=True)

        # Replace commas with dots in numeric columns (such as coordinates)
        columns_to_convert = [col for col in df_cc.columns if "Coordenada" in col]
        for col in columns_to_convert:
            df_cc[col] = df_cc[col].str.replace(",", ".", regex=False)
            df_cc[col] = pd.to_numeric(df_cc[col], errors="coerce")

        # Save the DataFrame to a CSV file
        df_cc.to_csv(cc_csv_filename, index=False)
    else:
        df_cc = pd.read_csv(cc_csv_filename)
    return df_cc


# Coger los datos del Ministerio
PRICE_URL = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
def get_ministry_dataframe(price_url):

    headers = {
        "Accept": "application/json"
    }

    response = requests.get(price_url, headers=headers)
    if response.status_code != 200:
        logging.error(f"Error fetching data from Ministerio. Status code: {response.status_code}")
        exit(1)

    data = response.json()
    stations = data["ListaEESSPrecio"]
    df_min = pd.DataFrame(stations)

    columnas_a_convertir = [col for col in df_min.columns if "Precio" in col or "Latitud" in col or "Longitud" in col]
    for col in columnas_a_convertir:
        df_min[col] = df_min[col].str.replace(",", ".", regex=False)
        df_min[col] = pd.to_numeric(df_min[col], errors="coerce")
    return df_min

def normalize_dfs(df_cc, df_min):
    # Change the column names "Municipio" and "Provincia" to uppercase in df_estaciones
    df_cc.rename(columns={"Municipio": "MUNICIPIO", "Provincia": "PROVINCIA"}, inplace=True)
    df_min.rename(columns={"Municipio": "MUNICIPIO", "Provincia": "PROVINCIA"}, inplace=True)

    # Convert MUNICIPIO and PROVINCIA to uppercase
    df_cc["MUNICIPIO"] = df_cc["MUNICIPIO"].str.upper()
    df_cc["PROVINCIA"] = df_cc["PROVINCIA"].str.upper()
    df_min["MUNICIPIO"] = df_min["MUNICIPIO"].str.upper()
    df_min["PROVINCIA"] = df_min["PROVINCIA"].str.upper()

    # Normalize province names
    province_name_replacement = {
        "ARABA/ÁLAVA": "ALAVA",
        "BALEARS (ILLES)": "BALEARES",
        "BIZKAIA": "VIZCAYA",
        "CASTELLÓN / CASTELLÓ": "CASTELLON",
        "CORUÑA (A)": "LA CORUÑA",
        "GIPUZKOA": "GUIPUZCOA",
        "GIRONA": "GERONA",
        "LLEIDA": "LERIDA",
        "OURENSE": "ORENSE",
        "PALMAS (LAS)": "LAS PALMAS",
        "RIOJA (LA)": "LA RIOJA",
        "SANTA CRUDA DE TENERIFE": "TENERIFE",
        "VALENCIA / VALÈNCIA": "VALENCIA"
    }

    df_min["PROVINCIA"] = df_min["PROVINCIA"].replace(province_name_replacement)

    def remove_accents(text):
        if isinstance(text, str):
            return ''.join(
                c for c in unicodedata.normalize('NFD', text)
                if unicodedata.category(c) != 'Mn'
            )
        return text

    df_cc["MUNICIPIO"] = df_cc["MUNICIPIO"].apply(remove_accents)
    df_cc["PROVINCIA"] = df_cc["PROVINCIA"].apply(remove_accents)
    df_min["MUNICIPIO"] = df_min["MUNICIPIO"].apply(remove_accents)
    df_min["PROVINCIA"] = df_min["PROVINCIA"].apply(remove_accents)

    return df_cc, df_min

def price_nearest_station(row, stations_grouped):
    municipio = row["MUNICIPIO"]
    provincia = row["PROVINCIA"]
    coord_origen = (row["Coordenada Y"], row["Coordenada X"])

    # Filter by group
    if (provincia) not in stations_grouped.groups:
        return None, None

    stations_filtered = stations_grouped.get_group((provincia))

    # Calculate distances
    stations_filtered["distancia"] = stations_filtered.apply(
        lambda x: geodesic(coord_origen, (x["Latitud"], x["Longitud (WGS84)"])).kilometers, axis=1
    )

    # Get the price of the nearest station
    nearest_station = stations_filtered.loc[stations_filtered["distancia"].idxmin()]

    # Remove the used station
    # global stations_grouped
    # stations_grouped = stations_grouped.drop(nearest_station.name)

    return nearest_station["Precio Gasolina 95 E5"], nearest_station["Precio Gasoleo A"]

def create_kml(df, filename="stations.kml"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    kml_header = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <name>Gasolineras</name>
'''
    kml_footer = '''</Document>
</kml>
'''

    placemarks = []
    for _, row in df.iterrows():
        try:
            lon = float(row["Coordenada X"])
            lat = float(row["Coordenada Y"])
        except (ValueError, TypeError):
            continue  # Saltar si no hay coordenadas válidas

        gasolina_95 = row.get("Precio Gasolina 95 E5", "")
        gasoleo_a = row.get("Precio Gasoleo A", "")
        provincia = escape(str(row.get("PROVINCIA", "")))
        municipio = escape(str(row.get("MUNICIPIO", "")))
        centro = escape(str(row.get("CENTRO", "")))
        direccion = escape(str(row.get("DIRECCIÓN", "")))
        concesion = escape(str(row.get("CONCESIÓN", ""))) 

#         description = f""" Gasolina 95: {gasolina_95}<br/>
# Gasóleo A: {gasoleo_a}<br/>
# Provincia: {provincia}<br/>
# Municipio: {municipio}<br/>
# Centro: {centro}<br/>
# Dirección: {direccion}<br/>
# Fecha: {now}"""
        # Use a detailed description instead of leaving it empty, as an empty description is not desirable
        description = f"""Concesión {concesion}"""

# TODO: Add a styleUrl if needed
# <styleUrl>#miEstilo</styleUrl> <!-- Opcional -->

        placemark = f"""
    <Placemark>
        <name>{centro}</name>
        <description><![CDATA[{description}]]></description>
        <ExtendedData>
            <Data name="Gasolina 95 E5">
                <value>{gasolina_95} €</value>
            </Data>
            <Data name="Gasóleo A">
                <value>{gasoleo_a} €</value>
            </Data>
            <Data name="Dirección">
                <value>{direccion}</value>
            </Data>
            <Data name="Municipio">
                <value>{municipio}</value>
            </Data>
            <Data name="Provincia">
                <value>{provincia}</value>
            </Data>
            <Data name="Fecha">
                <value>{now}</value>
            </Data>
        </ExtendedData>
        <Point>
            <coordinates>{lon},{lat},0</coordinates>
        </Point>
    </Placemark>
"""
        placemarks.append(placemark)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(kml_header)
        for pm in placemarks:
            f.write(pm)
        f.write(kml_footer)
  


def create_gpx(df, filename="stations.gpx"):
    gpx_header = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Gasolineras" xmlns="http://www.topografix.com/GPX/1/1">
'''
    gpx_footer = '''</gpx>
'''

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    waypoints = []
    for _, row in df.iterrows():
        try:
            lon = float(row["Coordenada X"])
            lat = float(row["Coordenada Y"])
        except (ValueError, TypeError):
            continue

        gasolina_95 = row.get("Precio Gasolina 95 E5", "")
        gasoleo_a = row.get("Precio Gasoleo A", "")
        provincia = escape(str(row.get("PROVINCIA", "")))
        municipio = escape(str(row.get("MUNICIPIO", "")))
        centro = escape(str(row.get("CENTRO", "")))
        direccion = escape(str(row.get("DIRECCIÓN", "")))

        description = f"""Gasolina 95: {gasolina_95}
Gasoleo A: {gasoleo_a}
Provincia: {provincia}
Municipio: {municipio}
Centro: {centro}
Direccion: {direccion}"""

        waypoint = f"""
  <wpt lat="{lat}" lon="{lon}">
    <name>{centro}</name>
    <desc>{description}</desc>
    <time>{now}</time>
  </wpt>
"""
        waypoints.append(waypoint)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(gpx_header)
        for wp in waypoints:
            f.write(wp)
        f.write(gpx_footer)

if __name__ == "__main__":

    if os.path.exists('.env'):
        load_dotenv('.env', override=True)

        CIRCULO_CONDUCTORES_CSV_FILENAME = os.getenv("CIRCULO_CONDUCTORES_CSV_FILENAME", DEFAULT_CIRCULO_CONDUCTORES_CSV_FILENAME)
        CIRCULO_CONDUCTORES_SHEET_URL = os.getenv("CIRCULO_CONDUCTORES_SHEET_URL", DEFAULT_CIRCULO_CONDUCTORES_SHEET_URL)
        PRICE_URL = os.getenv("MINISTRY_PRICE_URL", DEFAULT_MINISTRY_PRICE_URL)
        LOG_FILE = os.getenv("LOG_STATIONS_FILE", DEFAULT_LOG_FILE)
        STATIONS_FILE = os.getenv("STATIONS_PRICE_FILE", DEFAULT_STATIONS_PRICE_FILE)


    parser = argparse.ArgumentParser(
        description="Downloading prices for Circulo Conductores petrol stations",
        allow_abbrev=False
    )

    parser.add_argument(
        "--log-console",
        action="store_true",
        default=False,
        help="Enable logging to console (default: False)"
    )

    args = parser.parse_args()

    # Set up logging to write to a file instead of the console
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Handler para fichero rotativo (100MB, hasta 3 backups)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=100*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(message)s'))
    logger.addHandler(file_handler)

    # Handler para consola solo si --log-console está presente
    if args.log_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(message)s'))
        logger.addHandler(console_handler)


    df_cc = get_circulo_conductores_dataframe(CIRCULO_CONDUCTORES_CSV_FILENAME, CIRCULO_CONDUCTORES_SHEET_URL)

    # Remove rows where the "Red Fleet" column is "No"
    df_cc = df_cc[df_cc["Red Fleet"].str.lower() != "no"]
    
    df_min = get_ministry_dataframe(PRICE_URL)    

    df_cc, df_min = normalize_dfs(df_cc, df_min)

    # Group stations by province
    stations_grouped = df_min.groupby("PROVINCIA")

    # Apply the function
    df_cc[["Precio Gasolina 95 E5", "Precio Gasoleo A"]] = df_cc.apply(lambda row: price_nearest_station(row, stations_grouped), axis=1, result_type="expand")

    df_cc.to_csv(STATIONS_FILE.replace(".kml", ".csv"), index=False)

    create_kml(df_cc, STATIONS_FILE)
    create_gpx(df_cc, STATIONS_FILE.replace(".kml", ".gpx"))