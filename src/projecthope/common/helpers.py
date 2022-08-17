import time

from typing import (
    List,
    Dict,
    Tuple,
)
from tabulate import tabulate
from src.projecthope.common.variables import network_names
from src.projecthope.common.variables import base_tokens


def compare_lists(new_list: List[Dict[str, str]], old_list: List[Dict[str, str]],
                  keyword: str = 'hash') -> list:
    """
    Compares two lists of dictionaries.

    :param new_list: New list
    :param old_list: Old list
    :param keyword: Keyword to compare with
    :return: List of dictionaries that are in new list but not in old list
    """

    try:
        hashes = [txn[keyword] for txn in old_list]

        list_diff = [txn for txn in new_list if txn[keyword] not in hashes]

        return list_diff

    except TypeError:
        return []


def parse_args_1inch(data: dict, a_token: str, b_token: str,
                     amounts: float = 0) -> Tuple[List[list], list]:
    """
    Constructs a list of arguments for the 1inch 'get_swapout' function.

    :param data: Dictionary containing all token data
    :param a_token: Name of Base Token
    :param b_token: Name of Arb Token
    :param amounts: Amounts to swap. If empty - takes swap_amount from data
    :return: Tuple of list of tokens & range amounts

    Returns
    -------
    >>> parse_args_1inch(...)
    ([['1', ('0xA0b8', 'USDC', 6), ('0xAf51', 'STG', 18), 4000]...], [3000, 5000, 8000])
        ^    ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾    ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾     ^                ^
       ID         Token A                 Token B        Amount           amounts
    >>>

    """
    if a_token not in data:
        raise Exception(f"Token '{a_token}' not in coin data.")
    if b_token not in data:
        raise Exception(f"Token '{b_token}' not in coin data.")

    a_networks = data[a_token]['networks']
    b_networks = data[b_token]['networks']

    if amounts == 0:
        try:
            amounts = data[b_token]['swap_amount']
        except KeyError:
            raise Exception(f"Must provide range amounts for {a_token} -> {b_token} token swap.")

    args_ab = []
    for network, data in b_networks.items():
        network_id = network_names[network]
        to_token = (data['address'], b_token, data['decimals'])

        try:
            from_token = (a_networks[network]['address'], a_token, a_networks[network]['decimals'])
        except KeyError:
            # Skip if arbitraged token not on this network
            continue

        if type(amounts) is list:
            for amount in amounts:
                args_ab.append([network_id, from_token, to_token, amount])
        else:
            args_ab.append([network_id, from_token, to_token, amounts])

    return args_ab, amounts


def get_ttl_hash(seconds: int = 1200) -> int:
    """
    Function intended to be used with Python's functools.lru_cache only.
    Implements a length in which lru_cache will be used before clearing.

    :param seconds: How long to use cache for before clearing it up. Default is 20 minutes
    :return: Number of seconds
    """
    return round(time.time() / seconds)


def print_start_message(info: dict, base_token: str, timestamp: str) -> None:

    print(f"{timestamp} - Started screening the following configurations:")

    arb_tokens = [token for token in info if token not in base_tokens]

    message = []
    for i, arb_token in enumerate(arb_tokens):

        arb_token_networks = [net for net in info[arb_token]['networks']
                              if net in info[base_token]['networks']]

        ranges = info[arb_token]['swap_amount']
        swap_ranges = [f"{int((swap / 1000)):,}k" if swap > 1000 else swap for swap in ranges]

        message.append([base_token,
                        arb_token,
                        ", ".join(swap_ranges),
                        ", ".join(arb_token_networks),
                        info[arb_token]['min_arb'], ])

    columns = ["Base\nToken", "Arb\nToken", "Swap Amounts", "On networks", "Min. Arb."]

    print(tabulate(message, showindex=True, tablefmt="fancy_grid", headers=columns))
