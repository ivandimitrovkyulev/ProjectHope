from dataclasses import dataclass


@dataclass(frozen=True)
class BinanceSwap:
    """Class for keeping track of Binance swap data.
    Network name, Network id, gas, FromToken, ToToken"""
    swap_in: float
    swap_out: float
    fee: float

    def __repr__(self):
        return f"BinanceSwap {self.swap_in} for {self.swap_out}, fee: {self.fee}"
