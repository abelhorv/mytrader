class OrderManager:
    def __init__(self, slippage):
        self.slippage = slippage

    def send_order(self, signal, price):
        exec_price = price + (self.slippage if signal=='BUY' else -self.slippage)
        print(f"Executing {signal} at {exec_price}")
