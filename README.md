# Tradebot 
A trading bot that will open orders on ByBit exchange based on the signals you receive in some Telegram channel.
```
Received at 2022-06-21 08:00:03+00:00:
BTCUSDT: [0.49047726 0.50952274] BUY
{'symbol': 'BTCUSDT', 'side': 'Buy', 'price': 21156.4, 'qty': 6.068, 'stop_loss': 20265.6, 'take_profit': 21954.4, 'order_type': 'Market'}

Received at 2022-06-21 08:00:04+00:00:
ETHUSDT: [0.49853283 0.5014672 ] BUY
{'symbol': 'BTCUSDT', 'side': 'Buy', 'price': 1147.42, 'qty': 6.068, 'stop_loss': 1101.84, 'take_profit': 1193.66, 'order_type': 'Market'}
```

## Usage
Bot should be launched in the command line mode either in Docker container (recommended) or on the machine with the preinstalled Python environment:
```
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
  --amount AMOUNT       Amount of USDT to be used in a single order including leverage. Default is 100. (i.e amount of 100 USDT with default 10x leverage will use 10
                        USDT of your derivative account)
  --take_profit TAKE_PROFIT
                        Take profit in percent from the purchase price. Default is 4.
  --stop_loss STOP_LOSS
                        Stop loss in percent from the purchase price. Default is 4.
  --close_policy CLOSE_POLICY
                        Close active position if new signal shows opposite side (BUY or SELL). Default is
                        False.
  --open_policy OPEN_POLICY
                        Open new position on opposite side (BUY or SELL) when there is already an active one.
                        Default is False.
```

To start the bot in the Docker container provide the required arguments to connect to your Telegram account, ByBit exchange and provide Telegram channel ID to listen the sugnals.
```
docker run -it tradebot tradebot.py  --telegram_api_id [your API id on telegram] --telegram_api_hash [your API hash on telegram] --bybit_api_key [your ByBit API key] --bybit_api_secret [your ByBit API secret] --telegram_channel [Telegram channel ID to listen signals]
```

The bot will be open `Market` USDT Perpetual orders using the default `10x` leverage in the quantity of specified USDT amount, i.e amount of 100 USDT with default 10x leverage will use 10 USDT of your derivative account. Default amount is 100 USDT. Also the default take_profit and stop_loss of 4% from the order price will be set. You can change these values to any other in the command line arguments on submission.

## Specific behaviour
Before openning a new order bot will check if this symbol is currently an active position and if the requested order side (Buy or Sell) is the same it will ignore current signal:
```
Received at 2022-06-21 09:27:06+00:00:
BTCUSDT: [0.50497186 0.49502817] SELL
Sell order for BTCUSDT is already open
```

If the order side is opposite, it will follow open and close policy.  
If `close_policy` is set to True (default is False) it will close current position:
```
Received at 2022-06-20 08:00:19+00:00:
XLMUSDT: [0.50070024 0.49929973] BUY
XLMUSDT is open for Sell, but requested for Buy
Close in accordance with close_policy
```

If `open_policy` is set to False (default is False) it wont open new opposite position:
```
Received at 2022-06-20 08:00:17+00:00:
BTCUSDT: [0.50497186 0.49502817] BUY
BTCUSDT is open for Sell, but requested for Buy
Do not open opposite in accordance with open_policy
```

In case of an error in any REST API call the current order will be skipped:
```
Received at 2022-06-21 08:00:15+00:00:
ZECUSDT: [0.50497186 0.49502817] BUY
{'symbol': 'ZECUSDT', 'order_type': 'Market', 'side': 'Buy', 'qty': 1.513, 'price': None, 'stop_loss': 63.456, 'take_profit': 68.744, 'time_in_force': 'GoodTillCancel', 'reduce_only': False, 'close_on_trigger': False}
Failed to create order: {'symbol': 'ZECUSDT', 'order_type': 'Market', 'side': 'Buy', 'qty': 1.513, 'price': None, 'stop_loss': 63.456, 'take_profit': 68.744, 'time_in_force': 'GoodTillCancel', 'reduce_only': False, 'close_on_trigger': False}
Takeprofit err (ErrCode: 10001) (ErrTime: 08:00:16).
Request → POST https://api.bybit.com/private/linear/order/create: {'api_key': 'LCNQiXuqE8no6fUcz9', 'close_on_trigger': False, 'order_type': 'Market', 'qty': 1.513, 'recv_window': 5000, 'reduce_only': False, 'side': 'Buy', 'stop_loss': 63.456, 'symbol': 'ZECUSDT', 'take_profit': 68.744, 'time_in_force': 'GoodTillCancel', 'timestamp': 1655798416460, 'sign': 'b023e7e3e262dd91fa52246d5ff0d467728e540c57f33f8a62c62099975cd91d'}.
Skip
```
