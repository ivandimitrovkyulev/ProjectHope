import json
import requests

from datetime import datetime
from json.decoder import JSONDecodeError
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor

from src.projecthope.common.message import telegram_send_message
from src.projecthope.common.logger import (
    log_arbitrage,
    log_error,
)
from src.projecthope.common.helpers import (
    parse_args,
    max_swap,
)
from src.projecthope.common.variables import (
    time_format,
    network_ids,
)


def get_swapout(network_id: str, from_token: tuple, to_token: tuple, amount_float: float,
                max_retries: int = 3, timeout: int = 3) -> dict or None:
    """
    Queries https://app.1inch.io for swap out amount between 2 tokens on a given network.

    :param network_id: Network id
    :param from_token: From token (swap in). Tuple format (address, name, decimals)
    :param to_token: To token (swap out). Tuple format (address, name, decimals)
    :param amount_float: Amount to swap in
    :param max_retries: Maximum number ot GET retries
    :param timeout: Maximum time to wait per GET request
    :return: Swap dictionary
    """

    api = f"https://api.1inch.io/v4.0/{network_id}/quote"
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=max_retries))

    from_token_addr = str(from_token[0])
    from_token_name = from_token[1]
    from_token_decimal = int(from_token[2])

    to_token_addr = str(to_token[0])
    to_token_name = to_token[1]
    to_token_decimal = int(to_token[2])

    network_name = network_ids[str(network_id)]

    amount = int(amount_float * (10 ** from_token_decimal))

    payload = {"fromTokenAddress": from_token_addr,
               "toTokenAddress": to_token_addr,
               "amount": str(amount)}
    try:
        response = session.get(api, params=payload, timeout=timeout)
    except ConnectionError:
        log_error.warning(f"'ConnectionError': Unable to fetch amount for "
                          f"{network_name} {from_token_name} -> {to_token_name}")
        return None

    try:
        data = json.loads(response.content)
    except JSONDecodeError:
        log_error.warning(f"'JSONError' {response.status_code} - {response.url}")
        return None

    if response.status_code != 200:
        log_error.warning(f"'ResponseError' {response.status_code}, {data['error']}, {data['description']} - "
                          f"{network_name} {from_token_name} -> {to_token_name}")
        return None

    swap_out = float(data['toTokenAmount'])
    swap_out_float = swap_out / (10 ** to_token_decimal)

    gas = data['estimatedGas']

    return {
        "network": network_name, "network_id": network_id, "gas": gas,
        "from_token": {"token": from_token_name, "amount": amount_float, "decimals": from_token_decimal},
        "to_token": {"token": to_token_name, "amount": swap_out_float, "decimals": to_token_decimal}
    }


def compare_swaps(data: dict, base_token: str, arb_token: str) -> tuple:
    """
    Checks 1inch supported blockchains for arbitrage between 2 tokens.

    :param data: Input dictionary data
    :param base_token: Name of Base token being swapped in
    :param arb_token: Name of token being Arbitraged
    :return: Dictionary of Swap_ab & Swap_ba data
    """
    # Query networks for Base->Arb swap out
    args_ab = parse_args(data, base_token, arb_token)
    with ThreadPoolExecutor(max_workers=len(args_ab)) as pool:
        results = pool.map(lambda p: get_swapout(*p), args_ab, timeout=30)

    # Get the maximum swap out
    max_swap_ab, max_amount_ab = max_swap(results)

    # Query networks for Arb->Base swap out
    args_ba = parse_args(data, arb_token, base_token, max_amount_ab)
    with ThreadPoolExecutor(max_workers=len(args_ba)) as pool:
        results = pool.map(lambda p: get_swapout(*p), args_ba, timeout=30)

    # Get the maximum swap out
    max_swap_ba, _ = max_swap(results)

    return max_swap_ab, max_swap_ba


def alert_arb(data: dict, base_token: str, arb_token: str) -> None:
    """
    Alerts via Telegram for arbitrage if found.

    :param data: Input dictionary data
    :param base_token: Name of Base token being swapped in
    :param arb_token: Name of token being Arbitraged
    """
    # Get arbitrage data
    swap_ab, swap_ba = compare_swaps(data, base_token, arb_token)

    min_arb = data['arb_tokens'][arb_token]['min_arb']

    base_round = int(swap_ab['from_token']['decimals'] / 3)
    arb_round = int(swap_ab['to_token']['decimals'] / 3)

    base_swap_in = round(swap_ab['from_token']['amount'], base_round)
    arb_swap_out = round(swap_ab['to_token']['amount'], arb_round)
    network_1 = swap_ab['network']
    network_1_id = swap_ab['network_id']
    base_swap_out = round(swap_ba['to_token']['amount'], base_round)
    arb_swap_in = round(swap_ba['from_token']['amount'], arb_round)
    network_2 = swap_ba['network']

    arbitrage = base_swap_out - base_swap_in
    arbitrage = round(arbitrage, base_round)

    if arbitrage >= min_arb:
        timestamp = datetime.now().astimezone().strftime(time_format)
        telegram_msg = f"{timestamp}\n" \
                       f"1. Sell {base_swap_in:,} {base_token} for {arb_swap_out:,} {arb_token} on {network_1}\n" \
                       f"2. Sell {arb_swap_in:,} {arb_token} for {base_swap_out:,} {base_token} on {network_2}\n" \
                       f"<a href='https://app.1inch.io/#/{network_1_id}/swap/{base_token}/{arb_token}'>" \
                       f"-->Arbitrage: {arbitrage:,} {base_token}</a>"

        terminal_msg = f"1. Sell {base_swap_in:,} {base_token} for {arb_swap_out:,} {arb_token} on {network_1}\n" \
                       f"2. Sell {arb_swap_in:,} {arb_token} for {base_swap_out:,} {base_token} on {network_2}\n" \
                       f"-->Arbitrage: {arbitrage:,} {base_token}"

        # Send arbitrage to ALL alerts channel and log
        telegram_send_message(telegram_msg)
        log_arbitrage.info(terminal_msg)
        print(terminal_msg)
