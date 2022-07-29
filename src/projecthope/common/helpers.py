import time

from typing import (
    List,
    Dict,
)
from src.projecthope.common.variables import network_names


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


def parse_args(data: dict, base_token: str, arb_token: str, amounts: tuple = ()) -> List[list]:
    """
    Constructs a list of arguments for the 'get_swapout' function.

    :param data: Dictionary containing all token data
    :param base_token: Name of Base Token
    :param arb_token: Name of Arb Token
    :param amounts: Range list of amounts
    :return: Argument list of lists
    """

    if base_token not in data['base_tokens']:
        raise Exception(f"Token {base_token} not in 'base_tokens'")

    base_networks = data['base_tokens'][base_token]['networks']
    arb_networks = data['arb_tokens'][arb_token]['networks']

    if len(amounts) == 0:
        amounts = data['arb_tokens'][arb_token]['swap_amount']

    args_ab = []
    for network, data in arb_networks.items():
        for amount in range(*amounts):
            network_id = network_names[network]
            to_token = (data['address'], arb_token, data['decimals'])

            try:
                from_token = (base_networks[network]['address'], base_token, base_networks[network]['decimals'])
            except KeyError:
                continue

            args_ab.append([network_id, from_token, to_token, amount])

    return args_ab


def get_ttl_hash(seconds: int = 1200) -> int:
    """
    Function intended to be used with Python's functools.lru_cache only.
    Implements a length in which lru_cache will be used before clearing.

    :param seconds: How long to use cache for before clearing it up. Default is 20 minutes
    :return: Number of seconds
    """
    return round(time.time() / seconds)


def print_start_message(info: dict, base_token: str, timestamp: str) -> None:

    arb_tokens = [token for token in info['arb_tokens']]

    print(f"{timestamp} - Started screening the following configurations:")
    for i, arb_token in enumerate(arb_tokens):
        arb_token_networks = [net for net in info['arb_tokens'][arb_token]['networks']
                              if net in info['base_tokens'][base_token]['networks']]

        start, end, step = info['arb_tokens'][arb_token]['swap_amount']
        print(f"[{i+1}] {base_token} -> {arb_token}, range[{start:,}...{(start+step):,}...{end:,}] "
              f"on {arb_token_networks}")
