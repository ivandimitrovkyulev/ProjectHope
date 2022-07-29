import os

from functools import lru_cache

from dotenv import load_dotenv
from typing import Any

from web3.contract import Contract
from web3.gas_strategies.time_based import construct_time_based_gas_price_strategy
from web3 import (
    Web3,
    middleware,
)
from src.projecthope.common.logger import log_error


class EvmContract:
    """EVM compatible smart contract class."""

    def __init__(self, project_id: str = ""):
        """
        Set up Infura as node provider.

        :param project_id: Infura Project ID. If not provided it will look for a 'PROJECT_ID' in a .env file.
        """
        if project_id == "":
            load_dotenv()
            self.infura_url = f"https://mainnet.infura.io/v3/{os.getenv('PROJECT_ID')}"
        else:
            self.infura_url = f"https://mainnet.infura.io/v3/{project_id}"

        self.w3 = Web3(Web3.HTTPProvider(self.infura_url))

        # Construct and set gas strategy
        gas_str = construct_time_based_gas_price_strategy(max_wait_seconds=30, sample_size=60,
                                                          probability=98, weighted=False)
        self.w3.eth.set_gas_price_strategy(gas_str)

        # Set up various caches
        self.w3.middleware_onion.add(middleware.latest_block_based_cache_middleware)
        self.w3.middleware_onion.add(middleware.simple_cache_middleware)

    @lru_cache()
    def eth_gas_price(self, ttl_hash: int = None) -> int or None:
        """
        Get a quote for Eth gas price for a transaction to get mined.
        Set to 30secs max_wait, 60 sample_size, 98 probability & weighted False.
        Use 'change_gas_strategy' method to implement a different strategy.
        Pass get_ttl_hash() to cache for a period of time.
        """

        counter = 1
        while True:
            try:
                gas_price = self.w3.eth.generateGasPrice()
                return gas_price
            except IndexError:
                log_error.warning(f"Could not query gas price from Web3. Attempt: {counter}")
                counter += 1
                if counter > 3:
                    return None

    def change_gas_strategy(self, max_wait: int, sample_size: int = 60,
                            probability: int = 98, weighted: bool = False) -> int:
        """
        Construct a strategy that will estimate Eth gas price for a transaction to get mined.

        :param max_wait: The desired maxiumum number of seconds the transaction should take get mined
        :param sample_size: The number of recent blocks to sample tand calculate from
        :param probability: What's the probability the transaction will get mined
        :param weighted: Block time will be weighted towards more recently mined blocks
        :return: Gas price for a transaction to get mined
        """
        # Construct a strategy
        strategy = construct_time_based_gas_price_strategy(
            max_wait_seconds=max_wait,
            sample_size=sample_size,
            probability=probability,
            weighted=weighted
        )
        self.w3.eth.set_gas_price_strategy(strategy)

        gas_price = self.w3.eth.generate_gas_price()

        return gas_price

    @staticmethod
    def run_contract_function(contract_instance: Contract, func_name: str, func_args: tuple = ()) -> Any:
        """
        Run a smart contract function by name for a constructed contract.

        :param contract_instance: Web3 Contract Instance
        :param func_name: Name of function to run
        :param func_args: List of arguments to pass to function
        :return: Function output
        """
        # In case function take only one argument
        func_args = (func_args,)

        function_name = str(func_name)

        contract_func = contract_instance.functions[function_name]
        result = contract_func(*func_args).call()

        return result

    def create_contract(self, address: str, abi: str) -> Contract:
        """
        Creates a Web3 Contract Instance.
        Once instantiated, you can read data and execute transactions.

        :param address: Contract's address
        :param abi: Contract's ABI
        :return: Web3 Contract instance
        """

        # Convert transaction address to check-sum address
        checksum_address = Web3.toChecksumAddress(address)

        # Create contract instance
        contract = self.w3.eth.contract(address=checksum_address, abi=abi)

        return contract
