import os
import json
import requests

from requests.exceptions import ReadTimeout
from requests_cache import CachedSession
from urllib3 import Retry

from json.decoder import JSONDecodeError
from requests.adapters import HTTPAdapter

from src.projecthope.blockchain.evm import EvmContract
from src.projecthope.common.decorators import count_func_calls
from src.projecthope.common.helpers import get_ttl_hash
from src.projecthope.one_inch.datatypes import (
    Token,
    Swap,
)
from src.projecthope.common.logger import log_error
from src.projecthope.common.variables import network_ids


# Create an EVM contract class
contract = EvmContract()

# Set up and configure requests session
session = requests.Session()
retry_strategy = Retry(total=2, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

# Set up a cached session that expires in 12 mins. Used for getting ETH fees only
cached_session = CachedSession(cache_name="w3_cache", backend='sqlite', expire_after=720)


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
    except ConnectionError or ReadTimeout as e:
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


@count_func_calls
def get_swapout(network_id: str, from_token: tuple, to_token: tuple,
                amount_float: float, timeout: int = 2, include_fees: bool = True) -> dict or None:
    """
    Queries https://app.1inch.io for swap_out amount between 2 tokens on a given network.

    :param network_id: Network id
    :param from_token: From token (swap in). Tuple format (address, name, decimals)
    :param to_token: To token (swap out). Tuple format (address, name, decimals)
    :param amount_float: Amount to swap in
    :param timeout: Maximum time to wait per GET request
    :param include_fees: Include Eth fees?
    :return: Swap dataclass: (network_name, network_id, gas_info, from_token, to_token)
    """
    api = f"https://api.1inch.io/v4.0/{network_id}/quote"

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
        # requests.get passed throught get_request_1inch func in order to count GET calls
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
                          f"{network_name}, {amount_float} {from_token_name} -> {to_token_name}")
        return None

    swap_out = float(data['toTokenAmount'])
    swap_out_float = swap_out / (10 ** to_token_decimal)

    gas_amount = data['estimatedGas']
    gas_info = {"gas_amount": gas_amount}

    # Calculate fees on Ethereum only and add to gas_info dictionary
    if include_fees and int(network_id) == 1:
        get_eth_fees(gas_info, gas_amount, timeout=timeout)

    from_token = Token(from_token_name, from_token_decimal, amount_float)
    to_token = Token(to_token_name, to_token_decimal, swap_out_float)

    swap = Swap(network_name, network_id, gas_info, from_token, to_token)

    return swap
