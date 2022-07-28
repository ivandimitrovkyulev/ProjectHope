import json
import os

import requests
from requests_cache import CachedSession

from datetime import datetime
from json.decoder import JSONDecodeError
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor

from typing import (
    Tuple,
    Iterator,
)
from src.projecthope.blockchain.evm import EvmContract
from src.projecthope.common.message import telegram_send_message
from src.projecthope.common.helpers import (
    parse_args,
    get_ttl_hash,
)
from src.projecthope.one_inch.datatypes import (
    Token,
    Swap,
)
from src.projecthope.common.logger import (
    log_arbitrage,
    log_error,
)
from src.projecthope.common.variables import (
    time_format,
    network_ids,
)


# Create an EVM contract class
contract = EvmContract()

# Set up requests session
session = requests.Session()

# Set up a cached session
cached_session = CachedSession(cache_name="w3_cache", backend='sqlite', expire_after=720)


def max_swap(results: Iterator[Swap]) -> Tuple[Swap, float]:
    """
    Analyses a list of swaps and returns the one with maximum amount.

    :param results: Generator object containing swaps
    :return: Tuple (dictionary, max_amount)
    """

    # Create dict with key-swap and value-all_data
    swaps = {swap.to_token.amount: swap for swap in results if swap}

    max_amount = max(swaps)
    swap = swaps[max_amount]

    return swap, max_amount


def get_eth_fees(gas_info: dict, gas_amount: int, bridge_fees_eth: float = 0.005510, timeout: int = 3) -> dict:
    """
    Calculates fees on Ethereum in USD dollars. Adds 'gas_price' and 'usdc_cost' to gas_info dictionary.
    Queries https://etherscan.io for ETH/USD info and caches result to avoid rate limit.

    :param gas_info: Dictionary with gas_info data
    :param gas_amount: Gas amount for transaction to be executed
    :param bridge_fees_eth: Eth bridge fees, default 0.005510 ETH
    :param timeout: Maximum time to wait per GET request
    :return: Dictionary with updated gas_info data
    """
    # Get ETH gas price from Web3. Result is cached for 1200 secs before querying again
    gas_price = contract.eth_gas_price(ttl_hash=get_ttl_hash(1200))
    gas_info['gas_price'] = gas_price

    api = f"https://api.etherscan.io/api?module=stats&action=ethprice&apikey={os.getenv('ETHERSCAN_API_KEY')}"
    try:
        # Cache only Etherscan API get requests!
        response = cached_session.get(api, timeout=timeout)
    except ConnectionError as e:
        log_error.warning(f"'ConnectionError' - {e}")
        return gas_info

    try:
        data = json.loads(response.content)
        eth_usdc_price = float(data['result']['ethusd'])
    except JSONDecodeError:
        log_error.warning(f"'JSONError' {response.status_code} - {response.url}")
        return gas_info

    gas_cost_usdc = ((gas_amount * gas_price) / 10 ** 18) * eth_usdc_price
    bridge_cost_usdc = bridge_fees_eth * eth_usdc_price
    gas_info['usdc_cost'] = gas_cost_usdc + bridge_cost_usdc

    return gas_info


def get_swapout(network_id: str, from_token: tuple, to_token: tuple, amount_float: float,
                max_retries: int = 3, timeout: int = 3) -> dict or None:
    """
    Queries https://app.1inch.io for swap_out amount between 2 tokens on a given network.

    :param network_id: Network id
    :param from_token: From token (swap in). Tuple format (address, name, decimals)
    :param to_token: To token (swap out). Tuple format (address, name, decimals)
    :param amount_float: Amount to swap in
    :param max_retries: Maximum number ot GET retries
    :param timeout: Maximum time to wait per GET request
    :return: Swap dictionary
    """
    api = f"https://api.1inch.io/v4.0/{network_id}/quote"
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

    gas_amount = data['estimatedGas']
    gas_info = {"gas_amount": gas_amount}

    # Calculate fees on Ethereum only and add to gas_info dict
    if int(network_id) == 1:
        get_eth_fees(gas_info, gas_amount, timeout=timeout)

    from_token = Token(from_token_name, from_token_decimal, amount_float)
    to_token = Token(to_token_name, to_token_decimal, swap_out_float)

    swap = Swap(network_name, network_id, gas_info, from_token, to_token)

    return swap


def compare_swaps(data: dict, base_token: str, arb_token: str) -> Tuple[Swap, Swap]:
    """
    Compares 1inch supported blockchains for arbitrage between 2 tokens.

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

    base_round = int(swap_ab.from_token.decimals // 4)
    arb_round = int(swap_ab.to_token.decimals // 4)

    base_swap_in = round(swap_ab.from_token.amount, base_round)
    arb_swap_out = round(swap_ab.to_token.amount, arb_round)
    base_swap_out = round(swap_ba.to_token.amount, base_round)
    arb_swap_in = round(swap_ba.from_token.amount, arb_round)

    chain1 = swap_ab.chain
    chain2 = swap_ba.chain

    arbitrage = base_swap_out - base_swap_in
    arbitrage = round(arbitrage, base_round)

    if arbitrage >= min_arb:
        timestamp = datetime.now().astimezone().strftime(time_format)
        telegram_msg = f"{timestamp}\n" \
                       f"1) <a href='https://app.1inch.io/#/{swap_ab.id}/swap/{base_token}/{arb_token}'>" \
                       f"Sell {base_swap_in:,} {base_token} for {arb_swap_out:,} {arb_token} on {chain1}</a>\n" \
                       f"2) <a href='https://app.1inch.io/#/{swap_ba.id}/swap/{arb_token}/{base_token}'>" \
                       f"Sell {arb_swap_in:,} {arb_token} for {base_swap_out:,} {base_token} on {chain2}</a>\n" \
                       f"-->Arbitrage: {arbitrage:,} {base_token}"

        terminal_msg = f"1) {base_swap_in:,} {base_token} for {arb_swap_out:,} {arb_token} on {chain1}\n" \
                       f"2) {arb_swap_in:,} {arb_token} for {base_swap_out:,} {base_token} on {chain2}\n" \
                       f"-->Arbitrage: {arbitrage:,} {base_token}"

        if int(swap_ab.id) == 1 or int(swap_ba.id) == 1:
            fee1 = swap_ab.gas_info.get('usdc_cost')
            fee2 = swap_ba.gas_info.get('usdc_cost')
            if fee1:
                fee_msg = f", swap+bridge fees ~${fee1:,.0f}"
            elif fee2:
                fee_msg = f", swap+bridge fees ~${fee2:,.0f}"
            else:
                fee_msg = f", swap+bridge fees n/a"

            telegram_msg += fee_msg
            terminal_msg += fee_msg

        # Send arbitrage to ALL alerts channel and log
        telegram_send_message(telegram_msg)
        log_arbitrage.info(terminal_msg)
        print(f"{terminal_msg}\n")
