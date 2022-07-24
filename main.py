import os
import sys
import json

from copy import deepcopy
from pprint import pprint
from atexit import register
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from time import (
    sleep,
    perf_counter,
)
from src.projecthope.one_inch import get_swapout

from src.projecthope.common.exceptions import exit_handler
from src.projecthope.common.message import telegram_send_message
from src.projecthope.common.logger import log_arbitrage
from src.projecthope.common.variables import (
    time_format,
    CHAT_ID_ALERTS_FILTER,
    network_names,
)


if len(sys.argv) != 2:
    sys.exit(f"Usage: python3 {os.path.basename(__file__)} <input_file>\n")

# Send telegram debug message if program terminates
program_name = os.path.abspath(os.path.basename(__file__))
#register(exit_handler, program_name)

# Fetch variables
info = json.loads(sys.argv[-1])
timestamp = datetime.now().astimezone().strftime(time_format)
print(f"{timestamp} - Started screening:")

base_token_name = "USDC"
arb_token_name = "gOHM"

from_networks = info['base_tokens'][base_token_name]['networks']
to_networks = info['arb_tokens'][arb_token_name]['networks']
amount = info['base_tokens'][base_token_name]['swap_amount']

from_to_args = []
for network, data in to_networks.items():
    network_id = network_names[network]
    from_token = (from_networks[network]['address'], base_token_name, from_networks[network]['decimals'])
    to_token = (data['address'], arb_token_name, data['decimals'])

    from_to_args.append([network_id, from_token, to_token, amount])

for arg in from_to_args:
    swap1 = get_swapout(*arg)
    if swap1:
        print(swap1)

        arg[1], arg[2] = arg[2], arg[1]
        arg[-1] = swap1['to_token']['amount']
        swap2 = get_swapout(*arg)
        print(swap2)

        print()