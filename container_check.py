"""
Program that constantly checks if a docker container is running.
It checks the Loop timestamps and notifies vie Telegram if the last timestamp was older than 15 mins.
"""
import os
import sys
import time
import datetime
import requests
from re import compile


def telegram_send_message(message_text: str) -> requests.Response or None:
    """Sends a Telegram message to a specified chat."""
    telegram_token: str = ""
    telegram_chat_id: str = ""

    message_text = str(message_text)
    env_text = os.popen("cat .env").read()

    values = [val for val in env_text.split("\n") if val != ""]
    for val in values:
        if "TOKEN" in val:
            telegram_token = val.split("=")[1]
        elif "CHAT_ID_DEBUG" in val:
            telegram_chat_id = val.split("=")[1]

    if telegram_token == "" or telegram_chat_id == "":
        raise Exception("Invalid Telegram Token or Chat ID!")

    # construct url using token for a sendMessage POST request
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"

    # Construct data for the request
    payload = {"chat_id": telegram_chat_id, "text": message_text,
               "disable_web_page_preview": False, "parse_mode": "HTML"}

    # send the POST request
    try:
        # If too many requests, wait for Telegram's rate limit
        while True:
            post_request = requests.post(url=url, data=payload, timeout=15)

            if post_request.json()['ok']:
                return post_request

            time.sleep(3)

    except ConnectionError:
        return None


if len(sys.argv) != 2:
    sys.exit(f"Usage: python3 {os.path.basename(__file__)} <container_name>\n")

wait_time = 15 * 60
time.sleep(300)

current_dir = os.getcwd()
CHAT_ID = "-772766575"
time_format = "%Y-%m-%d %H:%M:%S, %Z"
time_format_regex = compile("\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}, [A-Za-z]*")

container_name = sys.argv[-1]


while True:
    # Get timestamp of last execution loop
    command = f"docker logs {container_name} | tail -n 50"
    output = os.popen(command).read()

    # Find last Loop timestamp
    time_str = time_format_regex.findall(output)[-1]

    # Construct date_time object from string
    script_time = datetime.datetime.strptime(time_str, time_format)

    now_time = datetime.datetime.now()

    # Calculate time difference in seconds
    time_diff = (now_time - script_time).seconds

    if time_diff > wait_time:
        message = f"WARNING - {now_time}\n" \
                  f"Container: {container_name}, path: {current_dir} has stopped!"
        # Send Telegram message in Debug Chat
        telegram_send_message(message)

        break

    time.sleep(wait_time)
