import asyncio
import re
from telethon.sync import TelegramClient, events
from bybittrade import BybitTrade

REGEX_SIGNAL_PATTERN = r'(^\w+).*(BUY|SELL)\s*$' # We expect messages like "BTCUSDT: [0.48500952 0.51499045] BUY"
APPROVED_SYMBOLS = {
    'TRXUSDT',
    'BTCUSDT',
    'ETHUSDT',
    'ADAUSDT',
    'XMRUSDT',
    'BNBUSDT',
    'XRPUSDT',
    'LINKUSDT',
    'ETCUSDT',
    'DASHUSDT',
    'EOSUSDT',
    'LTCUSDT',
    'ZECUSDT',
    'XLMUSDT',
}


async def trade(message, bybit_session):
    try:
        m = re.match(REGEX_SIGNAL_PATTERN, message, re.IGNORECASE)
        if not m:
            raise ValueError(f"Signal {message} has wrong pattern, expected something like 'BTCUSDT: [0.48500952 0.51499045] BUY'")
        
        symbol, side = m.group(1).upper(), m.group(2).upper()

        if symbol not in APPROVED_SYMBOLS:
            raise ValueError(f"Symbol {symbol} is not in the list of approved symbols")
        if side not in {'SELL', 'BUY'}:
            raise ValueError(f"Side {side} must be either BUY or SELL")

        side = 'Buy' if side == 'BUY' else 'Sell'
        orders = [{'symbol': symbol, 'side': side}]
        bybit_session.create_perp_orders_bulk(orders, order_type='Market')

    except Exception as e:
        print(e)
        print(f"Failed to create an order for signal {message}")
        pass

    return

def listen_telegram(api_id, api_hash, bybit_session, input_channel):
    with TelegramClient('Listen', api_id, api_hash) as client:
        @client.on(events.NewMessage(chats=[input_channel]))
        async def channel_listener(event):
            message = event.message
            print()
            print(f"Received at {str(message.date)}:")
            print(message.message)
            asyncio.create_task(trade(message.message, bybit_session))

        client.run_until_disconnected()


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--telegram_api_id', required=True, type=int, default=None, help="Telegram API id for telegram to access messages.")
    parser.add_argument('--telegram_api_hash', required=True, type=str, default=None, help="Telegram API hash for telegram to access messages.")
    parser.add_argument('--bybit_api_key', required=True, type=str, default=None, help="API key id for Bybit.")
    parser.add_argument('--bybit_api_secret', required=True, type=str, default=None, help="API secret hash for Bybit.")
    parser.add_argument('--telegram_channel', required=True, type=int, default=None, help="ID of telegram channel with signals.")
    parser.add_argument('--amount', type=int, default=100, 
        help="Amount of USDT to be used in a single order including leverage. Default is 100. (i.e amount of 100 USDT with default 10x leverage will use 10 USDT of your derivative account)")
    parser.add_argument('--take_profit', type=int, default=4, help="Take profit in percent from the purchase price. Default is 4.")
    parser.add_argument('--stop_loss', type=int, default=4, help="Stop loss in percent from the purchase price. Default is 4.")
    args = parser.parse_args()

    sess = BybitTrade(args.bybit_api_key, args.bybit_api_secret, amount=args.amount, take_profit=args.take_profit, stop_loss=args.stop_loss)
    listen_telegram(args.telegram_api_id, args.telegram_api_hash, bybit_session=sess, input_channel=args.telegram_channel)


if __name__ == '__main__':
    main()
