import asyncio
from datetime import datetime
from typing import List

from src.projecthope.datatypes import Swap
from src.projecthope.binance.api import (
    trade_a_for_b,
    trade_b_for_a,
)
from src.projecthope.one_inch.api import get_all_swapouts
from src.projecthope.common.message import telegram_send_message
from src.projecthope.common.helpers import parse_args_1inch
from src.projecthope.common.logger import log_arbitrage
from src.projecthope.common.variables import (
    time_format,
    base_tokens,
)


def max_swaps(swap_list: list, amounts: list | float) -> list[Swap]:
    """
    Analyses a list of swaps and returns the one with maximum amount in their respective range.

    :param swap_list: List containing swaps
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
            if highest_swap.from_token.name in base_tokens:
                stable_token_ratio = highest_swap.from_token.amount / highest_swap.to_token.amount
            elif highest_swap.to_token.name in base_tokens:
                stable_token_ratio = 1
            else:
                # If not swapping a stable coin - return highest_swap and don't compare with fees
                return highest_swap

            # Calculate token - fees difference
            difference_amount = (highest_amount - second_amount) * stable_token_ratio
            if difference_amount > highest_swap.cost['usdc_cost']:
                return highest_swap
            else:
                return second_swap

        else:
            return highest_swap

    swaps_amounts: list = []

    if type(amounts) is list or type(amounts) is tuple:
        for amount in amounts:
            # Create dict{swap_max_amount: swap_data} if swap not None
            all_swaps = {swap.to_token.amount: swap for swap in swap_list
                         if swap and swap.from_token.amount == amount}

            # Compare ethereum fees if all_swaps is not empty
            if len(all_swaps) > 0:
                max_swap = compare_swap_fees(all_swaps)
                swaps_amounts.append(max_swap)

    else:
        # Create dict{swap_max_amount: swap_data} if swap not None
        all_swaps = {swap.to_token.amount: swap for swap in swap_list if swap}

        # Compare ethereum fees if all_swaps is not empty
        if len(all_swaps) > 0:
            max_swap = compare_swap_fees(all_swaps)
            swaps_amounts.append(max_swap)

    return swaps_amounts


def compare_swaps(data: dict, base_token: str, arb_token: str) -> List[List[Swap]] | None:
    """
    Compares 1inch supported blockchains for arbitrage between 2 tokens.

    :param data: Input dictionary data
    :param base_token: Name of Base token being swapped in
    :param arb_token: Name of token being Arbitraged
    :return: List [max_Swap_ab, max_Swap_ba]
    """
    all_max_swaps: list = []

    # Query all networks on 1inch for Base->Arb swap outs for each range respectively
    args_ab, amounts = parse_args_1inch(data, base_token, arb_token)
    results = asyncio.run(get_all_swapouts(args_ab))

    # Get Binance CEX prices and a combine with all swaps
    binance_swaps_ab = trade_b_for_a(arb_token, base_token, amounts)
    swaps_ab = list(binance_swaps_ab) + list(results)

    # Get the maximum Swap for each range respectively
    max_swaps_ab = max_swaps(swaps_ab, amounts)

    # If no swaps returned - return an empty list
    if len(max_swaps_ab) == 0:
        return None

    for max_swap_ab in max_swaps_ab:
        # Save only 1 amount to query in Arb->Base
        max_amount_ab = max_swap_ab.to_token.amount

        # Query networks for Arb->Base swap out
        args_ba, _ = parse_args_1inch(data, arb_token, base_token, max_amount_ab)
        results = asyncio.run(get_all_swapouts(args_ba))

        # Get Binance CEX prices and a combine with all swaps
        binance_swaps_ba = trade_a_for_b(arb_token, base_token, [max_amount_ab])
        swaps_ba = list(binance_swaps_ba) + list(results)

        # Get the maximum swap out - should be list of only 1 item!
        max_swaps_ba = max_swaps(swaps_ba, max_amount_ab)

        if len(max_swaps_ba) > 0:
            max_swap_ba = max_swaps_ba[0]
            all_max_swaps.append([max_swap_ab, max_swap_ba])

    return all_max_swaps


def alert_arb(data: dict, base_token: str, arb_token: str) -> None:
    """
    Alerts via Telegram for arbitrage between 2 tokens.

    :param data: Input dictionary data
    :param base_token: Name of Base token being swapped in
    :param arb_token: Name of token being Arbitraged
    """
    # Get arbitrage data pairs for each amount swapped
    max_swap_pairs = compare_swaps(data, base_token, arb_token)

    # If max_swap_pairs is an empty list - return
    if not max_swap_pairs:
        return

    for max_swap_pair in max_swap_pairs:

        # Unpack values - A->B and B->A
        swap_ab, swap_ba = max_swap_pair

        chain1 = swap_ab.chain
        chain2 = swap_ba.chain

        # This may cause pairs to get 'skipped'!
        #if chain1 == chain2:
        #    break

        min_arb = data[arb_token]['min_arb']

        base_swap_in = swap_ab.from_token.amount
        base_swap_out = swap_ba.to_token.amount
        arb_swap_out = swap_ab.to_token.amount
        arb_swap_in = swap_ba.from_token.amount

        arbitrage = base_swap_out - base_swap_in

        if arbitrage >= min_arb:
            timestamp = datetime.now().astimezone().strftime(time_format)

            swap_1 = f"1) Sell {base_swap_in:,.0f} {base_token} for {arb_swap_out:,.4f} {arb_token} on {chain1}"
            swap_2 = f"2) Sell {arb_swap_in:,.4f} {arb_token} for {base_swap_out:,.0f} {base_token} on {chain2}"
            arb_string = f"{arbitrage:,.0f} {base_token}"

            if chain1.lower() == "binancecex":
                swap_1_link = f"<a href='https://www.binance.com/en/trade/{arb_token}_{base_token}'>{swap_1}</a>"
            else:
                swap_1_link = f"<a href='https://app.1inch.io/#/{swap_ab.id}/swap/{base_token}/{arb_token}'>" \
                              f"{swap_1}</a>"

            if chain2.lower() == "binancecex":
                swap_2_link = f"<a href='https://www.binance.com/en/trade/{arb_token}_{base_token}'>{swap_2}</a>"
            else:
                swap_2_link = f"<a href='https://app.1inch.io/#/{swap_ba.id}/swap/{arb_token}/{base_token}'>" \
                              f"{swap_2}</a>"

            telegram_msg = f"{timestamp}\n{swap_1_link}\n{swap_2_link}\n-->Arbitrage: {arb_string}"
            terminal_msg = f"{swap_1}\n{swap_2}\n-->Arbitrage: {arb_string}"

            # If any of the swaps are on Ethereum try to get gas cost in $
            if int(swap_ab.id) == 1 or int(swap_ba.id) == 1:
                if fee1 := swap_ab.cost.get('usdc_cost'):
                    fee_msg = f", eth fees ~${fee1:,.0f}"
                elif fee2 := swap_ba.cost.get('usdc_cost'):
                    fee_msg = f", eth fees ~${fee2:,.0f}"
                else:
                    fee_msg = f", eth fees n/a"
            else:
                fee_msg = f", eth fees n/a"

            telegram_msg += fee_msg
            terminal_msg += fee_msg

            # Send arbitrage to ALL alerts channel and log
            telegram_send_message(telegram_msg)
            log_arbitrage.info(terminal_msg)
            print(f"{terminal_msg}\n")
