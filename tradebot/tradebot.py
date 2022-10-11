import asyncio
import traceback
import re
from telethon.sync import TelegramClient, events
import demoji
import yaml
from bybittrade import BybitTrade
from symbol import Symbol
from watchdog_utils import start_config_watchdog

REGEX_SIGNAL_PATTERN = r'(^\w+).*(BUY|SELL)\s*$' # We expect messages like "BTCUSDT: [0.48500952 0.51499045] BUY"


async def trade(message, bybit_session):
    try:
        m = re.match(REGEX_SIGNAL_PATTERN, message, re.IGNORECASE)
        if not m:
            raise ValueError(f"Signal {message} has wrong pattern, expected something like 'BTCUSDT: [0.48500952 0.51499045] BUY'")
        
        symbol, side = m.group(1).upper(), m.group(2).upper()

        if symbol not in bybit_session.symbols:
            raise ValueError(f"Symbol {symbol} is not in the list of approved symbols")
        if side not in {'SELL', 'BUY'}:
            raise ValueError(f"Side {side} must be either BUY or SELL")

        side = 'Buy' if side == 'BUY' else 'Sell'
        bybit_session.create_perp_order(symbol, side)

    except Exception as e:
        print(traceback.format_exc())
        print(e)
        print(f"Failed to execute order for signal {message}")
        pass

    return

def listen_telegram(api_id, api_hash, bybit_session, input_channel):
    with TelegramClient('Listen', api_id, api_hash) as client:
        @client.on(events.NewMessage(chats=[input_channel]))
        async def channel_listener(event):
            response = event.message
            message = demoji.replace(response.message, '')
            message = message.encode("ascii", "ignore").decode()
            print(f"Received at {str(response.date)}:")
            print(message)
            asyncio.create_task(trade(message, bybit_session))

        client.run_until_disconnected()


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--telegram_api_id', required=True, type=int, default=None, help="Telegram API id for telegram to access messages.")
    parser.add_argument('--telegram_api_hash', required=True, type=str, default=None, help="Telegram API hash for telegram to access messages.")
    parser.add_argument('--bybit_api_key', required=True, type=str, default=None, help="API key id for Bybit.")
    parser.add_argument('--bybit_api_secret', required=True, type=str, default=None, help="API secret hash for Bybit.")
    parser.add_argument('--telegram_channel', required=True, type=int, default=None, help="ID of telegram channel with signals.")
    parser.add_argument('--config', required=True, type=str, default=None, help="Path to config.yaml file.")
    args = parser.parse_args()

    config_file = args.config
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)
    
    print(f"Apply config {config_file}:\n{yaml.dump(config, indent=4)}")
    
    ref = config.get('global_reference', None)
    endpoint = config.get('endpoint', 'https://api-testnet.bybit.com')
    global REGEX_SIGNAL_PATTERN
    REGEX_SIGNAL_PATTERN = config.get('regex', re.compile(r'(^\w+).*(BUY|SELL)\s*$'))
    trade_type = config.get('trade_type', 'usdt_perpetual')
    symbols = {symbol_name: Symbol(symbol_name, symbol_config, ref=ref) for symbol_name, symbol_config in config['symbols'].items()}

    sess = BybitTrade(
        args.bybit_api_key, 
        args.bybit_api_secret, 
        symbols,
        endpoint=endpoint, 
        trade_type=trade_type,
    )

    start_config_watchdog(config_file, sess)

    listen_telegram(args.telegram_api_id, args.telegram_api_hash, bybit_session=sess, input_channel=args.telegram_channel)


if __name__ == '__main__':
    main()
