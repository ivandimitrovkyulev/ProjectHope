from urllib import response
from binance.spot import Spot

from binance.spot.bswap import bswap_request_quote

client = Spot()

# api key/secret are required for user data endpoints
client = Spot(key='xxxx',
              secret='xxx')

limit = 1000  # limit of bid/ask pairs from origin

trading_pair = 'ETHUSDT'


def stables_to_tokens(limit, token_pair, stables_amount):
    total_bought = 0
    order_book = client.depth(token_pair, limit=limit)

    for item in order_book['asks']:  # asks are when they want to sell sth -> they are ASKING for the PRICE
        # getting the amounts at price closest to the origin
        price = float(item[0])
        quantity = float(item[1])
        print(f'p*q {price * quantity}')

        # check if our stables can fill the closest price level before moving to the next level
        # if ethereum is 1500 and there is 1 ethereum sitting at 1500
        # and a second ethereum sitting at 1550, we buy one at 1500, bump the price to 1550, if we buy more its at 1550

        # we check if we can clear the level with our size, if we can we do so and move to the next price level,
        if stables_amount >= price * quantity:
            stables_amount -= price * quantity
            total_bought += quantity

        # otherwise we check how much of the current level we are filling
        else:
            last_quantity_bought = float(stables_amount / price)
            total_bought += last_quantity_bought
            stables_amount -= price * last_quantity_bought
            print('===========================')
            print(f'last price {price}')
            print(f'last quantity bought {last_quantity_bought}')
            break
    print(f'bought so far {total_bought}')
    print(f'usdt remaining {stables_amount}')

    bought_after_fees = total_bought * (1 - 0.001)
    print(stables_amount == 0)
    print(f'bought after fees {bought_after_fees}')

    return bought_after_fees


# print(stables_to_tokens(limit, trading_pair, 500000))


def tokens_to_stables(limit, token_pair, coin_amount):
    coins_left_to_sell = coin_amount
    total_coins_sold = 0
    total_revenue = 0
    order_book = client.depth(token_pair, limit=limit)

    for item in order_book['bids']:  # bids are when they want to BUY sth -> they are BIDDING at the PRICE

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
            print(total_coins_sold == coin_amount)
            total_revenue += last_quantity_sold_to_stalbes
            break

    stables_after_fees = total_revenue * (1 - 0.001)

    return stables_after_fees

# print(tokens_to_stables(limit, trading_pair, 5))
