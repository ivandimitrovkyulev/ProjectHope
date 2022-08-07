from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class BinanceSwap:
    """Class for keeping track of Binance swap data.
    swap_in(name, amount), swap_out(name, amount), fee(currency, amount)"""
    swap_in_name: str
    swap_in_amount: float
    remainder: float
    swap_out_name: str
    swap_out_amount: float
    fee: Tuple[str, float]

    def __repr__(self):
        return f"BinanceSwap: {self.swap_in_amount:,.6f} {self.swap_in_name} for " \
               f"{self.swap_out_amount:,.6f} {self.swap_out_name}, fee: {self.fee[1]} {self.fee[0]}, " \
               f"price: {(self.swap_in_amount / self.swap_out_amount):,.6f} {self.swap_in_name}, " \
               f"remaining amount: {self.remainder:,.6f} {self.swap_in_name}"
