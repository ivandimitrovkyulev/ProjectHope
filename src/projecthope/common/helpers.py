from typing import (
    List,
    Iterator,
)

from src.projecthope.common.variables import network_names


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


def max_swap(results: Iterator) -> tuple:
    """
    Analyses a list of swaps and returns the one with maximum amount.

    :param results: Generator object containing swaps
    :return: Tuple (dictionary, max_amount)
    """

    # Create dict and hash swap: all_data
    swaps = {res['to_token']['amount']: res for res in results if res}

    max_amount = max(swaps)
    dictionary = swaps[max_amount]

    return dictionary, max_amount
