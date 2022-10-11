

class Symbol:
    def __init__(self, name, config, ref=None):
        self.name = name
        self.order_type = config.get('order_type', ref.order_type if ref else 'Market')
        self.buy_leverage = config.get('buy_leverage', ref.buy_leverage if ref else None)
        self.sell_leverage = config.get('sell_leverage', ref.sell_leverage if ref else None)
        self.multiplier = config.get('multiplier', ref.multiplier if ref else 1.0)
        self.take_profit = config.get('take_profit', ref.take_profit if ref else 0)
        self.stop_loss = config.get('stop_loss', ref.stop_loss if ref else 0)
        self.open_policy = config.get('open_policy', ref.open_policy if ref else None)
        self.close_policy = config.get('close_policy', ref.close_policy if ref else None)
        self.size = config.get('size', ref.size if ref else 100)
        self.target_profit = config.get('target_profit', ref.target_profit if ref else 0.2)