from binance.spot import Spot
from binance.error import ClientError

from typing import (
    Tuple,
    List,
)

from src.projecthope.binance.datatypes import BinanceSwap
from src.projecthope.common.logger import log_error
from src.projecthope.common.variables import (
    BINANCE_KEY,
    BINANCE_SECRET,
)


# Initialise client class
client = Spot(key=BINANCE_KEY, secret=BINANCE_SECRET)


def trade_b_for_a(token_pair: Tuple[str, str], b_amounts: tuple,
                  book_limit: int = 100) -> List[BinanceSwap] or None:
    """
    Given pair 'AB', by selling amount 'B' calculate the received amount of 'A'
    Based on Binance's order books asks.

    :param token_pair: Token pair to trade, eg. ('ETH', 'USDT'), order matters!
    :param b_amounts: Amount range of token 'B' to swap in
    :param book_limit: Number of asks to check against in the order book
    :return: BinanceSwap dataclass: (swap_in, swap_out, fee)
    """
    token_a_name = token_pair[0].upper()
    token_b_name = token_pair[1].upper()
    pair = token_a_name + token_b_name
    try:
        order_book = client.depth(symbol=pair, limit=book_limit)
    except ClientError:
        log_error.warning(f"BinanceCEX API, ClientError: Invalid query for pair: {token_pair}, amounts: {b_amounts}")
        return None

    all_swaps = []
    for b_amount in range(*b_amounts):

        # Deduct binance 0.1% fee before trading
        fee = b_amount * (0.1 / 100.0)
        b_sold = b_amount
        b_amount -= fee

        a_bought = 0
        # asks are when they want to sell sth -> they are ASKING for the PRICE
        for item in order_book['asks']:
            # getting the amounts at price closest to the origin
            price = float(item[0])
            quantity = float(item[1])
            cost = price * quantity

            # If stables_amount less than ask total cost
            if b_amount >= cost:
                b_amount -= cost
                a_bought += quantity

            # otherwise we check how much of the current level we are filling
            else:
                last_quantity_bought = float(b_amount / price)
                a_bought += last_quantity_bought
                b_amount -= price * last_quantity_bought

                # No more stables left to trade
                break

        swap = BinanceSwap(token_b_name, b_sold, token_a_name, a_bought, (token_b_name, fee))
        # Append swap to list of all swaps
        all_swaps.append(swap)

    return all_swaps


def trade_a_for_b(token_pair: Tuple[str, str], a_amounts: tuple,
                  book_limit: int = 100) -> List[BinanceSwap] or None:
    """
    Given pair 'AB', by selling amount 'A' calculate the received amount of 'B'
    Based on Binance's order books asks.

    :param token_pair: Token pair to trade, eg. 'ETHUSDT', order matters!
    :param a_amounts: Amount range of token 'A' to swap in
    :param book_limit: Number of asks to check against in the order book
    :return: BinanceSwap dataclass: (swap_in, swap_out, fee)
    """
    token_a_name = token_pair[0].upper()
    token_b_name = token_pair[1].upper()
    pair = token_a_name + token_b_name
    try:
        order_book = client.depth(symbol=pair, limit=book_limit)
    except ClientError:
        log_error.warning(f"BinanceCEX API, ClientError: Invalid query for pair: {token_pair}, amount: {a_amounts}")
        return None

    all_swaps = []
    for a_amount in range(*a_amounts):

        # Deduct binance 0.1% fee before trading
        fee = a_amount * (0.1 / 100.0)
        total_a_sold = a_amount
        a_amount -= fee

        b_bought = 0
        a_sold = 0
        # bids are when they want to BUY sth -> they are BIDDING at the PRICE
        for item in order_book['bids']:

            price = float(item[0])
            quantity = float(item[1])
            cost = price * quantity

            if a_amount >= quantity:
                a_amount -= quantity
                a_sold += quantity
                b_bought += cost
            else:
                a_sold += a_amount
                b_bought += a_amount * price

                # No more tokens left to trade
                break

        swap = BinanceSwap(token_a_name, total_a_sold, token_b_name, b_bought, (token_a_name, fee))
        # Append swap to list of all swaps
        all_swaps.append(swap)

    return all_swaps
