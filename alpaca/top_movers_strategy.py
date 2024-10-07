import os
import requests
import json
from alpaca.data import CryptoHistoricalDataClient, StockHistoricalDataClient, OptionHistoricalDataClient
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import REST, TimeFrame
import websocket
import datetime as dt
import time
import threading

os.chdir("/Users/yujiuqiao/Desktop/Algorithmic-Trading/alpaca")

endpoint = "https://data.alpaca.markets/v2"
headers = json.loads(open("keys.txt",'r').read())
api = tradeapi.REST(headers["APCA-API-KEY-ID"], headers["APCA-API-SECRET-KEY"], base_url='https://paper-api.alpaca.markets')

# tickers to subscribe
tickers = ['AMZN','AAPL','GOOG','CSCO','ADBE',
           'NVDA','NFLX','PYPL','AMGN','AVGO',
           'TXN','CHTR','QCOM','GILD', 'FISV']
ltp = {} # last traded price
prev_close = {} # previous close price
perc_change = {} # percentage change
traded_tickers = [] #storing tickers which have been traded and therefore to be excluded
max_pos = 3000 #max position size for each ticker

def historical_data(symbols, start_date ="2024-08-01", timeframe="Minute"):
    """
    returns historical bar data for a list of tickers e.g. symbols = ["MSFT,AMZN,GOOG"]
    """
    df_data = {}
    api = REST(headers["APCA-API-KEY-ID"], headers["APCA-API-SECRET-KEY"], base_url=endpoint)
    for ticker in symbols:
        if timeframe == "Minute":
            df_data[ticker] = api.get_bars(ticker, TimeFrame.Minute, start_date, adjustment='all').df
        elif timeframe == "Hour":
            df_data[ticker] = api.get_bars(ticker, TimeFrame.Hour, start_date, adjustment='all').df
        else:
            df_data[ticker] = api.get_bars(ticker, TimeFrame.Day, start_date, adjustment='all').df
    return df_data

data_dump = historical_data(tickers, timeframe="Day")
for ticker in tickers:
    prev_close[ticker] = data_dump[ticker]["close"].iloc[-2] # note this value!!!
    ltp[ticker] = data_dump[ticker]["close"].iloc[-1]
    perc_change[ticker] = 0

def on_open(ws):
    auth = {
        "action": "auth", 
        "key": headers["APCA-API-KEY-ID"], 
        "secret": headers["APCA-API-SECRET-KEY"]
    }
    ws.send(json.dumps(auth))
    message = {
        "action":"subscribe",
        "trades":tickers
    }  
    ws.send(json.dumps(message))
 
def on_message(ws, message):
    #print(message)
    tick = json.loads(message)
    tkr = tick[0]["S"]
    ltp[tkr] = float(tick[0]["p"])
    # calculate the percentage change
    perc_change[tkr] = round((ltp[tkr]/prev_close[tkr] - 1)*100,2)   
    
def connect():
    ws = websocket.WebSocketApp("wss://stream.data.alpaca.markets/v2/iex", on_open=on_open, on_message=on_message)
    ws.run_forever()

# calculate the position size
def pos_size(ticker):
    return max(1,int(max_pos/ltp[ticker]))

# trading signal
# top movers strategy
def signal(traded_tickers):
    #print(traded_tickers)
    for ticker, pc in perc_change.items():
        #   (ticker, pc)
        if pc > 2 and ticker not in traded_tickers:
            api.submit_order(ticker, pos_size(ticker), "buy", "market", "ioc")
            time.sleep(2)
            try:
                filled_qty = api.get_position(ticker).qty
                time.sleep(1)
                api.submit_order(ticker, int(filled_qty), "sell", "trailing_stop", "day", trail_percent = "1.5")
                traded_tickers.append(ticker)
            except Exception as e:
                print(ticker, e)
        if pc < -2 and ticker not in traded_tickers:
            api.submit_order(ticker, pos_size(ticker), "sell", "market", "ioc")
            time.sleep(2)
            try:
                filled_qty = api.get_position(ticker).qty
                time.sleep(1)
                api.submit_order(ticker, -1*int(filled_qty), "buy", "trailing_stop", "day", trail_percent = "1.5")
                traded_tickers.append(ticker)
            except Exception as e:
                print(ticker, e)

con_thread = threading.Thread(target=connect)
con_thread.start()

starttime = time.time()
timeout = starttime + 60*5 # 5 minutes time out
while time.time() <= timeout:
    for ticker in tickers:
        print("percent change for {} = {}".format(ticker, perc_change[ticker]))
    time.sleep(60 - ((time.time() - starttime) % 60)) # print every 1 minute

#closing all positions and cancelling all orders at the end of the strategy  
api.close_all_positions()
api.cancel_all_orders()
time.sleep(5)