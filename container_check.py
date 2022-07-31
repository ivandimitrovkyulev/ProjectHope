"""
Program that constantly checks if a docker container is running.
It checks the Loop timestamps and notifies vie Telegram if the last timestamp was older than 15 mins.
"""
import os
import sys
import time
import datetime

from src.projecthope.common.message import telegram_send_message
from src.projecthope.common.variables import (
    CHAT_ID_DEBUG,
    time_format,
    time_format_regex,
)


if len(sys.argv) != 2:
    sys.exit(f"Usage: python3 {os.path.basename(__file__)} <container_name>\n")

wait_time = 15 * 60
time.sleep(300)
container_name = sys.argv[-1]
current_dir = os.getcwd()


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
        telegram_send_message(message, telegram_chat_id=CHAT_ID_DEBUG)

        break

    time.sleep(wait_time)