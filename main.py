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

config = toml.load("./config.toml")
INSTANCE = config["AirWatch"]["instance"]
USERNAME = config["AirWatch"]["username"]
PASSWORD = config["AirWatch"]["password"]

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
    # Open csv file in readonly mode
    with open('devices_to_process.csv', mode='r') as file:
        # read csv file
        csv_file = csv.reader(file)
        # each line is another device. do things with each device
        for device in csv_file:
            # breakout of the encapsuting list, attempt to remove extra whitespace
            device = device[0].strip()
            # Query airwatch, returning the device id & if it is installed
            device, state = query(device, driver=driver)
            if state:
                logger.info(f"{device}, installed")
            else:
                logger.info(f"{device}, Not installed")

if __name__ == "__main__":
    run()
    # input pauses at the end, giving the user chance to remove device that need doing
    input()