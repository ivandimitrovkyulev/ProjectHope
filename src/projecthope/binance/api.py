from pprint import pprint
from functools import lru_cache

from binance.spot import Spot

from src.projecthope.common.helpers import get_ttl_hash
from src.projecthope.common.variables import (
    BINANCE_KEY,
    BINANCE_SECRET,
)


client = Spot(key=BINANCE_KEY, secret=BINANCE_SECRET)


def stables_to_tokens(token_pair: str, stables_amount: float, book_limit: int = 100) -> float:
    """
    Calculates received amount of 'B' from pair 'AB' based on binance's order book asks.

    :param token_pair: Token pair to trade, eg. 'ETHUSDT'
    :param stables_amount: Amount of stablescoins (B) to swap out
    :param book_limit: Number of asks to check againts in the order book
    :return: Amount of tokens bought (swap in)
    """
    order_book = client.depth(token_pair, limit=book_limit)

    # Deduct binance 0.1% fee before trading
    fee = stables_amount * (0.1 / 100.0)
    stables_amount -= fee

    tokens_bought = 0
    # asks are when they want to sell sth -> they are ASKING for the PRICE
    for i, item in enumerate(order_book['asks']):
        # getting the amounts at price closest to the origin
        price = float(item[0])
        quantity = float(item[1])
        cost = price * quantity

        # If stables_amount less than ask total cost
        if stables_amount >= cost:
            stables_amount -= cost
            tokens_bought += quantity

        # otherwise we check how much of the current level we are filling
        else:
            last_quantity_bought = float(stables_amount / price)
            tokens_bought += last_quantity_bought
            stables_amount -= price * last_quantity_bought

            # No more stables left to trade
            break

    return tokens_bought


def tokens_to_stables(token_pair: str, tokens_amount: float, book_limit: int = 100) -> float:
    """
    Calculates received amount of 'A' from pair 'AB' based on binance's order book asks.

    :param token_pair: Token pair to trade, eg. 'ETHUSDT'
    :param tokens_amount: Amount of tokens (A) to swap out
    :param book_limit: Number of asks to check againts in the order book
    :return: Amount of tokens bought (swap in)
    """
    coins_left_to_sell = tokens_amount
    total_coins_sold = 0
    total_revenue = 0
    order_book = client.depth(token_pair, limit=book_limit)

    # bids are when they want to BUY sth -> they are BIDDING at the PRICE
    for item in order_book['bids']:

        price = float(item[0])
        quantity = float(item[1])
        print(f'p*q {price * quantity}')

        if coins_left_to_sell >= quantity:
            coins_left_to_sell -= quantity
            total_coins_sold += quantity
            total_revenue += price * quantity
        else:
            last_quantity_sold_to_stalbes = coins_left_to_sell * price
            total_coins_sold += coins_left_to_sell
            print(total_coins_sold == tokens_amount)
            total_revenue += last_quantity_sold_to_stalbes
            break

    stables_after_fees = total_revenue * (1 - 0.001)

    return stables_after_fees


print(tokens_to_stables("ETHUSDT", 500))
