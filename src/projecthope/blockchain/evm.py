import os
import json
import requests

from dotenv import load_dotenv
from datetime import datetime
from typing import (
    List,
    Dict,
)
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError
from json.decoder import JSONDecodeError

from web3 import Web3
from web3.contract import Contract
from web3.gas_strategies.time_based import medium_gas_price_strategy

from src.projecthope.common.logger import (
    log_txns,
    log_error,
)
from src.projecthope.common.variables import time_format
from src.projecthope.common.message import telegram_send_message


class EvmContract:
    """
    EVM contract and transaction screener class.
    """
    def __init__(self, name: str, bridge_address: str):

        networks = {
            'arbitrum': ['https://api.arbiscan.io', 'https://arbiscan.io'],
            'optimism': ['https://api-optimistic.etherscan.io', 'https://optimistic.etherscan.io'],
            'polygon': ['https://api.polygonscan.com', 'https://polygonscan.com'],
            'gnosis': ['https://blockscout.com/xdai/mainnet/api', 'https://blockscout.com/xdai/mainnet'],
        }
        if name.lower() not in networks:
            raise ValueError(f"No such network. Choose from: {networks}")

        self.name = name.lower()
        self.bridge_address = bridge_address.lower()
        self.network = networks[self.name][1]
        self.api = networks[self.name][0]
        self.session = requests.Session()

        self.node_api_key = os.getenv(f"{self.name.upper()}_API_KEY")

        self.abi_endpoint = f"{self.api}/api?module=contract&action=getabi"

        self.txn_url = f"{self.api}/api?module=account&action=txlist"

        self.erc20_url = f"{self.api}/api?module=account&action=tokentx"

        # Create contract instance
        try:
            abi = self.get_contract_abi(self.bridge_address)
            self.contract_instance = self.create_contract(self.bridge_address, abi)
        except Exception as e:
            self.contract_instance = None
            message = f"Contract instance not created for {self.name}, {self.bridge_address}. {e}"
            log_error.warning(message)
            print(message)

    @staticmethod
    def gas_price():

        load_dotenv()
        infura_url = f"https://mainnet.infura.io/v3/{os.getenv('PROJECT_ID')}"
        w3 = Web3(Web3.HTTPProvider(infura_url))

        w3.eth.set_gas_price_strategy(medium_gas_price_strategy)

        gas_price = w3.eth.generate_gas_price()

        return gas_price

    @staticmethod
    def run_contract_function(contract_instance: Contract, function_name: str, args_list: list):

        function_name = str(function_name)

        contract_func = contract_instance.functions[function_name]
        result = contract_func(*args_list).call()

        return result

    def get_contract_abi(self, address: str, timeout: float = 3) -> str or None:
        """
        Queries contract's ABI using an API.

        :param address: Contract's address
        :param timeout: Max number of secs to wait for request
        :return: Contract's ABI
        """
        # Contract's ABI
        payload = {'address': address, 'apikey': self.node_api_key}

        try:
            url = requests.get(self.abi_endpoint, params=payload, timeout=timeout)
        except ConnectionError:
            log_error.warning(f"'ConnectionError': Unable to fetch data for {self.abi_endpoint}")
            return None

        # Convert Contract's ABI text to JSON file
        abi = json.loads(url.text)

        return abi['result']

    @staticmethod
    def create_contract(address: str, abi: str) -> Contract:
        """
        Creates a contract instance.
        Once you instantiated, you can read data and execute transactions.

        :param address: Contract's address
        :param abi: Contract's ABI
        :return: web3 Contract instance
        """
        load_dotenv()
        infura_url = f"https://mainnet.infura.io/v3/{os.getenv('PROJECT_ID')}"
        w3 = Web3(Web3.HTTPProvider(infura_url))

        # Convert transaction address to check-sum address
        checksum_address = Web3.toChecksumAddress(address)

        # Create contract instance
        contract = w3.eth.contract(address=checksum_address, abi=abi)

        return contract

    @staticmethod
    def run_contract(contract: Contract, txn_input: str) -> dict:
        """
        Runs an EVM contract given a transaction input.

        :param contract: web3 Contract instance
        :param txn_input: Transaction input field
        :return: Dictionary of transaction output
        """

        # Get transaction output from contract instance
        _, func_params = contract.decode_function_input(txn_input)

        return func_params

    @staticmethod
    def compare_lists(new_list: List[Dict[str, str]], old_list: List[Dict[str, str]],
                      keyword: str = 'hash') -> list:
        """
        Compares two lists of dictionaries.

        :param new_list: New list
        :param old_list: Old list
        :param keyword: Keyword to compare with
        :return: List of dictionaries that are in new list but not in old list
        """

        try:
            hashes = [txn[keyword] for txn in old_list]

            list_diff = [txn for txn in new_list if txn[keyword] not in hashes]

            return list_diff

        except TypeError:
            return []

    def get_last_txns(self, txn_count: int = 1, bridge_address: str = "",
                      max_retries: int = 3, timeout: float = 3) -> List or None:
        """
        Gets the last transactions from a specified contract address.

        :param txn_count: Number of transactions to return
        :param bridge_address: Contract address
        :param max_retries: Max number of times to repeat GET request
        :param timeout: Max number of secs to wait for request
        :return: A list of transaction dictionaries
        """
        if int(txn_count) < 1:
            txn_count = 1

        if bridge_address == "":
            bridge_address = self.bridge_address

        self.session.mount("https://", HTTPAdapter(max_retries=max_retries))

        if self.name.lower() == 'gnosis':
            payload = {"address": bridge_address}
        else:
            payload = {"address": bridge_address, "startblock": "0", "endblock": "99999999", "sort": "desc",
                       "apikey": self.node_api_key}

        try:
            response = self.session.get(self.txn_url, params=payload, timeout=timeout)
        except ConnectionError:
            log_error.warning(f"'ConnectionError': Unable to fetch transaction data for {self.name}")
            return []

        try:
            txn_dict = response.json()
        except JSONDecodeError:
            log_error.warning(f"'JSONError' {response.status_code} - {response.url}")
            return []

        # Get a list with number of txns
        try:
            last_transactions = txn_dict['result'][:txn_count]
        except TypeError:
            log_error.warning(f"'ResponseError' {response.status_code} - {response.url}")
            return []

        return last_transactions

    def get_last_erc20_txns(self, token_address: str, txn_count: int = 1, bridge_address: str = "",
                            filter_by: tuple = (), max_retries: int = 3, timeout: float = 3) -> List or None:
        """
        Gets the latest Token transactions from a specific smart contract address.

        :param token_address: Address of Token contract of interest
        :param txn_count: Number of transactions to return
        :param bridge_address: Address of the smart contract interacting with Token
        :param filter_by: Filter transactions by field and value, eg. ('to', '0x000...000')
        :param max_retries: Max number of times to repeat GET request
        :param timeout: Max number of secs to wait for request
        :return: A list of transaction dictionaries
        """
        if int(txn_count) < 1:
            txn_count = 1

        token_address = token_address.lower()

        if bridge_address == "":
            bridge_address = self.bridge_address

        self.session.mount("https://", HTTPAdapter(max_retries=max_retries))

        if self.name.lower() == 'gnosis':
            payload = {"address": bridge_address}
        else:
            payload = {"contractaddress": token_address, "address": bridge_address, "page": "1",
                       "offset": "100", "sort": "desc", "apikey": self.node_api_key}

        try:
            response = self.session.get(self.erc20_url, params=payload, timeout=timeout)
        except ConnectionError:
            log_error.warning(f"'ConnectionError': Unable to fetch transaction data for {self.name}")
            return []

        try:
            txn_dict = response.json()
        except JSONDecodeError:
            log_error.warning(f"'JSONError' {response.status_code} - {response.url}")
            return []

        # Get a list with number of txns
        try:
            last_txns = txn_dict['result'][:txn_count]
        except TypeError:
            log_error.warning(f"'ResponseError' {response.status_code} - {response.url}")
            return []

        try:
            if len(filter_by) != 2:
                temp = {t_dict['hash']: t_dict for t_dict in last_txns}
            else:
                temp = {t_dict['hash']: t_dict for t_dict in last_txns
                        if t_dict[filter_by[0]] == filter_by[1]}

            last_txns_cleaned = [txn for txn in temp.values()]

            return last_txns_cleaned

        except KeyError:
            raise KeyError(f"Error in f'get_last_erc20_txns': Can not filter by {filter_by} for {self.name}")

    def alert_checked_txns(self, txns: list, min_txn_amount: float,
                           token_decimals: int, token_name: str) -> None:
        """
        Checks transaction list and alerts if new transaction is important.

        :param txns: List of transactions
        :param min_txn_amount: Minimum transfer amount to alert for
        :param token_decimals: Number of decimals for this coin being swapped
        :param token_name: Name of token
        :return: None
        """
        if self.contract_instance:
            for txn in txns:
                # Simulate contract execution and calculate amount
                contract_output = EvmContract.run_contract(self.contract_instance, txn['input'])
                txn_amount = float(contract_output['amount']) / (10 ** token_decimals)

                rounding = int(token_decimals) // 6
                txn_amount = round(txn_amount, rounding)

                # Construct messages
                time_stamp = datetime.now().astimezone().strftime(time_format)
                message = f"{time_stamp}\n" \
                          f"{txn_amount:,} {token_name} swapped on " \
                          f"<a href='{self.network}/tx/{txn['hash']}'>{self.name}</a>"

                terminal_msg = f"{txn['hash']}, {txn_amount:,} {token_name} swapped on {self.name}"

                # Log all transactions
                log_txns.info(terminal_msg)

                if txn_amount >= min_txn_amount:
                    # Send formatted Telegram message
                    telegram_send_message(message)

                    print(f"{time_stamp}\n{terminal_msg}")

    def alert_erc20_txns(self, txns: list, min_txn_amount: float) -> None:
        """
        Checks transaction list and alerts if new transaction is important.

        :param txns: List of transactions
        :param min_txn_amount: Minimum transfer amount to alert for
        :return: None
        """
        for txn in txns:

            txn_amount = float(int(txn['value']) / 10 ** int(txn['tokenDecimal']))
            # round txn amount number
            rounding = int(txn['tokenDecimal']) // 6
            txn_amount = round(txn_amount, rounding)
            token_name = txn['tokenSymbol']

            # Construct messages
            time_stamp = datetime.now().astimezone().strftime(time_format)
            message = f"{time_stamp}\n" \
                      f"{txn_amount:,} {token_name} swapped on " \
                      f"<a href='{self.network}/tx/{txn['hash']}'>{self.name}</a>"

            terminal_msg = f"{txn['hash']}, {txn_amount:,} {token_name} swapped on {self.name}"

            # Log all transactions
            log_txns.info(terminal_msg)

            if txn_amount >= min_txn_amount:
                # Send formatted Telegram message
                telegram_send_message(message)

                print(f"{time_stamp} - {terminal_msg}")
