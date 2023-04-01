from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
from statistics import mean

class Trader:         
    lim = {"PEARLS": 20, "BANANAS": 20, "COCONUTS": 600, "PINA_COLADAS": 300, "BERRIES": 250, "DIVING_GEAR": 50, "BAGUETTE": 150, "DIP": 300, "UKULELE": 70, "PICNIC_BASKET": 70}                          
    long = {"PEARLS": False, "BANANAS": False, "COCONUTS": False, "PINA_COLADAS": False, "BERRIES": False, "DIVING_GEAR": False, "BAGUETTE": False, "DIP": False, "UKULELE": False, "PICNIC_BASKET": False}              
    r_buys = {}
    r_sells = {}
    three_fifty_avgs = {}
    three_twenty_avgs = {}
    prev_price = {}

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        cur_buy_means = {}
        cur_sell_means = {}
        for sym, order_depth in state.order_depths.items():
            buy_med = []
            sell_med = []
            for k,v in order_depth.buy_orders.items():
                buy_med += [int(k)]*abs(int(v))
            for k,v in order_depth.sell_orders.items():
                sell_med += [int(k)]*abs(int(v))
            cur_buy_means[sym] = mean(buy_med)
            cur_sell_means[sym] = mean(sell_med)

        for sym in state.listings.keys():
            if sym not in self.r_buys and sym in cur_buy_means:
                self.r_buys[sym] = [cur_buy_means[sym]]
            if sym not in self.r_sells and sym in cur_sell_means:
                self.r_sells[sym] = [cur_sell_means[sym]]
            
            elif sym in self.r_buys and sym in self.r_sells and sym in cur_buy_means and sym in cur_sell_means:
                if len(self.r_buys[sym]) < 50:
                    self.r_buys[sym].append(cur_buy_means[sym])
                elif len(self.r_buys[sym]) == 50:
                    self.r_buys[sym] = self.r_buys[sym][1:] + [cur_buy_means[sym]]
                
                if len(self.r_sells[sym]) < 50:
                    self.r_sells[sym].append(cur_sell_means[sym])
                elif len(self.r_sells[sym]) == 50:
                    self.r_sells[sym] = self.r_sells[sym][1:] + [cur_sell_means[sym]]

        # BUY / SELL #
        results = {}
        for sym in state.listings.keys():
            buy_price = 0
            buy_vol = 0
            sell_price = 0
            sell_vol = 0
            try:
                if len(state.order_depths[sym].buy_orders) > 0:
                    buy_price = min(state.order_depths[sym].sell_orders.keys())
                    buy_vol = state.order_depths[sym].sell_orders[buy_price]

                if len(state.order_depths[sym].sell_orders) > 0:
                    sell_price = max(state.order_depths[sym].buy_orders.keys())
                    sell_vol = state.order_depths[sym].buy_orders[sell_price]

            except: continue
            if sym not in cur_buy_means or sym not in cur_sell_means or sym not in self.r_buys or sym not in self.r_sells or len(self.r_buys[sym]) < 50 or len(self.r_sells[sym]) < 50: continue

            if sym not in self.three_fifty_avgs:
                self.three_fifty_avgs[sym] = [mean(self.r_sells[sym])]
                self.three_twenty_avgs[sym] = [mean(self.r_sells[sym][19:])]
                continue
            else:
                if len(self.three_fifty_avgs[sym]) < 3:
                    self.three_fifty_avgs[sym].append(mean(self.r_sells[sym]))
                    self.three_twenty_avgs[sym].append(mean(self.r_sells[sym][19:]))
                    continue
                elif len(self.three_fifty_avgs[sym]) == 3:
                    self.three_fifty_avgs[sym] = self.three_fifty_avgs[sym][1:] + [mean(self.r_sells[sym])]
                    self.three_twenty_avgs[sym] = self.three_twenty_avgs[sym][1:] + [mean(self.r_sells[sym][19:])]
            buy_signal = self.three_twenty_avgs[sym][-1] > self.three_fifty_avgs[sym][-1] and self.three_twenty_avgs[sym][-3] < self.three_fifty_avgs[sym][-3]
            sell_signal = self.three_twenty_avgs[sym][-1] < self.three_fifty_avgs[sym][-1] and self.three_twenty_avgs[sym][-3] > self.three_fifty_avgs[sym][-3]

            t = []
            for i in range(len(self.r_sells[sym][36:]) - 1): 
                t.append(self.r_sells[sym][36:][i + 1] - self.r_sells[sym][36:][i])    
            pos = [n for n in t if n > 0]
            neg = [n for n in t if n < 0]
            try:
                RS = mean(pos) / abs(mean(neg))
                RSI = 100 - 100 / (1 + RS)
            except:
                RSI = 100
            #print(f'{sym};{mean(self.r_sells[sym][19:])};{mean(self.r_sells[sym])};{RSI}')
            
            t = []
            if sym == "PEARLS":
                if self.long[sym] and sym in self.prev_price and sell_price >= 10002:
                    print(f'SELL :: {sym} :: {sell_price} :: {sell_vol}')
                    t.append(Order(sym, sell_price, -sell_vol))
                    self.long[sym] = False
                if not self.long[sym] and buy_price <= 9998:
                    print(f'BUY :: {sym} :: {buy_price} :: {buy_vol}')
                    t.append(Order(sym, buy_price, -buy_vol))
                    self.prev_price[sym] = buy_price
                    self.long[sym] = True
                results[sym] = t
                continue
            if sym != "PEARLS": continue
            
            if sym in state.position and state.position[sym] == 0: self.long[sym] = False

            if self.long[sym] and sym in self.prev_price and sym in state.position and sell_signal and sell_price*.99 > self.prev_price[sym]:
                pos = state.position[sym]
                vol = sell_vol
                if abs(sell_vol) > abs(pos):
                    vol = pos
                print(f'SELL :: {sym} :: {sell_price*.99} :: {vol}')
                t.append(Order(sym, sell_price*.99, -vol))

            if not self.long[sym] and buy_signal and RSI >= 60:
                print(f'BUY :: {sym} :: {buy_price*1.01} :: {buy_vol*(RSI / 200)} :: {RSI}')
                t.append(Order(sym, buy_price*1.01, -buy_vol*(RSI / 200)))
                self.prev_price[sym] = buy_price*1.01
                self.long[sym] = True
            results[sym] = t
        return results
    






     





            


