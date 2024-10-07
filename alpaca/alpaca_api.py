import requests
import os
import json
import pandas as pd
import time

os.chdir('/Users/yujiuqiao/Desktop/Algorithmic-Trading/Alpaca')
endpoint = 'https://data.alpaca.markets'
headers = json.loads(open('keys.txt', 'r').read())

# get account information
def get_account():
    endpoint = 'https://paper-api.alpaca.markets'
    acc_url = endpoint + "/v2/account"
    response = requests.get(acc_url, headers=headers)
    return response.json()

# bar_url = "https://data.alpaca.markets/v2/stocks/bars?limit=1000&adjustment=raw&feed=sip&sort=asc"

# # specify the parameters
# params = {
#     'symbols': 'IBM,AAPL',
#     'timeframe': '15Min',
# }

# # get request
# response = requests.get(bar_url, headers=headers, params = params)
# data = response.json()

# # convert to dataframe
# temp = data['bars']['AAPL']
# df = pd.DataFrame.from_records(temp)
# df.rename({'t': 'time', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, axis=1, inplace=True)
# df['time'] = pd.to_datetime(df['time'])
# df.set_index('time', inplace=True)
# df.index = df.index.tz_convert('America/New_York')
# print(df.head())

def hist_data(symbols, timeframe, limit, start, end, after, until):
    df_data = {}
    bar_url = "https://data.alpaca.markets/v2/stocks/bars"
    params = {
        'symbols': symbols,
        'timeframe': timeframe,
        'limit': limit,
        'start': start,
        'end': end,
        'after': after,
        'until': until,
    }
    response = requests.get(bar_url, headers=headers, params=params)
    json_dump = response.json()

    if 'bars' not in json_dump:
        raise KeyError("'bars' not found in the response data")
    
    df_data = {}
    for symbol in json_dump['bars']:
        temp = json_dump['bars'][symbol]
        df = pd.DataFrame.from_records(temp)
        df.rename({'t': 'time', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, axis=1, inplace=True)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        df.index = df.index.tz_convert('America/New_York')
        df_data[symbol] = df   
    return df_data

def last_trade(symbol):
    last_trade_url = "https://data.alpaca.markets/v2/stocks/trades/latest"
    params = {
        'symbols': symbol
    }
    response = requests.get(last_trade_url, headers=headers, params=params)
    json_dump = response.json()
    # get the price and size of the latest trade
    return json_dump["trades"][symbol]["p"], json_dump["trades"][symbol]["s"]

def last_quote(symbol):
    last_quote_url = "https://data.alpaca.markets/v2/stocks/quotes/latest"
    params = {
        'symbols': symbol
    }
    response = requests.get(last_quote_url, headers=headers, params=params)
    json_dump = response.json()
    # get the ask price, ask size, bid price, bid size
    return json_dump["quotes"][symbol]["ap"], json_dump["quotes"][symbol]["as"], json_dump["quotes"][symbol]["bp"], json_dump["quotes"][symbol]["bs"]

# data_dump = hist_data('IBM,META,AAPL', '15Min', 2000, '', '', None, None)
# print(data_dump['IBM'])
# print(data_dump['META'])
# print(data_dump['AAPL'])

# # iteratively get the historical data
# tickers = ["FB", "AMZN", "GOOG"]
# starttime = time.time()
# timeout = starttime + 60 * 5
# while time.time() <= timeout:
#     for ticker in tickers:
#         print(hist_data(ticker, '1Min', 2000, '', '', None, None))
#         time.sleep(60 - ((time.time() - starttime) % 60.0))

# market order
def market_order(symbol, quantity, side, timeinforce):
    endpoint = 'https://paper-api.alpaca.markets'
    ord_url = endpoint + "/v2/orders"
    params = {
        'symbol': symbol,
        'qty': quantity,
        'side': side,
        'type': 'market',
        'time_in_force': timeinforce,
    }
    response = requests.post(ord_url, headers=headers, json=params)
    print(response.json())
    return response.json()

# limit order
def limit_order(symbol, quantity, side, timeinforce, limit_price):
    endpoint = 'https://paper-api.alpaca.markets'
    ord_url = endpoint + "/v2/orders"
    params = {
        'symbol': symbol,
        'qty': quantity,
        'side': side,
        'type': 'limit',
        'time_in_force': timeinforce,
        'limit_price': limit_price,
    }
    response = requests.post(ord_url, headers=headers, json=params)
    return response.json()

# stop order
def stop_order(symbol, quantity, side, timeinforce, stop_price):
    endpoint = 'https://paper-api.alpaca.markets'
    ord_url = endpoint + "/v2/orders"
    params = {
        'symbol': symbol,
        'qty': quantity,
        'side': side,
        'type': 'stop',
        'time_in_force': timeinforce,
        'stop_price': stop_price,
    }
    response = requests.post(ord_url, headers=headers, json=params)
    return response.json()

# stop limit order
def stop_limit_order(symbol, quantity, side, timeinforce, limit_price, stop_price):
    endpoint = 'https://paper-api.alpaca.markets'
    ord_url = endpoint + "/v2/orders"
    params = {
        'symbol': symbol,
        'qty': quantity,
        'side': side,
        'type': 'stop_limit',
        'time_in_force': timeinforce,
        'stop_price': stop_price,
        'limit_price': limit_price,
    }
    response = requests.post(ord_url, headers=headers, json=params)
    return response.json()

# trailing stop order
def trailing_stop_order(symbol, quantity, side, timeinforce, trail_price):
    endpoint = 'https://paper-api.alpaca.markets'
    ord_url = endpoint + "/v2/orders"
    params = {
        'symbol': symbol,
        'qty': quantity,
        'side': side,
        'type': 'trailing_stop',
        'time_in_force': timeinforce,
        'trail_price': trail_price,
    }
    response = requests.post(ord_url, headers=headers, json=params)
    return response.json()

# bracket order
def bracket_order(symbol, quantity, side, timeinforce, take_profit_limit_price, stop_price, stop_loss_limit_price):
    endpoint = 'https://paper-api.alpaca.markets'
    ord_url = endpoint + "/v2/orders"
    # take_profit_limit_price must be greater than base price + 0.01
    params = {
        'symbol': symbol,
        'qty': quantity,
        'side': side,
        'type': 'market',
        'time_in_force': timeinforce,
        "order_class": "bracket",
        "take_profit": {
                        "limit_price": take_profit_limit_price
                        },
        "stop_loss": {
                        "stop_price": stop_price,
                        "limit_price": stop_loss_limit_price
                    }
        }
    response = requests.post(ord_url, headers=headers, json=params)
    return response.json()

# get order list
def order_list(status, limit):
    endpoint = 'https://paper-api.alpaca.markets'
    ord_list_url = endpoint + "/v2/orders"
    params = {
        'status': status,
        'limit': limit,
    }
    response = requests.get(ord_list_url, headers=headers, params = params)
    data = response.json()
    return pd.DataFrame(data)

# sample use
# order_df = order_list('open', 10)
# order_df[order_df["symbol"] == "AAPL"]['id'].to_list()[0]

# cancel order
def order_cancel(order_id):
    if (len(order_id) <= 0): # exception handling
        raise ValueError("order_id cannot be empty")
    else:
        endpoint = 'https://paper-api.alpaca.markets'
        ord_cancel_url = endpoint + f"/v2/orders/{order_id}"
        print(ord_cancel_url)
    # cancel the most recent order
    response = requests.delete(ord_cancel_url, headers=headers)
    return response.text # return null

# replace order
def order_replace(order_id, params):
    endpoint = 'https://paper-api.alpaca.markets'
    ord_replace_url = endpoint + f"/v2/orders/{order_id}"
    response = requests.patch(ord_replace_url, headers=headers, json=params)
    return response.json()

def positions(symbol = ""):
    endpoint = 'https://paper-api.alpaca.markets'
    if len(symbol) > 1:
        pos_url = endpoint + f"/v2/positions/{symbol}"
    else:
        pos_url = endpoint + "/v2/positions"
    response = requests.get(pos_url, headers=headers)
    # positions["symbol"][] is a string! not a float
    return response.json()

# delete positions
def del_positions(symbol="", quantity=0):
    endpoint = 'https://paper-api.alpaca.markets'
    # delete a specific symbol's position
    if (len(symbol) > 1):
        pos_url = endpoint + f"/v2/positions/{symbol}"
        params = {
            'symbol': symbol,
            'qty': quantity,
        }
    # delete all positions
    else:
        pos_url = endpoint + "/v2/positions"
        params = {}
    response = requests.delete(pos_url, headers=headers,json=params)
    return response.json()
