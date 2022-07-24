import json
import requests
from json.decoder import JSONDecodeError
from requests.adapters import HTTPAdapter

from src.projecthope.common.logger import log_error
from src.projecthope.common.variables import network_ids


def get_swapout(network_id: str, from_token: tuple, to_token: tuple, amount: float,
                max_retries: int = 3, timeout: int = 3) -> float or None:
    """
    Queries https://app.1inch.io for swap out amount between 2 tokens on a given network.

    :param network_id: Network id
    :param from_token: From token (swap in). Tuple format (address, name, decimals)
    :param to_token: To token (swap out). Tuple format (address, name, decimals)
    :param amount: Amount to swap in
    :param max_retries: Maximum number ot GET retries
    :param timeout: Maximum time to wait per GET request
    :return: Swap out amount
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

    network_name = network_ids[network_id]

    amount = amount * (10 ** from_token_decimal)

    payload = {"fromTokenAddress": from_token_addr,
               "toTokenAddress": to_token_addr,
               "amount": amount}
    try:
        response = session.get(api, params=payload, timeout=timeout)
    except ConnectionError:
        log_error.warning(f"'ConnectionError': Unable to fetch amount for "
                          f"{network_name} {from_token_name} -> {to_token_name}")
        return None

    if response.status_code != 200:
        log_error.warning(f"'ResponseError' {response.status_code} - {response.url}")
        return None

    try:
        data = json.loads(response.content)
    except JSONDecodeError:
        log_error.warning(f"'JSONError' {response.status_code} - {response.url}")
        return None

    swap_out = float(data['toTokenAmount'])
    swap_out = swap_out / (10 ** to_token_decimal)

    return swap_out
