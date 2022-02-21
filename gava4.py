import asyncio
import traceback
from time import time
from datetime import datetime, timedelta
from collections import deque
import numpy as np
import pandas as pd

from ftx import FTX
from ftxbotbase import FTXBotBase

import csv

class gava4(FTXBotBase):
    ALLOW_ORDER = True
    MARKET = 'AXS-PERP'
    LOT = 10

    SEC_TO_MAIN_LOGIC_LOOP = 1
    SEC_TO_REST_POSITION_CHECK = 30
    SEC_TO_EXPIRE = 15
    SEC_TO_ORDER = 15
    next_order_time_buy = 0
    next_order_time_sell = 0
    target_profit_bandwidth = 15

    def __init__(self, api_key, api_secret):
        self.ftx = FTX(api_key=api_key, api_secret=api_secret)
        self.ftx.MARKET = self.MARKET

        loop = asyncio.get_event_loop()
        tasks = [self.ftx.ws_run(self.realtime),self.order_check_engine(),self.position_check_engine(self.SEC_TO_REST_POSITION_CHECK),self.is_tradable(5),self.run()]
        loop.run_until_complete(asyncio.wait(tasks))

    async def run(self):
        while(True):
            await self.main()
            await asyncio.sleep(self.SEC_TO_MAIN_LOGIC_LOOP)

    async def main(self):
        try:
            if self.ltp != 0 and len(self.loh5s_asks) == 5 and len(self.loh5s_bids) == 5 and len(self.exec5s_buy) == 5 and len(self.exec5s_sell) == 5:
                #np.set_printoptions(precision=4,suppress=True)
                board_size_asks = list(self.board['asks'].values())
                board_size_bids = list(self.board['bids'].values())
                np_board_size_asks = np.array(board_size_asks)
                np_board_size_bids = np.array(board_size_bids)
                np_board_csize_asks = np.cumsum(np_board_size_asks)
                np_board_csize_bids = np.cumsum(np_board_size_bids)
                #return
                board_10doller_size_asks = np_board_csize_asks[target_profit_bandwidth - 1]
                board_10doller_size_bids = np_board_csize_bids[target_profit_bandwidth - 1]
                #loh5s_max/min
                loh5s_asks_var = [self.loh5s_asks[0][0], self.loh5s_asks[1][0], self.loh5s_asks[2][0], self.loh5s_asks[3][0],self.loh5s_asks[4][0]]
                loh5s_asks_max = max(loh5s_asks_var)
                loh5s_asks_min = min(loh5s_asks_var)
                loh5s_bids_var = [self.loh5s_bids[0][0], self.loh5s_bids[1][0], self.loh5s_bids[2][0], self.loh5s_bids[3][0],self.loh5s_bids[4][0]]
                loh5s_asks_max = max(loh5s_bids_var)
                loh5s_asks_min = min(loh5s_bids_var)
                #size_estimated
                Se5s_asks_max = board_10doller_size_asks + loh5s_asks_max * 0.1
                Se5s_asks_min = board_10doller_size_asks + loh5s_asks_min * 0.1
                Se5s_bids_max = board_10doller_size_bids + loh5s_asks_max * 0.1
                Se5s_bids_min = board_10doller_size_bids + loh5s_asks_min * 0.1
                #exec5s_max/min
                exec5s_buy_var = [self.exec5s_buy[0][0], self.exec5s_buy[1][0], self.exec5s_buy[2][0], self.exec5s_buy[3][0],self.exec5s_buy[4][0]]
                exec5s_buy_max = max(exec5s_buy_var)
                exec5s_buy_min = min(exec5s_buy_var)
                exec5s_sell_var = [self.exec5s_sell[0][0], self.exec5s_sell[1][0], self.exec5s_sell[2][0], self.exec5s_sell[3][0],self.exec5s_sell[4][0]]
                exec5s_sell_max = max(exec5s_sell_var)
                exec5s_sell_min = min(exec5s_sell_var)
                #Verocity_board_consumption
                Vbc_buy_max = float(Se5s_asks_min / exec5s_buy_max)
                Vbc_sell_max = float(Se5s_bids_min / exec5s_sell_max)
                Vbc_spread = round(abs(Vbc_buy_max - Vbc_sell_max),3)

                Po_buy, Po_sell, Po_check = self.slider(Vbc_buy_max, Vbc_sell_max, Vbc_spread)

                ##place_order
                if self.ALLOW_ORDER == True:
                    if Po_check == True:
                        if self.check_orders(self.orders, 'buy') == False and self.next_order_time_buy <= time():
                            if self.positions['position'] == 'SHORT':
                                bid_size = abs(self.positions['size'])
                                bid_price = Po_buy
                            else:
                                bid_size = self.LOT
                                bid_price = Po_buy

                            await self.limit_order(side='buy', price=bid_price, size=bid_size)

                            self.next_order_time_buy = time() + self.SEC_TO_ORDER
                            print(self.orders)

                        if self.check_orders(self.orders, 'sell') == False and self.next_order_time_sell <= time():
                            if self.positions['position'] == 'LONG':
                                ask_size = abs(self.positions['size'])
                                ask_price = Po_sell
                            else:
                                ask_size = self.LOT
                                ask_price = Po_sell

                            await self.limit_order(side='sell', price=ask_price, size=ask_size)

                            self.next_order_time_sell = time() + self.SEC_TO_ORDER
                            print(self.orders)

                    elif Po_check == False:
                        print("発注不可")

        except Exception as e:
            print(e)
            print(traceback.format_exc().strip())

    #long or short
    def slider(self, Vbc_buy_max, Vbc_sell_max, Vbc_spread):
        global Po_buy
        global Po_sell
        global Po_check
        if Vbc_buy_max > 0 and Vbc_buy_max < 10000 and Vbc_sell_max > 0 and Vbc_sell_max < 10000:
            Po_check = True
            #long
            if Vbc_buy_max < 5 and Vbc_sell_max > 8 and Vbc_spread > 0.01:
                Po_buy = self.board_best_bid_price - 0.025
                Po_sell = Po_buy + 0.075
            #short
            elif Vbc_sell_max < 5 and Vbc_buy_max > 8 and Vbc_spread > 0.01:
                Po_sell = self.board_best_ask_price + 0.025
                Po_buy = Po_sell - 0.075
            else:
                Po_check = False
                Po_buy = 10
                Po_sell = 100000000
                Po_check = False
                print("out of strategy...")
        else:
            Po_check = False
            Po_buy = 10
            Po_sell = 100000000
            Po_check = False
            print("out of strategy...")

        print(Po_buy)
        print(Po_sell)
        print(Po_check)

        return Po_buy, Po_sell, Po_check


if __name__ == '__main__':

    api_key = '*******'
    api_secret = '*******'

    gava4(api_key=api_key, api_secret=api_secret)
