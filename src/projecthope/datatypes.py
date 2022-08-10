from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Token:
    """Class for keeping track of token data.
    Token name, Amount to swap, Token decimals"""
    name: str
    amount: float
    decimals: int = 18

    def __repr__(self):
        return f"{self.name} token"


@dataclass(frozen=True)
class Swap:
    """Class for keeping track of swap data.
    Network name, Network id, Cost, FromToken, ToToken, remainder."""
    chain: str
    id: str
    cost: Dict[str, int]
    from_token: Token
    to_token: Token
    remainder: float = 0

    def __repr__(self):
        if self.chain.lower() == "binancecex":
            price_per = (self.from_token.amount - self.cost["exchange_fee"]) / self.to_token.amount
            fee = self.cost["exchange_fee"]
        else:
            price_per = self.from_token.amount / self.to_token.amount
            fee = self.cost

        return f"Swap {self.from_token.amount:,.6f} {self.from_token.name} -> " \
               f"{self.to_token.amount:,.6f} {self.to_token.name} on " \
               f"{self.chain}(id: {self.id}), fee: {fee}, price per {self.to_token.name}: {price_per:,.6f}, " \
               f"remaining amount: {self.remainder:,.6f} {self.from_token.name}"
