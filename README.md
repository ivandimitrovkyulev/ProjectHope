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
```
<br/>

## Running the script
<br/>

To screen https://synapseprotocol.com for arbitrage:
```
var="$(cat input.json)"

python3 main.py -s "$var"
```

Where **input.json** are variables for screening:
```
{ 
    "USDC": {
        "swap_amount": 50000,
        "arbitrage": 10,
        "networks": {
            "Ethereum":  {"decimals": 6,  "chain_id": 1,     "token": "USDC"},
            "Optimism":  {"decimals": 6,  "chain_id": 10,    "token": "USDC"},
            "Fantom":    {"decimals": 6,  "chain_id": 250,   "token": "USDC"},
        }
    },
    "ETH": {
        "swap_amount": 50,
        "arbitrage": 0.02,
        "networks": {
            "Ethereum":  {"decimals": 18, "chain_id": 1,     "token": "ETH"},
            "Optimism":  {"decimals": 18, "chain_id": 10,    "token": "WETH"},
            "Fantom":    {"decimals": 18, "chain_id": 250,   "token": "FTM_ETH"},
        }
    }
}
```
<br>

All log filles are saved in **./synapse/logs**

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
```

<br>
Contact: ivandkyulev@gmai.com