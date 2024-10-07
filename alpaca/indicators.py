import os
import json
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
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

# function to calculate MACD
# typical values a(fast moving average) = 12; 
# b(slow moving average) =26; 
# c(signal line moving average window) =9
def MACD(df_dict, a=12 ,b=26, c=9):
    for df in df_dict:
        df_dict[df]["ma_fast"] = df_dict[df]["close"].ewm(span=a, min_periods=a).mean()
        df_dict[df]["ma_slow"] = df_dict[df]["close"].ewm(span=b, min_periods=b).mean()
        df_dict[df]["macd"] = df_dict[df]["ma_fast"] - df_dict[df]["ma_slow"]
        df_dict[df]["signal"] = df_dict[df]["macd"].ewm(span=c, min_periods=c).mean()
        df_dict[df].drop(["ma_fast","ma_slow"], axis=1, inplace=True)
    return df_dict

# function to calculate True Range and Average True Range
def ATR(df_dict, n=14):
    for df in df_dict:
        df_dict[df]["H-L"] = df_dict[df]["high"] - df_dict[df]["low"]
        df_dict[df]["H-PC"] = abs(df_dict[df]["high"] - df_dict[df]["close"].shift(1))
        df_dict[df]["L-PC"] = abs(df_dict[df]["low"] - df_dict[df]["close"].shift(1))
        df_dict[df]["TR"] = df_dict[df][["H-L","H-PC","L-PC"]].max(axis=1, skipna=False)
        df_dict[df]["ATR"] = df_dict[df]["TR"].ewm(span=n, min_periods=n).mean()
        df_dict[df].drop(["H-L","H-PC","L-PC","TR"], axis=1, inplace=True)
    return df_dict

# function to calculate Bollinger Band
def bollBand(df_dict, n=20):
    for df in df_dict:
        df_dict[df]["MB"] = df_dict[df]["close"].rolling(n).mean()
        df_dict[df]["UB"] = df_dict[df]["MB"] + 2 * df_dict[df]["close"].rolling(n).std(ddof=0) # take the standard deviation of the population and not sample
        df_dict[df]["LB"] = df_dict[df]["MB"] - 2 * df_dict[df]["close"].rolling(n).std(ddof=0)
        df_dict[df]["BB_Width"] = df_dict[df]["UB"] -  df_dict[df]["LB"] 

# calculate relative strength index (RSI)
def RSI(df_dict, n=14):
    for df in df_dict:
        df_dict[df]["change"] = df_dict[df]["close"] - df_dict[df]["close"].shift(1)
        df_dict[df]["gain"] = np.where(df_dict[df]["change"]>=0, df_dict[df]["change"], 0)
        df_dict[df]["loss"] = np.where(df_dict[df]["change"]<0, -1*df_dict[df]["change"], 0)
        df_dict[df]["avgGain"] = df_dict[df]["gain"].ewm(alpha=1/n, min_periods=n).mean()
        df_dict[df]["avgLoss"] = df_dict[df]["loss"].ewm(alpha=1/n, min_periods=n).mean()
        df_dict[df]["rs"] = df_dict[df]["avgGain"]/df_dict[df]["avgLoss"]
        df_dict[df]["rsi"] = 100 - (100/ (1 + df_dict[df]["rs"]))
        df_dict[df].drop(["change","gain","loss","avgGain","avgLoss","rs"], axis=1, inplace=True)
    return df_dict

# calculate Average Directional Movement Index (ADX)
def ADX(df_dict, n=20):
    for df in df_dict:
        ATR(df_dict, n)
        df_dict[df]["upmove"] = df_dict[df]["high"] - df_dict[df]["high"].shift(1) # upward movement
        df_dict[df]["downmove"] = df_dict[df]["low"].shift(1) - df_dict[df]["low"] # downward movement
        df_dict[df]["+dm"] = np.where((df_dict[df]["upmove"]>df_dict[df]["downmove"]) & (df_dict[df]["upmove"] >0), df_dict[df]["upmove"], 0) # positive directional movement
        df_dict[df]["-dm"] = np.where((df_dict[df]["downmove"]>df_dict[df]["upmove"]) & (df_dict[df]["downmove"] >0), df_dict[df]["downmove"], 0) # negative directional movement
        df_dict[df]["+di"] = 100 * (df_dict[df]["+dm"]/df_dict[df]["ATR"]).ewm(alpha=1/n, min_periods=n).mean()
        df_dict[df]["-di"] = 100 * (df_dict[df]["-dm"]/df_dict[df]["ATR"]).ewm(alpha=1/n, min_periods=n).mean()
        # ADX, Average Directional Movement Index
        df_dict[df]["ADX"] = 100* abs((df_dict[df]["+di"] - df_dict[df]["-di"])/(df_dict[df]["+di"] + df_dict[df]["-di"])).ewm(alpha=1/n, min_periods=n).mean()
        df_dict[df].drop(["upmove","downmove","+dm","-dm","+di","-di"], axis=1, inplace=True)
    return df_dict

# function to calculate Stochastic Oscillator
# lookback = lookback period
# k and d = moving average window for %K and %D
def stochastic(df_dict, lookback=14, k=3, d=3):
    for df in df_dict:
        df_dict[df]["HH"] = df_dict[df]["high"].rolling(lookback).max() # highest high over lookback period
        df_dict[df]["LL"] = df_dict[df]["low"].rolling(lookback).min() # lowest low over lookback period
        df_dict[df]["%K"] = (100 * (df_dict[df]["close"] - df_dict[df]["LL"])/(df_dict[df]["HH"]-df_dict[df]["LL"])).rolling(k).mean() # %K
        df_dict[df]["%D"] = df_dict[df]["%K"].rolling(d).mean() # %D
        df_dict[df].drop(["HH","LL"], axis=1, inplace=True)
    return df_dict

print(stochastic(data_dump))