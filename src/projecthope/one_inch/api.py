import ast
import json

from json.decoder import JSONDecodeError
from aiohttp import (
    ClientSession,
    ClientConnectorSSLError,
)

from src.projecthope.blockchain.evm import EvmContract
from src.projecthope.datatypes import (
    Token,
    Swap,
)
from src.projecthope.common.decorators import count_func_calls
from src.projecthope.common.logger import log_error
from src.projecthope.common.variables import (
    network_ids,
    memcache,
    timeout_class,
)


# Create an EVM contract class
contract = EvmContract()


def get_ethusdt_price() -> float | None:
    """
    Get the ETH/USDT price from Binance 'ETHUSDT' WebSocket stream.
    """

    order_book: bytes = memcache.get(key="ETHUSDT", default=None)
    if not order_book:
        return None

    order_book: dict = ast.literal_eval(order_book.decode("utf-8"))  # Decode bytes string into a dictionary
    try:
        eth_usdt_price = float(order_book['bids'][0][0])

        return eth_usdt_price

    except Exception as e:
        log_error.error(f"'get_ethusd_price' Error - can not query ETH/USDT price. {e}")

        return None


def get_eth_fees(cost: dict, gas_amount: int, bridge_fees_eth: float = 0.005510) -> dict:
    """
    Calculates fees on Ethereum in USDT. Adds 'gas_price' and 'usdc_cost' to cost dictionary.
    Queries Binance WebSocket for ETH/USDT info then caches it.

    :param cost: Dictionary with cost data to transform
    :param gas_amount: Gas amount for transaction to be executed
    :param bridge_fees_eth: Eth bridge fees, default 0.005510 ETH
    :return: Dictionary with updated cost data
    """

    # Get ETH gas price from Web3. Result is cached for 1200 secs before querying again
    gas_price = contract.eth_gas_price()
    if gas_price:
        cost['gas_price'] = gas_price

    ethusdt_price = get_ethusdt_price()
    if ethusdt_price:
        gas_cost_usdc = ((gas_amount * gas_price) / 10 ** 18) * ethusdt_price
        bridge_cost_usdc = bridge_fees_eth * ethusdt_price

        cost['usdc_cost'] = gas_cost_usdc + bridge_cost_usdc

    return cost


@count_func_calls
async def get_swapout(network_id: str, from_token: tuple, to_token: tuple,
                      amount_float: float, timeout: int = 3, include_fees: bool = True) -> Swap | None:
    """
    Queries https://app.1inch.io for swap_out amount between 2 tokens on a given network.

    :param network_id: Network id
    :param from_token: From token (swap in). Tuple format (address, name, decimals)
    :param to_token: To token (swap out). Tuple format (address, name, decimals)
    :param amount_float: Amount to swap in
    :param timeout: Maximum time to wait for request
    :param include_fees: Include Eth fees?
    :return: Swap dataclass: (network_name, network_id, cost, from_token, to_token)
    """
    api = f"https://api.1inch.io/v4.0/{network_id}/quote"

    from_token_addr = str(from_token[0])
    from_token_name = from_token[1]
    from_token_decimal = int(from_token[2])

    to_token_addr = str(to_token[0])
    to_token_name = to_token[1]
    to_token_decimal = int(to_token[2])

    network_name = network_ids[str(network_id)]

    amount = int(amount_float * (10 ** from_token_decimal))

    payload = {"fromTokenAddress": from_token_addr,
               "toTokenAddress": to_token_addr,
               "amount": str(amount)}

    async with ClientSession(timeout=timeout_class) as async_http_session:
        try:
            async with async_http_session.get(api, ssl=False, params=payload, timeout=timeout) as response:

                try:
                    data = json.loads(await response.text())
                except JSONDecodeError as e:
                    log_error.warning(f"'JSONError' - {response.status} - {e} - {response.url}")
                    return None

                if response.status != 200:
                    log_error.warning(f"'ResponseError' {response.status}, {data['error']} - "
                                      f"{network_name}, {amount_float} {from_token_name} -> {to_token_name}")
                    return None

        except Exception as e:
            log_error.warning(f"'async_http_session.get' Error - {e} - Unable to fetch amount for "
                              f"{network_name}, {from_token_name} -> {to_token_name}")
            return None

    swap_out = float(data['toTokenAmount'])
    swap_out_float = swap_out / (10 ** to_token_decimal)

    gas_amount = int(data['estimatedGas'])
    cost = {"gas_amount": gas_amount}

    # Calculate fees on Ethereum only and add to cost dictionary
    if include_fees and int(network_id) == 1:
        get_eth_fees(cost, gas_amount)

    from_token = Token(from_token_name, amount_float, from_token_decimal)
    to_token = Token(to_token_name, swap_out_float, to_token_decimal)

    inch_swap = Swap(network_name, network_id, cost, from_token, to_token)

    return inch_swap
