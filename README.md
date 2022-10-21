# **TRADEBOT** overview
A trading bot that will open orders on ByBit exchange based on the signals you receive in some Telegram channel.
```sh
Received at 2022-06-21 08:00:03+00:00:
BTCUSDT: [0.49047726 0.50952274] BUY
{'symbol': 'BTCUSDT', 'side': 'Buy', 'price': 21156.4, 'qty': 6.068, 'stop_loss': 20265.6, 'take_profit': 21954.4, 'order_type': 'Market'}

Received at 2022-06-21 08:00:04+00:00:
ETHUSDT: [0.49853283 0.5014672 ] BUY
{'symbol': 'BTCUSDT', 'side': 'Buy', 'price': 1147.42, 'qty': 6.068, 'stop_loss': 1101.84, 'take_profit': 1193.66, 'order_type': 'Market'}
```

## Usage
Bot should be launched in the command line mode either in Docker container (recommended) or on the machine with the preinstalled Python environment:
```sh
usage: tradebot.py [-h] --telegram_api_id TELEGRAM_API_ID --telegram_api_hash TELEGRAM_API_HASH --bybit_api_key BYBIT_API_KEY --bybit_api_secret BYBIT_API_SECRET
                   --telegram_channel TELEGRAM_CHANNEL [--amount AMOUNT] [--take_profit TAKE_PROFIT] [--stop_loss STOP_LOSS]

options:
  -h, --help            show this help message and exit
  --telegram_api_id TELEGRAM_API_ID
                        Telegram API id for telegram to access messages.
  --telegram_api_hash TELEGRAM_API_HASH
                        Telegram API hash for telegram to access messages.
  --bybit_api_key BYBIT_API_KEY
                        API key id for Bybit.
  --bybit_api_secret BYBIT_API_SECRET
                        API secret hash for Bybit.
  --telegram_channel TELEGRAM_CHANNEL
                        ID of telegram channel with signals.
  --config CONFIG
                        Path to config.yaml file.
```

To start the bot in the Docker container provide the required arguments to connect to your Telegram account, ByBit exchange and provide Telegram channel ID to listen the signals.
```sh
docker run -it tradebot tradebot.py  --telegram_api_id [your API id on telegram] --telegram_api_hash [your API hash on telegram] --bybit_api_key [your ByBit API key] --bybit_api_secret [your ByBit API secret] --telegram_channel [Telegram channel ID to listen signals] --config [Path to the config file]
```

Launched bot will use the configuration from the config.yml file and will apply actions in accordance with it.

## Set up `config.yml`
File example can be found in `tradebot/tradebot/config.yml`:

```yml
endpoint: "https://api.bybit.com"
trade_type: "usdt_perpetual"
regex: '(^\w+).*(BUY|SELL)\s*$'
logfile: "tradebot.log"

symbols:
  BTCUSDT:
    multiplier: 5
    buy_leverage: 4
    sell_leverage: 4
    close_policy: 1
    open_policy: 1

  ETHUSDT:
    multiplier: 2
    buy_leverage: 2
    sell_leverage: 2
```
### Configurable fields
* `endpoint` - ByBit endpoint to connect (for the tests `"https://api-testnet.bybit.com"`)
```yml
endpoint: "https://api.bybit.com"
```
* `trade_type` - Type of API to use for order placment (`"usdt_perpetual"`)
```yml
trade_type: "usdt_perpetual"
```
* `regex` - Regular expression for Telegram signal format
```yml
regex: '(^\w+).*(BUY|SELL)\s*$'
```
* `logfile` - Absolute path to the log file to write
```yml
logfile: "tradebot.log"
```
* `symbols` - Symbols are used to set up individual settings for each pair that bot will open/close
```yml
symbols:
  BTCUSDT:
    multiplier: 5
    buy_leverage: 4
    sell_leverage: 4
```
> The name of the pair, for example `BTCUSDT`, following all settings for this pair.<br>
> Possible fields for each pair:
> * `multiplier` (float) - multiplier. Used to apply a multiplier factor for the size of each opened position as `[size] = [quantity from the signal or calculated] * [multiplier]`. Default is 1.0.
> * `buy_leverage` (float) - The size of leverage to use for LONG positions. Default is 1.0.
> * `sell_leverage` (float) - The size of leverage to use for SHORT positions. Default is 1.0.
> * `take_profit` (int) - Take profit percentage to use (calculated from the current price). Not used by default.
> * `stop_loss` (int) - Stop loss percentage to use (calculated from the current price). Not used by default.
> * `close_policy` (1 or 2) - If set to 1 and the unrealized pnl is more than target_profit in USDT it will close current profitable position and open new one. If set to 2 it will close the current open position. Not used by default.
> * `open_policy` (1) - If not set and there is already an opened position the signal will be skipped. If set to 1 the order will always be executed despite currently opened position. Not used by default.
> * `target_profit` (float) - Target profit in USDT to be used in close_policy 1. Default is 0.2 USDT
> * `order_type` ("Market" or "Limit") - Order type. In case of "Limit" the openning price should come in a signal. Default is "Market".

## Specific behaviour
In case of an error in any REST API call the current order will be skipped:
```sh
Received at 2022-06-21 08:00:15+00:00:
ZECUSDT: [0.50497186 0.49502817] BUY
{'symbol': 'ZECUSDT', 'order_type': 'Market', 'side': 'Buy', 'qty': 1.513, 'price': None, 'stop_loss': 63.456, 'take_profit': 68.744, 'time_in_force': 'GoodTillCancel', 'reduce_only': False, 'close_on_trigger': False}
Failed to create order: {'symbol': 'ZECUSDT', 'order_type': 'Market', 'side': 'Buy', 'qty': 1.513, 'price': None, 'stop_loss': 63.456, 'take_profit': 68.744, 'time_in_force': 'GoodTillCancel', 'reduce_only': False, 'close_on_trigger': False}
Takeprofit err (ErrCode: 10001) (ErrTime: 08:00:16).
Request → POST https://api.bybit.com/private/linear/order/create: {'api_key': 'LCNQiXuqE8no6fUcz9', 'close_on_trigger': False, 'order_type': 'Market', 'qty': 1.513, 'recv_window': 5000, 'reduce_only': False, 'side': 'Buy', 'stop_loss': 63.456, 'symbol': 'ZECUSDT', 'take_profit': 68.744, 'time_in_force': 'GoodTillCancel', 'timestamp': 1655798416460, 'sign': 'b023e7e3e262dd91fa52246d5ff0d467728e540c57f33f8a62c62099975cd91d'}.
Skip
```
