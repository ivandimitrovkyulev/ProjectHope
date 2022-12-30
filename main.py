import os
import sys
import json

from atexit import register
from datetime import datetime
from time import (
    sleep,
    perf_counter,
)
from multiprocessing import Process
from concurrent.futures import ThreadPoolExecutor

from src.projecthope.compare import alert_arb
from src.projecthope.one_inch.api import get_swapout
from src.projecthope.binance.api import start_binance_streams

from src.projecthope.common.exceptions import exit_handler
from src.projecthope.common.helpers import print_start_message
from src.projecthope.common.message import telegram_send_message
from src.projecthope.common.logger import log_error
from src.projecthope.common.variables import (
    time_format,
    base_tokens,
)


def arb_screener(args: list, time_to_sleep: int) -> None:
    """
    Main function that constantly screens for arbitrage between 1inch and binance trading pairs.

    :param args: Arguments list to pass
    :param time_to_sleep: While loop sleep time
    """
    loop_counter = 1
    total_calls = 0
    while True:
        start = perf_counter()

        with ThreadPoolExecutor(max_workers=len(args)) as executor:
            arbs = executor.map(lambda p: alert_arb(*p), args, timeout=10)

        for arb in arbs:
            if not arb:
                log_error.warning(f"'alert_arb' Error - {arb[0]} -> {arb[1]}")

        sleep(time_to_sleep)

        time_stamp = datetime.now().astimezone().strftime(time_format)
        print(f"{time_stamp}: Loop {loop_counter} executed in {(perf_counter() - start):,.2f} secs. "
              f"1inch API calls: {abs(total_calls - get_swapout.calls)}")

        total_calls = get_swapout.calls
        loop_counter += 1


if __name__ == "__main__":

    if len(sys.argv) != 2:
        sys.exit(f"Usage: python3 {os.path.basename(__file__)} <input_file>\n")

    # Send telegram debug message if program terminates
    program_name = os.path.abspath(os.path.basename(__file__))
    register(exit_handler, program_name)

    # Fetch variables
    info: dict = json.loads(sys.argv[-1])
    sleep_time, base_token = info["settings"].values()

    timestamp = datetime.now().astimezone().strftime(time_format)
    print_start_message(info, base_token, timestamp)
    telegram_send_message(f"✅ PROJECTHOPE has started.")

    arb_tokens = [token for token in info['coins'] if token not in base_tokens]

    # Start Binance WebSockets for traiding pairs
    trading_pairs = [f"{token}{base_token}" for token in arb_tokens]

    # Create all Base-Arbitrage token pairs
    arguments = [[info, base_token, arb_token] for arb_token in arb_tokens]

    binance_stream = Process(target=start_binance_streams, args=(trading_pairs, ))
    main_screener = Process(target=arb_screener, args=(arguments, sleep_time, ))

    binance_stream.start()  # Start Process 1 - Binance WebSocket streams
    sleep(3)  # Wait initially for WebSocket handshake
    main_screener.start()  # Start Process 2 - Main arbitrage screener loop

    while True:
        sleep(86395)  # Restart every 23:55 hours and restart binance stream
        binance_stream.terminate()
        binance_stream = Process(target=start_binance_streams, args=(trading_pairs,))
        binance_stream.start()