import requests
import json
import pandas as pd

#ftxの設定
base_url = 'https://ftx.com/api/futures'
leverage = 10
account_value = 1000
#pandasの表示設定
pd.options.display.float_format = '{:.6f}'.format
pd.set_option('display.max_rows',500)

#絞り込みの設定
target_market = 10000000
maker_fee = 0.04
interval_sec = 60

def get_markets():
    res = requests.get(base_url).json()
    res_result = res['result']
    df1 = pd.DataFrame(res_result)
    #Volume/24h > 100万ドル以上
    df2 = df1.query('volumeUsd24h > @target_market')
    #futuresだけに絞る
    df3 = df2.drop(df2.index[(df2['type'] == 'future')])
    #不必要な列情報を削除
    df4 = df3.drop(['sizeIncrement','group','changeBod','lowerBound','mark','positionLimitWeight','description','enabled','expired','expiry','imfFactor','index','moveStart','marginPrice','upperBound','perpetual','postOnly','expiryDescription','underlyingDescription','underlying','type','openInterestUsd'],axis=1)
    #volumeの昇順にする
    df5 = df4.sort_values('volumeUsd24h', ascending=False)
    #通貨名をインデックスにする
    df6 = df5.set_index('name')

    #列追加
    df6['spread'] = df6['ask'] - df6['bid']
    df6['spread_per'] = df6['spread'] / df6['bid'] *100
    df6['price_vw24h'] = df6['volumeUsd24h'] / df6['volume']

    #mm可能かどうか絞り込み
    df7_mm = df6.query('spread > priceIncrement & spread_per > @maker_fee')
    df8_mm = df7_mm.copy()
    df8_mm['tp_size'] = account_value * leverage / df8_mm['ask']
    df8_mm['tp'] = df8_mm['tp_size'] * df8_mm['spread']
    df8_mm['av_sec'] = df8_mm['volume'] / 24 / 60 / interval_sec
    df8_mm['tp2'] = df8_mm['av_sec'] / df8_mm['tp_size'] * df8_mm['tp']
    df9 = df8_mm.sort_values('tp2',ascending=False)
    print(df9)

if __name__ == '__main__':
    get_markets()
