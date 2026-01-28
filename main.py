from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
import requests, time
from bs4 import BeautifulSoup
import config

json_token = ""
active_sessions = []
BASE_URL = "https://lovelyprofessionaluniversity.codetantra.com"

service = Service(config.webdriverExecutablePath)

chrome_options = Options()
chrome_options.add_argument("--use-fake-ui-for-media-stream")
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

if config.headless:
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=chrome_options, service=service)

if not config.headless:
    driver.maximize_window()

USERNAME = config.regNo
PASSWORD = config.password
BOT_TOKEN = config.botToken
CHAT_ID = config.chatId


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        log("Telegram send failed:", e)

def log(msg: str):
    print   (msg)
    send_telegram(msg)

def login(username, password):
    url = BASE_URL + "/r/l/p"
    data = f"i={username}&p={password}"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://myclass.lpu.in/"
    }
    response = requests.post(url, headers=headers, data=data)
    return response.headers["Set-Cookie"]

def fetch_meetings(wtj_token):
    url = BASE_URL + "/secure/rest/dd/mf"
    time_curr = int(time.time()*1000)
    data = '{"minDate":'+ str(time_curr-(15*3600000)) +',"maxDate":' + str(time_curr+(15*3600000)) + ',"filters":{"showSelf":true,"status":"started,ended,scheduled"}}'
    headers={
        "cookie": wtj_token,
        "Referer": BASE_URL + "/secure/tla/mi.jsp",
    }
    response = requests.post(url, headers=headers, data=data)
    for i in response.json()["ref"]:
        if i["status"] == "started": return (i["_id"], i["title"])
    return None, None

def fetch_meeting(cookie, meeting_id):
    url = BASE_URL + "/secure/tla/jnr.jsp?m="+meeting_id
    headers = {
        "cookie": cookie,
        "Referer": BASE_URL + "/secure/tla/mi.jsp",
    }
    response = requests.get(url, headers=headers)
    return response.content.decode('utf-8')

def get_session_url(raw_data):
    soup = BeautifulSoup(raw_data, "html.parser")
    frame = soup.find("iframe", {"id": "frame"})
    return frame.get("src")

def get_session_token(url):
    response = requests.head(url, allow_redirects=False)
    return response.headers['location']

def findnclick_xpath(xpath):
    wait = WebDriverWait(driver, 3600)
    click = lambda : wait.until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
    try:
        click()
    except WebDriverException as e:
        time.sleep(10)
        click()

def connect2class(url):
    driver.get(url)
    if (config.joinAudio):
        if (config.audioMode == 0):
            findnclick_xpath("/html/body/div[2]/div/div/div[1]/div/div/span/button[2]")
        elif (config.audioMode == 1):
            findnclick_xpath("/html/body/div[2]/div/div/div[1]/div/div/span/button[1]")
            findnclick_xpath("/html/body/div[2]/div/div/div[1]/div/span/button[1]")
    else:
        findnclick_xpath("/html/body/div[2]/div/div/header/button")


def main():
    global json_token
    while True:
        log("[*] Fetching meetings..")
        try:
            mid, title = fetch_meetings(json_token)
        except Exception:
            json_token = login(USERNAME, PASSWORD)
            continue
        if (mid, title) != (None, None) and mid not in active_sessions:
            log("[+] Live meeting found: ", title)
            meeting_data = fetch_meeting(json_token, mid)
            log("[*] Getting session url...")
            try:
                sess_url = get_session_url(meeting_data)
                sess_url = get_session_token(sess_url)
            except AttributeError:
                log('[-] Class locating failed.. Retrying in 10 sec')
                time.sleep(10)
                continue
            log("[+] Connecting to the class...")
            connect2class(sess_url)
            active_sessions.append(mid)
            log("[+] Connected successfully.")
        else: log(f"[-] No more live meeting found. Refreshing in {config.refreshTime}s")
        time.sleep(config.refreshTime)

if __name__ == '__main__':
    json_token = login(USERNAME, PASSWORD)
    main()