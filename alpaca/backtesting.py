import os
import json
from alpaca_trade_api.rest import REST, TimeFrame
import numpy as np

os.chdir("/Users/yujiuqiao/Desktop/Algorithmic-Trading/alpaca")

endpoint = "https://data.alpaca.markets/v2"
headers = json.loads(open("keys.txt",'r').read())

# get historical ticker bar data
def hist_data(symbols, start_date, timeframe):
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
        
# get historical data for AAPL, AMZN, NVDA from 2024-07-01
data_dump = hist_data(["AAPL","AMZN","NVDA"], start_date ="2024-07-01", timeframe="Hour") 

#adding return column to each bar dataframe - assuming long and hold strategy
for df in data_dump:
    data_dump[df]["return"] = data_dump[df]["close"].pct_change()

# calculate the Cumulative Annual Growth Rate
def CAGR(df_dict):
    cagr = {}
    for df in df_dict:
        abs_return = (1 + df_dict[df]["return"]).cumprod().iloc[-1]
        n = len(df_dict[df]) / 252
        cagr[df] = (abs_return)**(1/n) - 1
    return cagr

# calculate annual volatility
def volatility(df_dict):
    vol = {}
    for df in df_dict:
        vol[df] = df_dict[df]["return"].std() * np.sqrt(252)
    return vol

# calculate sharpe ratio
# rf rate is the risk free rate
def sharpe(df_dict, rf_rate):
    sharpe = {}
    cagr = CAGR(df_dict)
    vol = volatility(df_dict)
    for df in df_dict:
        sharpe[df] = (cagr[df] - rf_rate)/vol[df]
    return sharpe

# calculate maximum drawdown
def max_drawdown(df_dict):
    max_drawdown = {}
    for df in df_dict:
        df_dict[df]["cum_return"] = (1 + df_dict[df]["return"]).cumprod() # cumulative return
        df_dict[df]["cum_max"] = df_dict[df]["cum_return"].cummax() # cumulative maximum
        df_dict[df]["drawdown"] = df_dict[df]["cum_max"] - df_dict[df]["cum_return"] # drawdown
        df_dict[df]["drawdown_pct"] = df_dict[df]["drawdown"] / df_dict[df]["cum_max"] # drawdown percentage
        max_drawdown[df] = df_dict[df]["drawdown_pct"].max()
        df_dict[df].drop(["cum_return","cum_max","drawdown","drawdown_pct"], axis=1, inplace=True)
    return max_drawdown