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
            price = float(res['result'][0]['price'])
        
        qty = round(amount / price, 3)
        
        if side == 'Buy':
            sl = price - price * sl_perc/100
            tp = price + price * tp_perc/100
        else:
            sl = price + price * sl_perc/100
            tp = price - price * tp_perc/100
        sl = round(sl, 3)
        tp = round(tp, 3)
                
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