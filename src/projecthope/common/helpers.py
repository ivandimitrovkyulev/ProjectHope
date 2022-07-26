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


def parse_args(data: dict, token_name_a: str, token_name_b: str, amount: float = 0) -> List[list]:
    """
    Parses arguments for swap out function.

    :param data: Dictionary containing all token data
    :param token_name_a: Name of Token A
    :param token_name_b: Name of Token B
    :param amount: Amount to swap
    :return: Argument list of lists
    """

    if token_name_a in data['base_tokens']:
        a_networks = data['base_tokens'][token_name_a]['networks']
        b_networks = data['arb_tokens'][token_name_b]['networks']
        if amount == 0:
            amount = data['arb_tokens'][token_name_b]['swap_amount']

    else:
        a_networks = data['arb_tokens'][token_name_a]['networks']
        b_networks = data['base_tokens'][token_name_b]['networks']

    args_ab = []
    for network, data in b_networks.items():
        network_id = network_names[network]
        to_token = (data['address'], token_name_b, data['decimals'])

        try:
            from_token = (a_networks[network]['address'], token_name_a, a_networks[network]['decimals'])
        except KeyError:
            continue

        args_ab.append([network_id, from_token, to_token, amount])

    return args_ab
