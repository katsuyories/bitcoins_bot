import websocket
import json
import sys
import os
import time
import threading
from collections import deque
from datetime import datetime, timedelta
import pandas as pd
import pybitflyer


class kotukotukun:
    def __init__(self):
        self.API_key="*******"
        self.API_secret="*******"
        self.exec_bitmex = deque(maxlen=12)
        self.bitflyer_ltp = deque(maxlen=1)

    def store_bitmex_data(self):
        # define_websocket
        def on_open_bitmex(ws_bitmex):
            ws_bitmex.send(json.dumps({"op": "subscribe", "args": "trade:XBTUSD"}))

        def on_message_bitmex(ws_bitmex, message):
            message = json.loads(message)
            data = message["data"]
            self.exec_bitmex = [i["side"] for i in data]

        def on_error_bitmex(ws_bitmex, error):
            print("disconnected from bitmex_streaming_server")

        def on_close_bitmex(ws_bitmex):
            try:
                print("disconnected from bitmex_streaming_server. restarting websocket_app...")
                ws_bitmex = websocket.WebSocketApp("wss://www.bitmex.com/realtime", on_open=on_open_bitmex, on_message=on_message_bitmex, on_error=on_error_bitmex, on_close=on_close_bitmex)

                ws_bitmex.run_forever()

            except KeyboardInterrupt:
                print("disconnected from bitmex_streaming_server")
                sys.exit()

        ws_bitmex = websocket.WebSocketApp("wss://www.bitmex.com/realtime", on_open=on_open_bitmex, on_message=on_message_bitmex,  on_error=on_error_bitmex, on_close=on_close_bitmex)
        ws_bitmex.run_forever()

    def get_bitflyer_ltp(self):
        #callback_functions
        def on_open_bitflyer(ws_bitflyer):
            ws_bitflyer.send(json.dumps({"method":"subscribe", "params":{"channel":"lightning_ticker_FX_BTC_JPY"}}))

        def on_message_bitflyer(ws_bitflyer, message):
            temp_data = json.loads(message)['params']['message']
            ltp = temp_data['ltp']
            self.bitflyer_ltp.append(ltp)

        ws_bitflyer = websocket.WebSocketApp("wss://ws.lightstream.bitflyer.com/json-rpc", on_open=on_open_bitflyer, on_message=on_message_bitflyer)
        ws_bitflyer.run_forever()



    def arbitrager(self):

        while True:
            # the deque is stored from bitmex_streaming_server.
            # pandas_dataframe is appended from the deque.
            exec_bitmex = list(self.exec_bitmex)
            print(exec_bitmex)
            print(len(exec_bitmex))

            ##statical_functions
            """
            #each_side_volume
            temp_buy = df_bitmex[df_bitmex['side'] == 'Buy']
            buy_vol = temp_buy['size'] * temp_buy['price']
            buy_total = buy_vol.sum()

            temp_sell = df_bitmex[df_bitmex['side'] == 'Sell']
            sell_vol = temp_sell['size'] * temp_sell['price']
            sell_total = sell_vol.sum()

            print("buy_vol :" + str(buy_total), "sell_vol :" + str(sell_total))
            print("buy :" + str(len(temp_buy)) + " sell :" + str(len(temp_sell)))
            """

            #self.bitflyer_price convert deque to int
            temp_bitflyer_ltp = list(map(int, self.bitflyer_ltp))
            if temp_bitflyer_ltp :
                bitflyer_ltp = temp_bitflyer_ltp[0]
                print(str(bitflyer_ltp) + "yen")

            time.sleep(0.2)

            #order
            api = pybitflyer.API(api_key=self.API_key, api_secret=self.API_secret)

            if len(exec_bitmex) > 11 :
                #long
                if exec_bitmex in "Buy" :
                    side1 == "BUY"
                    side2 == "SELL"
                close_price = bitflyer_ltp - 20
                order_long = api.sendparentorder(order_method = "IFD", minute_to_expire = 4, time_in_force = "GTC", parameters = [{"product_code": "FX_BTC_JPY",  "condition_type": "LIMIT", "side": side1, "price": bitflyer_ltp, "size": 0.05},{"product_code": "FX_BTC_JPY", "condition_type": "LIMIT", "side": side2, "price": close_price, "size": 0.05}])
                print("ordered. side :long win_price :" + str(close_price))

                time.sleep(10)

            else:
                continue

def ws_client_run():
    # create instance
    ktk = kotukotukun()
    # set up thread0(store_bitmex_data)
    thread0 = threading.Thread(target=ktk.store_bitmex_data)
    # set up thread1(bf_ltp)
    thread1 = threading.Thread(target=ktk.get_bitflyer_ltp)
    # set up deamon_thread(arbitrager)
    thread2 = threading.Thread(target=ktk.arbitrager)
    thread2.setDaemon(True)

    # run
    thread0.start()
    thread1.start()
    thread2.start()


if __name__ == '__main__':
    ws_client_run()
