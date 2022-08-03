from binance.spot import Spot

from src.projecthope.binance.datatypes import BinanceSwap
from src.projecthope.common.variables import (
    BINANCE_KEY,
    BINANCE_SECRET,
)


# Initialise client class
client = Spot(key=BINANCE_KEY, secret=BINANCE_SECRET)


def stables_to_tokens(token_pair: str, stables_amount: float, book_limit: int = 100) -> BinanceSwap:
    """
    Calculates received amount of 'B' from pair 'AB' based on binance's order book asks.

    :param token_pair: Token pair to trade, eg. 'ETHUSDT'
    :param stables_amount: Amount of stablescoins (B) to swap out
    :param book_limit: Number of asks to check againts in the order book
    :return: Amount of tokens bought (swap in)
    """
    order_book = client.depth(symbol=token_pair, limit=book_limit)

    # Deduct binance 0.1% fee before trading
    fee = stables_amount * (0.1 / 100.0)
    stables_sold = stables_amount
    stables_amount -= fee

    tokens_bought = 0
    # asks are when they want to sell sth -> they are ASKING for the PRICE
    for item in order_book['asks']:
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

    swap = BinanceSwap(stables_sold, tokens_bought, fee)

    return swap


def tokens_to_stables(token_pair: str, tokens_amount: float, book_limit: int = 100) -> BinanceSwap:
    """
    Calculates received amount of 'A' from pair 'AB' based on binance's order book asks.

    :param token_pair: Token pair to trade, eg. 'ETHUSDT'
    :param tokens_amount: Amount of tokens (A) to swap out
    :param book_limit: Number of asks to check againts in the order book
    :return: Amount of tokens bought (swap in)
    """
    order_book = client.depth(symbol=token_pair, limit=book_limit)

    # Deduct binance 0.1% fee before trading
    fee = tokens_amount * (0.1 / 100.0)
    total_tokens_sold = tokens_amount
    tokens_amount -= fee

    stables_bought = 0
    tokens_sold = 0
    # bids are when they want to BUY sth -> they are BIDDING at the PRICE
    for item in order_book['bids']:

        price = float(item[0])
        quantity = float(item[1])
        cost = price * quantity

        if tokens_amount >= quantity:
            tokens_amount -= quantity
            tokens_sold += quantity
            stables_bought += cost
        else:
            tokens_sold += tokens_amount
            stables_bought += tokens_amount * price

            # No more tokens left to trade
            break

    swap = BinanceSwap(total_tokens_sold, stables_bought, fee)

    return swap
