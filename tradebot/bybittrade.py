import math
from pybit import usdt_perpetual

class BybitTrade:
    def __init__(self, api_key, api_secret, approved_symbols:list,
            leverage:int=1,
            amount:int=100,
            take_profit:int=4,
            stop_loss:int=4,
            open_policy:bool=False,
            close_policy:bool=False,
        ):
        self.session = usdt_perpetual.HTTP(
            endpoint='https://api.bybit.com', 
            api_key=api_key,
            api_secret=api_secret,
        )
        
        self.amount = amount
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.open_policy = open_policy
        self.close_policy = close_policy
        self._init_symbols(leverage, approved_symbols)
    
    def _init_symbols(self, leverage:int, approved_symbols:list) -> None:
        if not approved_symbols:
            raise ValueError("Approved symbols list is mandatory, got None.")

        res = self.session.query_symbol()
        self.ticks = {}
        self.sizes = {}
        approved_symbols = set(approved_symbols)
        for symbol in res['result']:
            if symbol['name'] not in approved_symbols:
                continue

            self.ticks[symbol['name']] = symbol['price_filter']
            self.sizes[symbol['name']] = symbol['lot_size_filter']

            try:
                self.session.set_leverage(
                    symbol=symbol['name'],
                    buy_leverage=leverage,
                    sell_leverage=leverage,
                )
            except Exception as e:
                print(e)
                print("Skip")
                pass
    
    def current_positions(self) -> list:
        result = self.session.my_position()['result']
        positions = []
        for pos in result:
            if pos['data']['size'] > 0:
                positions.append(pos['data'])
        return positions
    
    def get_active_position(self, positions:list, symbol:str) -> str:
        for pos in positions:
            if pos['symbol'] == symbol:
                return pos
        return None
    
    def create_perp_orders_bulk(self, orders:list, order_type:str='Limit') -> None:
        positions = self.current_positions()
        for order in orders:
            symbol = order['symbol']
            side = order['side']
            position = self.get_active_position(positions, symbol)
            if position:
                if position['unrealised_pnl'] > 0.2:
                    print(f"Close {position['side']} {symbol} position with {position['unrealised_pnl']} profit")
                    self.session.close_position(symbol)
                else:
                    if position['side'] == side:
                        print(f"{side} order for {symbol} is already open")
                        continue
                    else:
                        print(f"{symbol} is open for {position['side']}, but requested for {side}")
                        if self.close_policy:
                            print("Close in accordance with close_policy")
                            self.session.close_position(symbol)
                        if not self.open_policy:
                            print("Do not open opposite in accordance with open_policy")
                            continue
                        print("Open opposite position")

            if 'amount' in order:
                amount = order['amount']
            else:
                amount = self.amount
            
            self.create_perp_order(symbol, side, amount, order_type=order_type)
    
    def create_perp_order(self, symbol:str, side:str, amount:int=None, order_type:str='Limit', target_price:int=None, tp_perc:int=None, sl_perc:int=None) -> None:
        amount = self.amount if not amount else amount
        tp_perc = self.take_profit if not tp_perc else tp_perc
        sl_perc = self.stop_loss if not sl_perc else sl_perc

        if target_price:
            price = target_price
        else:
            res = self.session.orderbook(symbol=symbol)
            price = float(res['result'][0]['price']) if side == "Buy" else float(res['result'][1]['price'])
        
        # Round quantity up to a qty_step
        #qty = amount / price
        #factor = 1/float(self.sizes[symbol]['qty_step'])
        #qty = round(qty*factor) / factor
        qty = round(amount/price, 5)

        
        if side == 'Buy':
            sl = price - price * sl_perc/100
            tp = price + price * tp_perc/100
        else:
            sl = price + price * sl_perc/100
            tp = price - price * tp_perc/100

        # Round sl/tp up to a tick_size
        tick_size = float(self.ticks[symbol]['tick_size'])
        factor = 1 / tick_size
        sl = math.floor(sl*factor)
        tp = math.floor(tp*factor)

        # Adjust sl/tp with a single tick_size so that price*sl_perc < sl and tp > price*tp_perc
        sl = sl + 1 if side == 'Buy' else sl - 1
        tp = tp + 1 if side == 'Buy' else tp - 1
        
        # Really a hacky workaround to mitigate float representation error in IEEE-754. Propose better. TODO
        sl = round(sl / factor, 16)
        tp = round(tp / factor, 16)
                
        order = {}
        order['symbol'] = symbol
        order['side'] = side
        order['price'] = price
        order['qty'] = qty
        order['stop_loss'] = sl
        order['take_profit'] = tp
        order['order_type'] = order_type
        print(order)

        try:
            self.session.place_active_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                price=price,
                take_profit=tp,
                stop_loss=sl,
                qty=qty,
                time_in_force="GoodTillCancel",
                reduce_only=False,
                close_on_trigger=False,
            )
        except Exception as e:
            print(f"Failed to create order: {order}")
            print(e)
            print("Skip")
            pass        
        
        return
