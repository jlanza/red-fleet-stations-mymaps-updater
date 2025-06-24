from playwright.sync_api import sync_playwright
import os
import logging
from logging.handlers import RotatingFileHandler
import argparse
from dotenv import load_dotenv

# Chrome User-Agent on Windows 10
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# URL of Google Account Login
ACCOUNT_GOOGLE_URL = "https://accounts.google.com/"

# Folder where the session is saved
DEFAULT_USER_SESSION_DATA_DIR = "google_session"

DEFAULT_LOG_FILE = "mymaps.log"

# STATIONS_FILE = r"D:\05_Proyectos_tlmat\gasolineras_all.kml"

def manual_session_google():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            args=["--disable-blink-features=AutomationControlled"], 
            user_data_dir=USER_DATA_DIR,
            headless=False
        )
        page = browser.new_page()
        page.goto(ACCOUNT_GOOGLE_URL)
        print("🔐 Please log in to Google manually.")
        input("✅ Press Enter here when you have finished logging in...")
        browser.close()

def stored_session_google():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            args=["--disable-blink-features=AutomationControlled"], 
            user_data_dir=USER_SESSION_DATA_DIR,
            headless=False
        )
        page = browser.new_page()
        page.goto("https://www.google.com/")
        input("✅ Press Enter to close the browser...")
        browser.close()

# Run this the first time to save the session
# manual_session_google()
# exit()

# Then you can use this function to reuse the session
# stored_session_google()


# tengo que mirar como se hace para ponerlo en la configuración de playwright
# https://playwright.dev/python/docs/api/class-browsercontext#browser-context-user-agent
# Y la parte de disable-blink-features=AutomationControlled es para evitar que Google detecte que es un bot
# y no me deje acceder a la página de Google Maps
# https://www.zenrows.com/blog/disable-blink-features-automationcontrolled#permanently-avoid-getting-blocked


# https://scribe.rawbit.ninja/@adequatica/google-authentication-with-playwright-8233b207b71a
def update_mymap_google(headless=True, persistent=False):
    with sync_playwright() as p:
        logging.info("\n🌐 Iniciando Playwright...")
        if persistent:
            # If you want to use a persistent session
            browser = p.chromium.launch_persistent_context(
                args=["--disable-blink-features=AutomationControlled"], 
                user_data_dir=USER_DATA_DIR,
                headless=headless)
            page = browser.new_page()
        else:
            # If you want to use a non-persistent session
            browser = p.chromium.launch(
                args=["--disable-blink-features=AutomationControlled"], 
                headless=headless) 
            context = browser.new_context(user_agent=CHROME_USER_AGENT)
            page = context.new_page()

        if not persistent:
            # If not using a persistent session, log in manually
            logging.info("🔐 Logging in to Google.")
            # Code to log in every time the browser is opened
            page.goto(ACCOUNT_GOOGLE_URL)
            page.wait_for_timeout(2000)  # Wait 2 seconds for the page to load
            page.fill("input[type='email']", USERNAME)
            page.locator("#identifierNext >> button").click()
            page.wait_for_timeout(2000)
            page.fill("#password >> input[type='password']", PASSWORD)
            page.locator('button >> nth=1').click()
            page.wait_for_timeout(5000)

        logging.info("🗺️ Opening Google My Maps...")
        page.goto(MAP_URL)
        page.wait_for_timeout(1000)  # Wait 1 second to view the page

        logging.info("🔄 Reimporting the gas stations file...")
        page.get_by_label("Layer options").click()
        page.get_by_text("Reimport and merge►").click()
        page.get_by_text("Reimport►").click()
        page.get_by_text("Replace all items").click()
        page.wait_for_timeout(1000)  # Wait 1 second to view the page

        # Iterate over all frames on the page
        for frame in page.frames:
            try:
                # Try to locate the button by role and name within the frame
                button = frame.get_by_role("button", name="Browse")
                if button.is_visible():
                    logging.info(f"🔎 'Browse' button found in frame: {frame.name}")
                    # button.click()
                    locator = frame.locator('input[type="file"]')
                    if locator.count() > 0:
                        locator.set_input_files(STATIONS_FILE)
                        logging.info(f"📂 File uploaded: {STATIONS_FILE}")
                        page.wait_for_timeout(5000)  # Wait 5 seconds to view the page
                        logging.info("✅ Google My Maps updated successfully.")      
                        break
                    break  # Exit the loop after clicking
            except:
                pass  # If the frame does not contain the button or throws an error, ignore it

        browser.close()


if __name__ == "__main__":

    if os.path.exists('.env'):
        load_dotenv('.env', override=True)
        # Load environment variables from .env if they exist
        USERNAME = os.getenv("USERNAME")
        PASSWORD = os.getenv("PASSWORD")
        MAP_URL = os.getenv("MAP_URL")
        STATIONS_FILE = os.getenv("STATIONS_PRICE_FILE")
        missing_vars = [var for var, val in [
            ("USERNAME", USERNAME),
            ("PASSWORD", PASSWORD),
            ("MAP_URL", MAP_URL),
            ("STATIONS_FILE", STATIONS_FILE)
        ] if not val]
        if missing_vars:
            print(f"❌ The following variables are missing in the .env file: {', '.join(missing_vars)}")
            exit(1)
        LOG_FILE = os.getenv("LOG_MYMAPS_FILE", DEFAULT_LOG_FILE)
        USER_SESSION_DATA_DIR = os.getenv("USER_SESSION_DATA_DIR", DEFAULT_USER_SESSION_DATA_DIR)

    parser = argparse.ArgumentParser(
        description="Update Google My Maps with Playwright",
        allow_abbrev=False
    )
    parser.add_argument(
        "--persistent",
        action="store_true",
        default=False,
        help="Use persistent session (default: False)"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        default=False,
        help="Run in headed mode (default: False)"
    )

    parser.add_argument(
        "--log-console",
        action="store_true",
        default=False,
        help="Enable logging to console (default: False)"
    )

    parser.add_argument(
        "--file",
        required=False,
        help="Path to the KML file to import (if provided, overrides configuration)"
    )
    args = parser.parse_args()

    # Validate that only allowed arguments are passed
    allowed_args = {"persistent", "headed", "log_console", "file"}
    for arg in vars(args):
        if arg not in allowed_args:
            parser.error(f"Argument not allowed: --{arg.replace('_', '-')}")

    # If --file is provided, override STATIONS_FILE
    if args.file:
        STATIONS_FILE = args.file


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

    # logging.basicConfig(
    #     filename='mymaps.log',
    #     level=logging.INFO,
    #     format='%(asctime)s %(levelname)s:%(message)s'
    # )

    logging.debug("🔧 Current configuration:")
    logging.debug(f"  USERNAME: {USERNAME}")
    logging.debug(f"  PASSWORD: {'*' * len(PASSWORD) if PASSWORD else ''}")
    logging.debug(f"  MAP_URL: {MAP_URL}")
    logging.debug(f"  STATIONS_FILE: {STATIONS_FILE}")
    logging.debug(f"  LOG_FILE: {LOG_FILE}")
    logging.debug(f"  USER_SESSION_DATA_DIR: {USER_SESSION_DATA_DIR}")

    update_mymap_google(headless=(not args.headed), persistent=args.persistent)
