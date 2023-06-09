from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import selenium.webdriver.support.expected_conditions as EC
from loguru import logger
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import toml
import csv
import sqlite3

config = toml.load("./config.toml")
INSTANCE = config["AirWatch"]["instance"]
USERNAME = config["AirWatch"]["username"]
PASSWORD = config["AirWatch"]["password"]
database = config["AirWatch"]["database_location"]

logger.add("device.log", format="{time} | {level} | {message}")

    
def initialize_driver():
    options = Options()
    options.add_argument(f'--log-level=3')
    service = Service(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=options)
    driver.get(f"https://{INSTANCE}.awmdm.com/AirWatch/Login")
    return driver

def login(driver=None):
    wait = WebDriverWait(driver, 15, poll_frequency=0.5)
    email_input = wait.until(EC.element_to_be_clickable((By.ID, "UserName")))
    email_input.send_keys(USERNAME)
    next = wait.until(EC.element_to_be_clickable((By.NAME, "Login")))
    next.click()
    pass_input = wait.until(EC.element_to_be_clickable((By.ID, "Password")))
    pass_input.send_keys(PASSWORD)
    next = wait.until(EC.element_to_be_clickable((By.NAME, "Login")))
    next.click()
    otp_input = wait.until(EC.element_to_be_clickable((By.ID, "TwoFactorAuthToken")))
    driver.minimize_window()
    otp = input("Enter OTP: ")
    driver.maximize_window()
    otp_input.send_keys(otp)
    login = wait.until(EC.element_to_be_clickable((By.NAME, "Login")))
    login.click()
    # Verify login
    wait.until(EC.element_to_be_clickable((By.ID, "location_group")))

def query(serial_number, driver=None,):
    driver.get(f'https://{INSTANCE}.awmdm.com/#/AirWatch/Search?query={serial_number}')
    wait = WebDriverWait(driver, 15, poll_frequency=0.5)
    wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "#global_search_header > em:nth-child(2)"), serial_number))
    try:
        no_devices = driver.find_element(By.CSS_SELECTOR,"#devices_search_results > h1")
        if "No Devices Found" in no_devices.text:
            # Device does not need taking off
            return (serial_number, False)
    except:
        # Device needs moving
        return (serial_number, True)
    
def run():
    driver = initialize_driver()
    login(driver)
    # each line is another device. do things with each device
    for device in read_db():
        # breakout of the encapsuting list, attempt to remove extra whitespace
        device = device.strip()
        # Query airwatch, returning the device id & if it is installed
        device, state = query(device, driver=driver)
        if state:
            update_db(device, True)
            logger.info(f"{device}, installed")
        else:
            update_db(device, False)
            logger.info(f"{device}, Not installed")
    # Keep alive
    return driver

def update_db(serial_number, needs_removal):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE MC18 SET Airwatch_removal_required = (?),
        Date_Checked = date(),
        Airwatch_checked = 1
        WHERE Serial_Number like (?) AND Date_Checked is null
    """, (int(needs_removal), "%"+serial_number))
    conn.commit()
    pass

def display_removals_and_update():
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute("SELECT Serial_Number from MC18 WHERE Airwatch_removal_required = 1 and Date_Checked = date()")
    rows = cursor.fetchall()
    for row in rows:
        logger.debug(row[0])
        # print(row[0])
        update_db(row[0], False)



def read_db():
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute("SELECT Serial_Number from MC18 WHERE Airwatch_checked = 0")
    rows = cursor.fetchall()
    logger.debug(f'Found {len(rows)}')
    return [serial for serial in clean_raw_serial(rows)]
    

def clean_raw_serial(serials):
    for serial in serials:
        serial = serial[0].upper()
        if len(serial) == 0:
            return
        if serial[0] == "S":
            serial = serial[1:]
        if type(serial) == str and len(serial) == 14:
            yield serial

if __name__ == "__main__":
    driver = run()
    display_removals_and_update()
    input()