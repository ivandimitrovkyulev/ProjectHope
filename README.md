# HopBridge v0.2.1

Program that screens https://hop.exchange for arbitrage and etherscan networks for contract transactions of specified contract addresses. Alerts via a Telegram message if something of interest is found. Currently supports the following L2 networks: [Optimism](https://optimistic.etherscan.io/), [Arbitrum](https://arbiscan.io/), [Polygon](https://polygonscan.com), [Gnosis](https://blockscout.com/xdai/mainnet/).

<br>

## Installation ##
<br>

This project uses **Python 3.9** and requires a
[Chromium WebDriver](https://chromedriver.chromium.org/getting-started/) installed.

Clone the project:
```
git clone https://github.com/ivandimitrovkyulev/HopBridge

cd HopBridge
```

Activate virtual environment:

```
poetry shell
```

Install all third-party project dependencies:
```
poetry install
```

You will need to apply for API access and save the following variables in a **.env** file in .../HopBridge/:
```
CHROME_LOCATION=<your/web/driver/path/location> 

TOKEN=<telegram-token-for-your-bot>

CHAT_ID_ALERTS=<id-of-telegram-chat-for-alerts>

CHAT_ID_DEBUG=<id-of-telegram-chat-for-debugging>

WEB3_INFURA_PROJECT_ID=<project-id-from-node>

PROJECT_ID=<project-id-from-node>

OPTIMISM_API_KEY=<etherscan-optimism-api-key>

ARBITRUM_API_KEY=<etherscan-arbitrum-api-key>

POLYGON_API_KEY=<etherscan-polygon-api-key>

GNOSIS_API_KEY=<etherscan-gnosis-api-key>
```
<br/>

## Running the script
<br/>

To screen the hop-bridge website for arbitrage:
```
var="$(cat input.json)"
python3 main.py "$var"
```

Where **input.json** are variables for screening:
```
{
    "USDC": {
        "start": 50000,
        "end": 60000,
        "step": 10000,
        "min_arb": 50,
        "decimals": 6
    },
    "USDT": {
        "start": 30000,
        "end": 40000,
        "step": 10000,
        "min_arb": 50,
        "decimals": 6
    },
    "settings": {
        "sleep_time": 5
    }
}
```
<br>

To screen network etherscan for Erc20 Token Transactions:
```
var="$(cat contracts.json)"
python3 etherscan.py -e "$var"
```
Or to screen for a contract transaction:
```
python3 etherscan.py -t "$var"
```

Where **contracts.json** are Network and screening variables of the following schema:
```
{
    "optimism_usdt": {
        "token": "USDT",
        "url": "https://optimistic.etherscan.io/address/0x7D269D3E0d61A05a0bA976b7DBF8805bF844AF3F",
        "address": "0x7D269D3E0d61A05a0bA976b7DBF8805bF844AF3F",
        "network": "Optimism",
        "decimals": 6,
        "min_amount": 30000
    },
    "arbitrum_usdc": {
        "token": "USDC",
        "url": "https://arbiscan.io/address/0xe22d2bedb3eca35e6397e0c6d62857094aa26f52",
        "address": "0xe22D2beDb3Eca35E6397e0C6D62857094aA26F52",
        "network": "Arbitrum",
        "decimals": 6,
        "min_amount": 50000
    },
    "filter_by": ["to", "0x0000000000000000000000000000000000000000"]
}
```

For help:
```
python3 etherscan.py --help
```

<br>
Contact: ivandkyulev@gmai.com