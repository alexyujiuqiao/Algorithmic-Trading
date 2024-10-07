import os
import requests
import json
import pandas as pd
from alpaca.data import CryptoHistoricalDataClient, StockHistoricalDataClient, OptionHistoricalDataClient
import websocket
import sqlite3
import datetime as dt
import dateutil.parser

os.chdir("/Users/yujiuqiao/Desktop/Algorithmic-Trading/alpaca")

endpoint = "wss://stream.data.alpaca.markets/v2/iex"
headers = json.loads(open("keys.txt", "r").read())
# trade and quote tickers
trade_tickers = ["AAPL", "TSLA", "GOOG", "AMZN"]
quote_tickers = ["AAPL", "TSLA", "GOOG", "AMZN","META"]

db1 = sqlite3.connect("trades_ticks.db")
db2 = sqlite3.connect("quotes_ticks.db")

# create sql tables
def create_tables(db, tickers, tick_type):
    c = db.cursor()
    if tick_type == "trades":
        for ticker in tickers:
            c.execute("CREATE TABLE IF NOT EXISTS {} (timestamp datetime primary key, price real(15,5), volume integer)".format(ticker))
    if tick_type == "quotes":
        for ticker in tickers:
            c.execute("CREATE TABLE IF NOT EXISTS {} (timestamp datetime primary key, bid_price real(15,5), ask_price real(15,5), bid_volume integer, ask_volume integer)".format(ticker))
    try:
        db.commit()
    except:
        db.rollback()

create_tables(db1,trade_tickers,"trades")
create_tables(db2,quote_tickers,"quotes")

# convert sql data to pandas dataframe
# fetch data from sql tables
def get_bars(db, ticker):
    data = pd.read_sql("SELECT * FROM {}".format(ticker), con=db)
    data.set_index(['timestamp'], inplace=True)
    data.index = pd.to_datetime(data.index)
    price_ohlc = data['price'].resample('1Min').ohlc().dropna()
    price_ohlc.columns = ['open', 'high', 'low', 'close']
    vol_ohlc = data['volume'].resample('1Min').apply({'volume':'sum'}).dropna()
    df = price_ohlc.merge(vol_ohlc, left_index=True, right_index=True)
    return df

# insert ticks into the tables
def insert_ticks(tick):
    if tick[0]["T"] == "q":
        c = db2.cursor()
        for ms in range(100):
            try:        
                tabl = tick[0]["S"]
                vals = [dateutil.parser.isoparse(tick[0]["t"])+dt.timedelta(microseconds=ms),tick[0]["bp"],tick[0]["ap"],tick[0]["bs"],tick[0]["as"]]
                query = "INSERT INTO {}(timestamp,bid_price,ask_price,bid_volume,ask_volume) VALUES (?,?,?,?,?)".format(tabl)
                c.execute(query,vals)
                break
            except Exception as e:
                print(e)
        try:
            db2.commit()
        except:
            db2.rollback()
            
    if tick[0]["T"] == "t":
        c = db1.cursor()
        for ms in range(100):
            try:        
                tabl = tick[0]["S"]
                vals = [dateutil.parser.isoparse(tick[0]["t"])+dt.timedelta(microseconds=ms),tick[0]["p"],tick[0]["s"]]
                query = "INSERT INTO {}(timestamp,price,volume) VALUES (?,?,?)".format(tabl)
                c.execute(query,vals)
                break
            except Exception as e:
                print(e)
        try:
            db1.commit()
        except:
            db1.rollback()

def on_open(ws):
    auth_data = {
        "action": "auth",
        "key": headers["APCA-API-KEY-ID"],
        "secret": headers["APCA-API-SECRET-KEY"],
    }
    ws.send(json.dumps(auth_data))

    message = {
        "action": "subscribe",
        "trades": trade_tickers,
        "quotes": quote_tickers,
    }
    ws.send(json.dumps(message))

def on_message(ws, message):
    print(message)
    data = json.loads(message)
    insert_ticks(data)

def on_error(ws, error):
    print("Error encountered:", error)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed with code:", close_status_code, "and message:", close_msg)

# market data streaming
ws = websocket.WebSocketApp("wss://stream.data.alpaca.markets/v2/iex", on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
ws.run_forever()