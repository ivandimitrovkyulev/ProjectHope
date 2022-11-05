ProjectHope
===================
# version 0.1.0

---------------------------------------------------------------------------------------

ProjectHope screens for arbitrage between BinanceCEX and 1inch Smart Order Router. Alerts via Telegram message if something above minimum threshold is found.


### Installation

This project uses **Python 3.10** and **poetry 1.1.13**

Clone the project:
```shell
git clone https://github.com/ivandimitrovkyulev/ProjectHope.git

cd ProjectHope
```

Activate virtual environment:

```shell
poetry shell
```

Install all third-party project dependencies:
```shell
poetry install
```

Create a Telegram Bot and save the following variables in a **.env** file in **./ProjectHope**:
```dotenv
TOKEN=<telegram-token-for-your-bot>
CHAT_ID_ALERTS=<id-of-telegram-chat-for-alerts>
CHAT_ID_DEBUG=<id-of-telegram-chat-for-debugging>
PROJECT_ID=<node-provider-id>
ETHERSCAN_API_KEY=<etherscan-api-key>
BINANCE_KEY=<binance-api-key>
BINANCE_SECRET=<binance-secret-key>
```

### Running the script

To start screening for arbitrage:
```shell
# Save json file in a variable
var="$(cat coins.json)"
# Run script
python3 main.py -s "$var"
```

Where **coins.json** are variables for screening:
```json
{
    "base_tokens": {
        "USDC": {
            "networks": {
                "Ethereum":  {"address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "decimals": 6},
                "Binance":   {"address": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", "decimals": 18},
                "Polygon":   {"address": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", "decimals": 6},
            }
        }
    },
    "arb_tokens": {
        "coinX": {
            "networks": {
                "Ethereum":  {"address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "decimals": 18},
                "Binance":   {"address": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", "decimals": 18},
                "Polygon":   {"address": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", "decimals": 18},
            },
            "swap_amount": 10000, "min_arb": 100
        },
        "coinY": {
            "networks": {
                "Ethereum":  {"address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "decimals": 18},
                "Binance":   {"address": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", "decimals": 18},
                "Polygon":   {"address": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", "decimals": 18},
            },
            "swap_amount": 10000, "min_arb": 100
        }
    }

}
```

If an arbitrage is present, the alert message will have the following format:
```text
22/10/17 15:13:22, UTC
1) Buy 8,000 USDT -> 0.42 WBTC on BinanceCEX🟧
2) Sell 0.42 WBTC -> 8,100 USDT on Optimism
-->Arb. 100 USDT, fees ~$64
```

All log filles are saved in **./ProjectHope/logs**

For help:
```shell
python3 main.py --help
```


## Docker Deploy ##

```shell
# To build a Docker image
docker build . -t <docker-image-name>

# To run container
docker run -it <image-id> python3 main.py -s "$var"
docker run --name="projecthope" -it "<image-id>" python3 main.py "$var"
```

<br>
Contact: ivandkyulev@gmail.com