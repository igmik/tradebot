import math
from symtable import Symbol
from pybit import usdt_perpetual
from collections import defaultdict
import logging


ENDPOINT = 'https://api-testnet.bybit.com'


class BybitTrade:
    def __init__(self, api_key, api_secret, symbols:dict,
            endpoint:str=ENDPOINT,
            trade_type:str='usdt_perpetual',
        ):

        self.logger = logging.getLogger('tradebot.bybit')
        self.symbols = symbols
        self.trade_type = trade_type
        if trade_type == 'usdt_perpetual':
            trade_api = usdt_perpetual

        self.session = trade_api.HTTP(
            endpoint=endpoint, 
            api_key=api_key,
            api_secret=api_secret,
        )
        
        self.order_counter = {}
        self.order_counter['Buy'] = defaultdict(list)
        self.order_counter['Sell'] = defaultdict(list)
        self._init_symbols(symbols)
    
    def _init_symbols(self, symbols:dict) -> None:
        if not symbols:
            raise ValueError("Approved symbols configuration is mandatory, got None.")

        res = self.session.query_symbol()
        self.ticks = {}
        self.sizes = {}
        for symbol in res['result']:
            if symbol['name'] not in symbols:
                continue
            
            cur_symbol = symbols[symbol['name']]

            self.ticks[symbol['name']] = symbol['price_filter']
            self.sizes[symbol['name']] = symbol['lot_size_filter']
            self.set_leverage(cur_symbol)
    
    def _get_current_price(self, symbol:str, side:str=None) -> float:
        res = self.session.orderbook(symbol=symbol)
        if not side:
            side = 'Buy'
        return float(res['result'][0]['price']) if side == "Buy" else float(res['result'][1]['price'])

    def _apply_close_policy_1(self, position, symbol, target_profit=0.2, **kwargs):
        _ = kwargs
        if position['unrealised_pnl'] > target_profit:
            self.logger.info(f"Close {position['side']} {symbol} position with {position['unrealised_pnl']} profit")
            return self.session.close_position(symbol)
        return None
    
    def _apply_close_policy_2(self, position, symbol, side, **kwargs):
        _ = kwargs
        if position['side'] != side:
            self.logger.info(f"{symbol} is open for {position['side']}, but requested for {side}. Closing.")
            return self.session.close_position(symbol)
        return None
    
    def _apply_close_policy(self, close_policy:int, position:dict, **kwargs) -> object:
        if position:
            if close_policy == 1:
                return self._apply_close_policy_1(position, **kwargs)
            elif close_policy == 2:
                return self._apply_close_policy_2(position, **kwargs)
            else:
                return None
        else:
            return True

    def set_leverage(self, symbol:Symbol) -> None:
        try:
            self.session.set_leverage(
                symbol=symbol.name,
                buy_leverage=symbol.buy_leverage,
                sell_leverage=symbol.sell_leverage,
            )
        except Exception as e:
            self.logger.warning(e)
            self.logger.warning("Skip")
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
    
    def close_opened_position(self, symbol, side):
        try:
            position = self.get_active_position(self.current_positions(), symbol)
            if position:
                if position['side'] == side:
                    self.logger.info(f"Closing {symbol} for side {side}.")
                    self.session.close_position(symbol)
                else:
                    self.logger.info(f"Position {symbol} for side {side} not found.")
                    self.logger.info("Skip.")
            else:
                self.logger.info(f"Cannot close position {symbol} for side {side} as no opened positions.")
                self.logger.info("Skip.")
        except Exception as e:
            self.logger.warning(f"Failed to close order: {symbol} for side {side}.")
            self.logger.warning(e)
            self.logger.warning("Skip")
            pass  
    
    def close_last_order(self, symbol, side):
        try:
            if not self.order_counter[side][symbol]:
                self.logger.warning(f"No active orders of {symbol} for side {side} to close")
                self.logger.warning("Skip")
                return
    
            order_id = self.order_counter[side][symbol].pop()
            self.logger.info(f"Closing {symbol} for side {side} with order {order_id}.")
            self.session.close_order(symbol=symbol, parentOrderId=order_id)
        except Exception as e:
            self.logger.warning(f"Failed to close order: {symbol} for side {side} with order {order_id}.")
            self.logger.warning(e)
            self.logger.warning("Skip")
            pass
    
    def adjust_tpsl(self, symbol, side, price, tp_perc, sl_perc):
        if side == 'Buy':
            sl = price - price * sl_perc/100
            tp = price + price * tp_perc/100
        else:
            sl = price + price * sl_perc/100
            tp = price - price * tp_perc/100
        
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

        return tp, sl
    
    def create_perp_order(self, symbol:str, side:str, qty:float=0.0, target_price:int=None) -> None:
        size = self.symbols[symbol].size
        tp_perc = self.symbols[symbol].take_profit
        sl_perc = self.symbols[symbol].stop_loss
        mp = self.symbols[symbol].multiplier
        order_type = self.symbols[symbol].order_type
        open_policy = self.symbols[symbol].open_policy
        close_policy = self.symbols[symbol].close_policy
        target_profit = self.symbols[symbol].target_profit
        
        if open_policy or close_policy:
            position = self.get_active_position(self.current_positions(), symbol)
            closed = self._apply_close_policy(close_policy, position, symbol=symbol, side=side, target_profit=target_profit) if close_policy else None
            if position and not closed and not open_policy:
                self.logger.info(f"{position['side']} order for {symbol} is already open")
                self.logger.info('Skip')
                return                  

        if target_price:
            price = target_price
        else:
            price = self._get_current_price(symbol, side)
        
        factor = 1/float(self.sizes[symbol]['qty_step'])
        qty = qty * mp if qty else size / price
        # Round quantity up to a qty_step
        qty = math.floor(max(qty*factor, 1.0)) / factor

        order = {}
        order['symbol'] = symbol
        order['side'] = side
        order['price'] = price
        order['qty'] = qty
        order['order_type'] = order_type

        tp, sl = None, None
        if sl_perc or tp_perc:
            tp, sl = self.adjust_tpsl(symbol, side, price, tp_perc, sl_perc)
            tp = tp if tp_perc else None
            sl = sl if sl_perc else None
            order['stop_loss'] = sl
            order['take_profit'] = tp
        
        self.logger.debug(order)

        try:
            resp = self.session.place_active_order(
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
            if 'order_id' in resp['result'] or 'orderId' in resp['result']:
                order_id = resp['result'].get('order_id') if 'order_id' in resp['result'] else resp['result'].get('orderId')
                self.order_counter[side][symbol].append(order_id)
                self.logger.info(f"Opened {symbol} for {side} with order ID {order_id}")
        except Exception as e:
            self.logger.warning(f"Failed to create order: {order}")
            self.logger.warning(e)
            self.logger.warning("Skip")
            pass        
        
        return
