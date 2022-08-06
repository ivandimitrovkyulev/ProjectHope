from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import (
    List,
    Iterator,
)

from src.projecthope.one_inch.api import get_swapout
from src.projecthope.one_inch.datatypes import Swap
from src.projecthope.binance.api import (
    trade_a_for_b,
    trade_b_for_a,
)
from src.projecthope.common.message import telegram_send_message
from src.projecthope.common.helpers import parse_args_1inch
from src.projecthope.common.logger import log_arbitrage
from src.projecthope.common.variables import (
    time_format,
    stable_coins,
)


def max_swaps(results: Iterator, amounts: list | float) -> list[Swap]:
    """
    Analyses a list of swaps and returns the one with maximum amount in their respective range.

    :param results: Generator object containing swaps
    :param amounts: Range amounts for swaps
    :return: List of maximum swap_data for each swap amount respectively
    """
    def compare_swap_fees(swaps: dict) -> Swap:

        highest_amount: float = max(swaps)
        highest_swap: Swap = swaps[highest_amount]

        # If highest arb is on Ethereum check txn cost
        if int(highest_swap.id) == 1 and len(swaps) > 1:
            # Get second highest amount
            second_amount = sorted(swaps)[-2]
            second_swap = swaps[second_amount]

            # Calculate Stablecoin to Token ratio to adjust accordingly
            if highest_swap.from_token.name in stable_coins:
                stable_token_ratio = highest_swap.from_token.amount / highest_swap.to_token.amount
            elif highest_swap.to_token.name in stable_coins:
                stable_token_ratio = 1
            else:
                # If not swapping a stable coin - return highest_swap and don't compare with fees
                return highest_swap

            # Calculate token and fees difference
            difference_amount = (highest_amount - second_amount) * stable_token_ratio
            if difference_amount > highest_swap.gas_info['usdc_cost']:
                return highest_swap
            else:
                return second_swap

        else:
            return highest_swap

    results_list: list = list(results)
    swaps_amounts: list = []

    if type(amounts) is list:
        for amount in amounts:
            # Create dict{swap_max_amount: swap_data} if swap not None
            all_swaps = {swap.to_token.amount: swap for swap in results_list
                         if swap and swap.from_token.amount == amount}

            # Compare ethereum fees
            max_swap = compare_swap_fees(all_swaps)
            swaps_amounts.append(max_swap)

    else:
        # Create dict{swap_max_amount: swap_data} if swap not None
        all_swaps = {swap.to_token.amount: swap for swap in results_list if swap}

        # Compare ethereum fees
        max_swap = compare_swap_fees(all_swaps)
        swaps_amounts.append(max_swap)

    return swaps_amounts


def compare_swaps(data: dict, base_token: str, arb_token: str) -> List[List[Swap]]:
    """
    Compares 1inch supported blockchains for arbitrage between 2 tokens.

    :param data: Input dictionary data
    :param base_token: Name of Base token being swapped in
    :param arb_token: Name of token being Arbitraged
    :return: List [max_Swap_ab, max_Swap_ba]
    """
    # Query all networks for Base->Arb swap outs for each range respectively
    args_ab, ranges = parse_args_1inch(data, base_token, arb_token)
    with ThreadPoolExecutor(max_workers=len(args_ab)) as pool:
        swaps_ab = pool.map(lambda p: get_swapout(*p), args_ab, timeout=10)

    # Get the maximum Swap for each range respectively
    max_swaps_ab = max_swaps(swaps_ab, ranges)

    all_max_swaps: list = []
    for max_swap_ab in max_swaps_ab:
        # Save only 1 amount to query in Arb->Base
        max_amount_ab = max_swap_ab.to_token.amount

        # Query networks for Arb->Base swap out
        args_ba, _ = parse_args_1inch(data, arb_token, base_token, max_amount_ab)
        with ThreadPoolExecutor(max_workers=len(args_ba)) as pool:
            swaps_ba = pool.map(lambda p: get_swapout(*p), args_ba, timeout=10)

        # Get the maximum swap out - should be list of only 1 item!
        max_swap_ba = max_swaps(swaps_ba, max_amount_ab)[0]
        all_max_swaps.append([max_swap_ab, max_swap_ba])

    return all_max_swaps


def alert_arb(data: dict, base_token: str, arb_token: str) -> None:
    """
    Alerts via Telegram for arbitrage between 2 tokens.

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
            if fee1 := swap_ab.gas_info.get('usdc_cost'):
                fee_msg = f", swap+bridge fees ~${fee1:,.0f}"
            elif fee2 := swap_ba.gas_info.get('usdc_cost'):
                fee_msg = f", swap+bridge fees ~${fee2:,.0f}"
            else:
                fee_msg = f", swap+bridge fees n/a"

            telegram_msg += fee_msg
            terminal_msg += fee_msg

        # Send arbitrage to ALL alerts channel and log
        telegram_send_message(telegram_msg)
        log_arbitrage.info(terminal_msg)
        print(f"{terminal_msg}\n")
