import ast
import ssl
import json
from typing import List

from requests.exceptions import ReadTimeout
from websocket import WebSocketApp

from src.projecthope.datatypes import (
    Token,
    Swap,
)
from src.projecthope.common.logger import log_error
from src.projecthope.common.variables import (
    network_names,
    memcache,
    http_session,
)


class BinanceDepthSocket:

    def __init__(self, symbols: List[str], level: int = 20, update_speed: int = 1000):
        """
        :param symbols: List of trading pairs, eg. ['ETHUSDT', 'CVXUSDT']
        :param level: Binance socket depth level, eg. 5, 10, 20
        :param update_speed: Real time update speed, 1000ms or 100ms
        """
        self.symbols = [f"{symbol.lower()}@depth{level}@{update_speed}ms" for symbol in symbols]
        self._last_update_id = {symbol.upper(): 0 for symbol in symbols}

        self.url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(self.symbols)}"
        self.socket = WebSocketApp(self.url, on_open=self.on_open, on_message=self.on_message,
                                   on_error=self.on_error, on_close=self.on_close)

    @staticmethod
    def get_pair_depth(trading_symbol: str, limit: int = 1000, timeout: int = 5) -> dict | None:
        """
        Get the order book depth for a given trading pair.

        :param trading_symbol: Trading pair, eg. 'ETHUSDT'
        :param limit: Depth limit
        :param timeout: Maximum wait time for request
        :returns: Dictionary of response data
        """
        url = f"https://api.binance.us/api/v3/depth?symbol={trading_symbol.upper()}&limit={limit}"
        try:
            response = http_session.get(url, timeout=timeout)
        except ConnectionError or ReadTimeout as e:
            log_error.warning(f"'ConnectionError' {url} - {e}")
            return None

        try:
            data = json.loads(response.content)

            if response.status_code != 200:
                log_error.critical(f"'get_pair_depth' error - {data} - {url}")
                return None

            return data

        except Exception as e:
            log_error.warning(f"Error getting 'lastUpdateId' from {url} - {e}")

    @staticmethod
    def on_error(socket, error):
        """Websocket on_error method handler."""
        message = f">>> Error: {error}, {socket.url}"
        log_error.warning(message)
        print(message)

    @staticmethod
    def on_close(socket, close_status_code, close_msg):
        """Websocket on_close method handler."""
        message = f">>> Closed connection: {socket.url}. " \
                  f"Status code: {close_status_code}. " \
                  f"Closing msg: {close_msg}."
        log_error.warning(message)
        print(message)

    @staticmethod
    def on_open(socket):
        """Websocket on_open method handler."""
        message = f">>> Opened connection: {socket.url}"
        print(message)
        print(f"Started listening to streams...")

    def on_message(self, socket, message):
        """Websocket on_message method handler."""
        data = ast.literal_eval(message)  # Convert data into a dict
        try:
            stream_name: str = data['stream'].split('@')[0].upper()  # Get the trading pair part only, eg. 'ETHUSDT'
            stream_data = data['data']
            update_id = data['data']['lastUpdateId']

            if update_id >= self._last_update_id[stream_name]:
                memcache.set(key=stream_name, value=stream_data, expire=30)

            self._last_update_id[stream_name] = update_id  # Save last id for each stream in dict

        except Exception as e:
            log_error.warning(f"Error getting data from websocket stream - {socket} - {e}")

    def run_forever(self):
        """Start screening for messages from websocket and handle with on_message method"""
        self.socket.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})


def trade_b_for_a(token_a: str, token_b: str, b_amounts: list, asks: list) -> List[Swap]:
    """
    Given pair 'AB', by selling amount 'B', calculate the received amount of 'A'
    Based on Binance's order book asks. Returns none if trading pair not available.

    :param token_a: Name of Token A
    :param token_b: Name of Token B
    :param b_amounts: List of amounts of token 'B' to swap in
    :param asks: List of order book asks
    :return: List of Swap dataclass: (chain, id, cost, from_token, to_token, remainder)
    """
    b_amounts = list(b_amounts)

    network_name: str = "BinanceCEX"
    network_id: str = network_names[network_name]

    all_swaps: list = []
    for b_amount in b_amounts:

        # Deduct binance 0.1% fee before trading
        fee = b_amount * (0.1 / 100.0)
        swap_cost = {"exchange_fee": fee}
        b_sold = b_amount
        b_amount -= fee

        a_bought = 0
        # asks are when they want to sell sth -> they are ASKING for the PRICE
        for item in asks:
            # getting the amounts at price closest to the origin
            price = float(item[0])
            quantity = float(item[1])
            cost = price * quantity

            # If b_amount less than ask total cost
            if b_amount >= cost:
                a_bought += quantity
                b_amount -= cost

            # otherwise we check how much of the current level we are filling
            else:
                last_quantity_bought = float(b_amount / price)
                a_bought += last_quantity_bought
                b_amount -= price * last_quantity_bought

                # No more stables left to trade
                break

        # Deduct b_amount, if any, from total sold
        remainder = b_amount
        a_bought -= remainder
        b_sold -= remainder

        from_token = Token(token_b, b_sold)
        to_token = Token(token_a, a_bought)

        binance_swap = Swap(network_name, network_id, swap_cost, from_token, to_token, remainder)

        # Append swap to list of all swaps
        all_swaps.append(binance_swap)

    return all_swaps


def trade_a_for_b(token_a: str, token_b: str, a_amounts: list, bids: list) -> List[Swap]:
    """
    Given pair 'AB', by selling amount 'A', calculate the received amount of 'B'
    Based on Binance's order book bids. Returns none if trading pair not available.

    :param token_a: Name of Token A
    :param token_b: Name of Token B
    :param a_amounts: List of amounts of token 'A' to swap in
    :param bids: List of order book bids
    :return: List of Swap dataclass: (chain, id, cost, from_token, to_token, remainder)
    """
    a_amounts = list(a_amounts)

    network_name: str = "BinanceCEX"
    network_id: str = network_names[network_name]

    all_swaps: list = []
    for a_amount in a_amounts:

        # Deduct binance 0.1% fee before trading
        fee = a_amount * (0.1 / 100.0)
        swap_cost = {"exchange_fee": fee}
        total_a_sold = a_amount
        a_amount -= fee

        b_bought = 0
        a_sold = 0
        # bids are when they want to BUY sth -> they are BIDDING at the PRICE
        for item in bids:

            price = float(item[0])
            quantity = float(item[1])
            cost = price * quantity

            if a_amount >= quantity:
                a_amount -= quantity
                a_sold += quantity
                b_bought += cost
            else:
                last_quantity_sold = float(a_amount * price)
                a_sold += a_amount
                b_bought += last_quantity_sold

                # No more tokens left to trade
                break

        # Deduct a_amount, if any, from total sold
        remainder = (total_a_sold - fee) - a_sold

        from_token = Token(token_a, total_a_sold)
        to_token = Token(token_b, b_bought)

        binance_swap = Swap(network_name, network_id, swap_cost, from_token, to_token, remainder)

        # Append swap to list of all swaps
        all_swaps.append(binance_swap)

    return all_swaps


def start_binance_streams(trading_pairs):
    # Initialise BinanceDepthSocket with trading pairs
    binance_socket = BinanceDepthSocket(trading_pairs)
    binance_socket.run_forever()
