import math
from pybit import usdt_perpetual

class BybitTrade:
    def __init__(self, api_key, api_secret, amount:int=100, take_profit:int=4, stop_loss:int=4):
        self.session = usdt_perpetual.HTTP(
            endpoint='https://api.bybit.com', 
            api_key=api_key,
            api_secret=api_secret,
        )
        
        self.amount = amount
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self._query_and_set_symbols()
    
    def _query_and_set_symbols(self) -> None:
        res = self.session.query_symbol()
        self.ticks = {}
        self.sizes = {}
        for symbol in res['result']:
            self.ticks[symbol['name']] = symbol['price_filter']
            self.sizes[symbol['name']] = symbol['lot_size_filter']
    
    def current_positions(self) -> list:
        result = self.session.my_position()['result']
        positions = []
        for pos in result:
            if pos['data']['size'] > 0:
                positions.append(pos['data'])
        return positions
    
    def get_position_side(self, positions:list, symbol:str) -> str:
        for pos in positions:
            if pos['symbol'] == symbol:
                return pos['side']
        return None
    
    def create_perp_orders_bulk(self, orders:list, order_type:str='Limit', close_policy:bool=True) -> None:
        positions = self.current_positions()
        for order in orders:
            symbol = order['symbol']
            side = order['side']
            active_side = self.get_position_side(positions, symbol)
            if active_side:
                if active_side == side:
                    print(f"{side} order for {symbol} is already open")
                    continue
                else:
                    print(f"{symbol} is open for {active_side}, but requested for {side}")
                    if close_policy:
                        print("Will close first")
                        self.session.close_position(symbol)
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
