# ProjectHope v0.0.1

ProjectHope screens for arbitrage and alerts via a Telegram message if something of interest is found.

<br>

## Installation ##
<br>

This project uses **Python 3.10** and **poetry 1.1.13**

Clone the project:
```
git clone https://github.com/ivandimitrovkyulev/ProjectHope.git

cd ProjectHope
```

Activate virtual environment:

```
poetry shell
```

Install all third-party project dependencies:
```
poetry install
```

Create a Telegram Bot and save the following variables in a **.env** file in **./ProjectHope**:
```
TOKEN=<telegram-token-for-your-bot>
CHAT_ID_ALERTS=<id-of-telegram-chat-for-alerts>
CHAT_ID_DEBUG=<id-of-telegram-chat-for-debugging>
PROJECT_ID=<node-provider-id>
ETHERSCAN_API_KEY=<etherscan-api-key>
BINANCE_KEY=<binance-api-key>
BINANCE_SECRET=<binance-secret-key>
```
<br/>

## Running the script
<br/>

To start screening for arbitrage:
```
var="$(cat coins.json)"

python3 main.py -s "$var"
```

Where **coins.json** are variables for screening:
```
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
<br>

All log filles are saved in **./ProjectHope/logs**

For help:
```
python3 main.py --help
```
<br>

## Docker Deploy ##
<br>

```
# To build a Docker image
docker build . -t <docker-image-name>

# To run container
docker run -it <image-id> python3 main.py -s "$var"
docker run --name="projecthope" -it "<image-id>" python3 main.py "$var"
```

<br>
Contact: ivandkyulev@gmai.com