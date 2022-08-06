from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Token:
    """Class for keeping track of token data.
    Token name, Token decimals, Amount to swap"""
    name: str
    decimals: int
    amount: float

    def __repr__(self):
        return f"{self.name} token"


@dataclass(frozen=True)
class Swap:
    """Class for keeping track of swap data.
    Network name, Network id, gas, FromToken, ToToken"""
    chain: str
    id: str
    gas_info: Dict[str, int]
    from_token: Token
    to_token: Token

    def __repr__(self):
        return f"Swap {self.from_token.amount:,} {self.from_token.name} --> " \
               f"{self.to_token.amount:,} {self.to_token.name} on " \
               f"{self.chain}(id: {self.id}), costs: {self.gas_info}"
