# -*- coding: utf-8 -*-
"""
Alpaca API - MACD + stochastic strategy bactesting using Intraday KPIs (V2 API)

@author: Mayank Rasu (http://rasuquant.com/wp/)
"""

import os
import json
from alpaca_trade_api.rest import REST, TimeFrame
from copy import deepcopy
import numpy as np
import pandas as pd

os.chdir("/Users/yujiuqiao/Desktop/CQF/CQF_Project/alpaca")

endpoint = "https://data.alpaca.markets/v2"
headers = json.loads(open("keys.txt",'r').read())
tickers = ["SQQQ", "TQQQ", "IBIT", "BITI", "SPY"]

def hist_data(symbols, start_date ="2021-12-01", timeframe="Minute"):
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

def MACD(df_dict, a=12 ,b=26, c=9):
    """function to calculate MACD
       typical values a(fast moving average) = 12; 
                      b(slow moving average) =26; 
                      c(signal line ma window) =9"""
    for df in df_dict:
        df_dict[df]["ma_fast"] = df_dict[df]["close"].ewm(span=a, min_periods=a).mean()
        df_dict[df]["ma_slow"] = df_dict[df]["close"].ewm(span=b, min_periods=b).mean()
        df_dict[df]["macd"] = df_dict[df]["ma_fast"] - df_dict[df]["ma_slow"]
        df_dict[df]["signal"] = df_dict[df]["macd"].ewm(span=c, min_periods=c).mean()
        df_dict[df].drop(["ma_fast","ma_slow"], axis=1, inplace=True)

def stochastic(df_dict, lookback=14, k=3, d=3):
    """function to calculate Stochastic Oscillator
       lookback = lookback period
       k and d = moving average window for %K and %D"""
    for df in df_dict:
        df_dict[df]["HH"] = df_dict[df]["high"].rolling(lookback).max()
        df_dict[df]["LL"] = df_dict[df]["low"].rolling(lookback).min()
        df_dict[df]["%K"] = (100 * (df_dict[df]["close"] - df_dict[df]["LL"])/(df_dict[df]["HH"]-df_dict[df]["LL"])).rolling(k).mean()
        df_dict[df]["%D"] = df_dict[df]["%K"].rolling(d).mean()
        df_dict[df].drop(["HH","LL"], axis=1, inplace=True)
 

def winRate(DF):
    "function to calculate win rate of intraday trading strategy"
    df = DF["return"]
    pos = df[df>1]
    neg = df[df<1]
    return (len(pos)/len(pos+neg))*100

def meanretpertrade(DF):
    df = DF["return"]
    df_temp = (df-1).dropna()
    return df_temp[df_temp!=0].mean()

def meanretwintrade(DF):
    df = DF["return"]
    df_temp = (df-1).dropna()
    return df_temp[df_temp>0].mean()

def meanretlostrade(DF):
    df = DF["return"]
    df_temp = (df-1).dropna()
    return df_temp[df_temp<0].mean()

def maxconsectvloss(DF):
    df = DF["return"]
    df_temp = df.dropna(axis=0)
    df_temp2 = np.where(df_temp<1,1,0)
    count_consecutive = []
    seek = 0
    for i in range(len(df_temp2)):
        if df_temp2[i] == 0:
            if seek > 0:
                count_consecutive.append(seek)
            seek = 0
        else:
            seek+=1
    if len(count_consecutive) > 0:
        return max(count_consecutive)
    else:
        return 0

#extract and store historical data in dataframe
historicalData = hist_data(tickers, start_date ="2021-12-01", timeframe="Minute") 

    
#####################################   BACKTESTING   ##################################
ohlc_dict = deepcopy(historicalData)
stoch_signal = {}
tickers_signal = {}
tickers_ret = {}
trade_count = {}
trade_data = {}
hwm = {}
stochastic(ohlc_dict)
MACD(ohlc_dict)


for ticker in tickers:
    print("Calculating MACD & Stochastics for ",ticker)
    ohlc_dict[ticker].dropna(inplace=True)
    stoch_signal[ticker] = ""
    trade_count[ticker] = 0
    tickers_signal[ticker] = ""
    hwm[ticker] = 0
    tickers_ret[ticker] = [0]
    trade_data[ticker] = {}
    
for ticker in tickers:
    print("Calculating daily returns for ",ticker)
    for i in range(1,len(ohlc_dict[ticker])-1):
        if ohlc_dict[ticker]["%K"].iloc[i] < 20:
            stoch_signal[ticker] = "oversold"
        elif ohlc_dict[ticker]["%K"][i] > 80:
            stoch_signal[ticker] = "overbought"
        
        if tickers_signal[ticker] == "":
            tickers_ret[ticker].append(0)
            if ohlc_dict[ticker]["macd"].iloc[i]> ohlc_dict[ticker]["signal"].iloc[i] and \
               ohlc_dict[ticker]["macd"].iloc[i-1]< ohlc_dict[ticker]["signal"].iloc[i-1] and \
               stoch_signal[ticker]=="oversold":
                   tickers_signal[ticker] = "Buy"
                   trade_count[ticker]+=1
                   trade_data[ticker][trade_count[ticker]] = [ohlc_dict[ticker]["open"].iloc[i+1]]
                   hwm[ticker] = ohlc_dict[ticker]["open"].iloc[i+1]
                     
        elif tickers_signal[ticker] == "Buy":
            if ohlc_dict[ticker]["low"][i]<0.985*hwm[ticker]:
                tickers_signal[ticker] = ""
                trade_data[ticker][trade_count[ticker]].append(0.985*hwm[ticker])
                trade_count[ticker]+=1
                tickers_ret[ticker].append((0.985*hwm[ticker]/ohlc_dict[ticker]["close"].iloc[i-1])-1)
            else:
                hwm[ticker] = max(hwm[ticker],ohlc_dict[ticker]["high"][i])
                tickers_ret[ticker].append((ohlc_dict[ticker]["close"].iloc[i]/ohlc_dict[ticker]["close"].iloc[i-1])-1)
                            
    if trade_count[ticker]%2 != 0:
        trade_data[ticker][trade_count[ticker]].append(ohlc_dict[ticker]["close"].iloc[i+1])
    
    tickers_ret[ticker].append(0) #since we are removing the last row
    ohlc_dict[ticker]["ret"] = np.array(tickers_ret[ticker])

# calculating overall strategy's KPIs
trade_df = {}
overall_return = 0
for ticker in tickers:
    trade_df[ticker] = pd.DataFrame(trade_data[ticker]).T
    trade_df[ticker].columns = ["trade_entry_pr","trade_exit_pr"]
    trade_df[ticker]["return"] = trade_df[ticker]["trade_exit_pr"]/trade_df[ticker]["trade_entry_pr"]
    print("total return {} = {}".format(ticker,trade_df[ticker]["return"].cumprod().iloc[-1] - 1))
    overall_return+= (1/len(tickers))*(trade_df[ticker]["return"].cumprod().iloc[-1] - 1)

print("Overall Return of Strategy = {}".format(overall_return))
  
#calculating individual stock's KPIs
win_rate = {}
mean_ret_pt = {}
mean_ret_pwt = {}
mean_ret_plt = {}
max_cons_loss = {}
for ticker in tickers:
    print("calculating intraday KPIs for ",ticker)
    win_rate[ticker] =  winRate(trade_df[ticker])      
    mean_ret_pt[ticker] =  meanretpertrade(trade_df[ticker])
    mean_ret_pwt[ticker] =  meanretwintrade(trade_df[ticker])
    mean_ret_plt[ticker] =  meanretlostrade(trade_df[ticker])
    max_cons_loss[ticker] =  maxconsectvloss(trade_df[ticker])

KPI_df = pd.DataFrame([win_rate,mean_ret_pt,mean_ret_pwt,mean_ret_plt,max_cons_loss],
                      index=["Win Rate","Mean Return Per Trade","MR Per WR", "MR Per LR", "Max Cons Loss"])      
print(KPI_df.T)
    