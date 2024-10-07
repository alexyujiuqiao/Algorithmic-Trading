import os
import json
from alpaca_trade_api.rest import REST, TimeFrame
from copy import deepcopy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

os.chdir("/Users/yujiuqiao/Desktop/Algorithmic-Trading/alpaca")

endpoint = "https://data.alpaca.markets/v2"
headers = json.loads(open("keys.txt",'r').read())
# tickers = ['AMZN','INTC','MSFT','AAPL','GOOG','CSCO','CMCSA','GILD','PYPL','NFLX']
tickers = ['AMZN','INTC','MSFT','AAPL','GOOG','CSCO','CMCSA'
           ,'NFLX','PYPL','AMGN','AVGO','TXN','CHTR','QCOM','GILD']

# get historical ticker bar data
def hist_data(symbols, start_date ="2024-06-01", timeframe="Minute"):
    df_data = {}
    api = REST(headers["APCA-API-KEY-ID"], headers["APCA-API-SECRET-KEY"], base_url=endpoint)
    for ticker in symbols:
        if timeframe == "Minute":
            df_data[ticker] = api.get_bars(ticker, "15Min", start_date, adjustment='all').df
        elif timeframe == "Hour":
            df_data[ticker] = api.get_bars(ticker, TimeFrame.Hour, start_date, adjustment='all').df
        else:
            df_data[ticker] = api.get_bars(ticker, TimeFrame.Day, start_date, adjustment='all').df
    return df_data

# function to calculate Exponential Moving Average (EMA)
# span = window size, take 20 days
def EMA(df_dict, span):
    for df in df_dict:
        df_dict[df]["ema"] = df_dict[df]["close"].ewm(span=span, adjust=False).mean()
    return df_dict

def diff(df_dict):
    for df in df_dict:
        df_dict[df]["diff"] = df_dict[df]["close"] - df_dict[df]["ema"]
    return df_dict

# kalman filter function
# data is the historical market data close columns
def kalman_filter(data): 
    length = len(data)
    filter_data = np.zeros(length)  # State estimate
    P = np.zeros(length)  # Estimate covariance
    Q = 1e-5        # Process noise covariance
    R = 1e-2        # Measurement noise covariance
    K = np.zeros(length)  # Kalman Gain
    filter_data[0] = data[0]
    P[0] = 1.0

    for k in range(1, length): # iteratively
        filter_data[k] = filter_data[k-1] # State prediction
        P[k] = P[k-1] + Q # covariance prediction
        K[k] = P[k] / (P[k] + R) # Kalman Gain
        filter_data[k] = filter_data[k] + K[k] * (data[k] - filter_data[k]) # status update
        P[k] = (1 - K[k]) * P[k] # covariance update
    return filter_data

# calculate relative strength index (RSI)
def RSI(df_dict, n=14):
    for df in df_dict:
        df_dict[df]["change"] = df_dict[df]["close"] - df_dict[df]["close"].shift(1)
        df_dict[df]["gain"] = np.where(df_dict[df]["change"] >= 0, df_dict[df]["change"], 0)
        df_dict[df]["loss"] = np.where(df_dict[df]["change"] < 0, -1*df_dict[df]["change"], 0)
        df_dict[df]["avgGain"] = df_dict[df]["gain"].ewm(alpha = 1 / n, min_periods=n).mean()
        df_dict[df]["avgLoss"] = df_dict[df]["loss"].ewm(alpha = 1 / n, min_periods=n).mean()
        df_dict[df]["rs"] = df_dict[df]["avgGain"]/df_dict[df]["avgLoss"]
        df_dict[df]["rsi"] = 100 - (100 / (1 + df_dict[df]["rs"]))
        df_dict[df].drop(["change","gain","loss","avgGain","avgLoss","rs"], axis=1, inplace=True)
    return df_dict

# # function to calculate Moving Average Convergence / Divergence (MACD)
# # typical values a(fast moving average) = 12; 
# # b(slow moving average) = 26; 
# # c(signal line ma window) =9
# def MACD(df_dict, a=12 ,b=26, c=9):
#     for df in df_dict:
#         df_dict[df]["ma_fast"] = df_dict[df]["close"].ewm(span=a, min_periods=a).mean()
#         df_dict[df]["ma_slow"] = df_dict[df]["close"].ewm(span=b, min_periods=b).mean()
#         df_dict[df]["macd"] = df_dict[df]["ma_fast"] - df_dict[df]["ma_slow"]
#         df_dict[df]["signal"] = df_dict[df]["macd"].ewm(span=c, min_periods=c).mean()
#         df_dict[df].drop(["ma_fast","ma_slow"], axis=1, inplace=True)

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

# # function to calculate Stochastic Oscillator
# # lookback = lookback period
# # k and d = moving average window for %K and %D
# def stochastic(df_dict, lookback=14, k=3, d=3):
#     for df in df_dict:
#         df_dict[df]["HH"] = df_dict[df]["high"].rolling(lookback).max() # highest high over lookback period
#         df_dict[df]["LL"] = df_dict[df]["low"].rolling(lookback).min() # lowest low over lookback period
#         df_dict[df]["%K"] = (100 * (df_dict[df]["close"] - df_dict[df]["LL"]) / (df_dict[df]["HH"]-df_dict[df]["LL"])).rolling(k).mean()
#         df_dict[df]["%D"] = df_dict[df]["%K"].rolling(d).mean()
#         df_dict[df].drop(["HH","LL"], axis=1, inplace=True)

def winRate(DF):
    "function to calculate win rate of intraday trading strategy"
    df = DF["return"]
    pos = df[df > 1]
    neg = df[df < 1]
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
    df_temp2 = np.where(df_temp < 1,1,0)
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

# calculate the Cumulative Annual Growth Rate
def CAGR(df_dict):
    df = df_dict.copy()
    df = df[df["return"] <= 2]
    df["cum_return"] = (1 + df["return"]).cumprod()
    n = len(df) / (252 * 26) #6.5 one-hour candles each trading day
    cagr = (df["cum_return"].iloc[-1])**(1 / n) - 1
    return cagr

# calculate annual volatility
def volatility(df_dict):
    df = df_dict.copy()
    df = df[df["return"] <= 2]
    vol = df["return"].std() * np.sqrt(252 * 26)
    return vol

# calculate sharpe ratio
# rf rate is the risk free rate
def sharpe(df_dict, rf_rate):
    df = df_dict.copy()
    df = df[df["return"] <= 2]
    sharpe = (CAGR(df) - rf_rate) / volatility(df)
    return sharpe

# calculate maximum drawdown
def max_drawdown(df_dict):
    df = df_dict.copy()
    df["cum_return"] = (1 + df["return"]).cumprod() # cumulative return
    df["cum_roll_max"] = df["cum_return"].cummax() # cumulative maximum
    df["drawdown"] = df["cum_roll_max"] - df["cum_return"] # drawdown
    df["drawdown_pct"] = df["drawdown"] / df["cum_roll_max"] # drawdown percentage
    max_drawdown = df["drawdown_pct"].max()
    return max_drawdown

#extract and store historical data in dataframe
historicalData = hist_data(tickers, start_date ="2023-08-01", timeframe="Minute") 

#####################################   BACKTESTING  INTRADAY ##################################
ohlc_dict = deepcopy(historicalData)
stoch_signal = {}
adx_signal = {}
tickers_signal = {}
tickers_ret = {}
trade_count = {}
long_data = {}
short_data = {}
hwm = {}

EMA(ohlc_dict, 5)
diff(ohlc_dict)
ADX(ohlc_dict)
RSI(ohlc_dict)

for ticker in tickers:
    ohlc_dict[ticker].dropna(inplace=True)
    trade_count[ticker] = 0
    tickers_signal[ticker] = ""
    stoch_signal[ticker] = ""
    hwm[ticker] = 0
    tickers_ret[ticker] = [0]
    long_data[ticker] = {}
    short_data[ticker] = {}

for ticker in tickers:
    ohlc_dict[ticker]["kal"] = kalman_filter(ohlc_dict[ticker]["close"].values)
    for i in range(1,len(ohlc_dict[ticker]) - 1):
        z_threshold = 0.02
        if ohlc_dict[ticker]["rsi"].iloc[i] < 20 and \
            ohlc_dict[ticker]["ADX"].iloc[i] > 25:
            stoch_signal[ticker] = "oversold"
        elif ohlc_dict[ticker]["rsi"].iloc[i] > 75:
            stoch_signal[ticker] = "overbought"
        
        if tickers_signal[ticker] == "":
            tickers_ret[ticker].append(0)
            if (ohlc_dict[ticker]["diff"].iloc[i] / ohlc_dict[ticker]['close'].std()) < -z_threshold and \
            ohlc_dict[ticker]["kal"].iloc[i] < ohlc_dict[ticker]["kal"].mean() and \
                stoch_signal[ticker] == "oversold":
                tickers_signal[ticker] = "Buy"
                trade_count[ticker] += 1
                long_data[ticker][trade_count[ticker]] = [ohlc_dict[ticker]["open"].iloc[i+1]]
                hwm[ticker] = ohlc_dict[ticker]["open"].iloc[i+1]
            elif (ohlc_dict[ticker]["diff"].iloc[i] / ohlc_dict[ticker]['close'].std()) > z_threshold and \
             ohlc_dict[ticker]["kal"].iloc[i] > ohlc_dict[ticker]["kal"].mean() and \
                stoch_signal[ticker] == "overbought":
                tickers_signal[ticker] = "Sell"
                trade_count[ticker] += 1
                short_data[ticker][trade_count[ticker]] = [ohlc_dict[ticker]["open"].iloc[i+1]]
                hwm[ticker] = ohlc_dict[ticker]["open"].iloc[i+1]
                     
        elif tickers_signal[ticker] == "Buy":
            if ohlc_dict[ticker]["low"].iloc[i] < 0.985 * hwm[ticker]:
                tickers_signal[ticker] = ""
                long_data[ticker][trade_count[ticker]].append(0.985 * hwm[ticker])
                trade_count[ticker] += 1
                tickers_ret[ticker].append((0.985 * hwm[ticker] / ohlc_dict[ticker]["close"].iloc[i-1]) - 1)
            else:
                hwm[ticker] = max(hwm[ticker], ohlc_dict[ticker]["high"].iloc[i])
                tickers_ret[ticker].append((ohlc_dict[ticker]["close"].iloc[i] / ohlc_dict[ticker]["close"].iloc[i-1]) - 1)

        elif tickers_signal[ticker] == "Sell":
            if ohlc_dict[ticker]["high"].iloc[i] > 1.015 * hwm[ticker]:
                tickers_signal[ticker] = ""
                short_data[ticker][trade_count[ticker]].append(1.015 * hwm[ticker])
                trade_count[ticker] += 1
                tickers_ret[ticker].append((ohlc_dict[ticker]["close"].iloc[i-1] / 1.015 * hwm[ticker]) - 1)
            else:
                hwm[ticker] = ohlc_dict[ticker]["low"].iloc[i]
                tickers_ret[ticker].append((ohlc_dict[ticker]["close"].iloc[i-1] / ohlc_dict[ticker]["close"].iloc[i]) - 1)

    if trade_count[ticker] % 2 != 0:
        for trade in long_data[ticker]:
            if len(long_data[ticker][trade]) == 1:
                long_data[ticker][trade].append(ohlc_dict[ticker]["close"].iloc[i])
        for trade in short_data[ticker]:
            if len(short_data[ticker][trade]) == 1:
                short_data[ticker][trade].append(ohlc_dict[ticker]["close"].iloc[i])

    tickers_ret[ticker].append(0)
    ohlc_dict[ticker]["ret"] = np.array(tickers_ret[ticker]) 

# calculating overall strategy's KPIs
strategy_df = pd.DataFrame()
for ticker in tickers:
    strategy_df = ohlc_dict[ticker]["ret"]
    strategy_df[ticker].fillna(0)
strategy_df["ret"] = strategy_df.mean(axis=1)
    
CAGR(strategy_df)
sharpe(strategy_df, 0.03)
max_drawdown(strategy_df)

strategy_df['cum_return'] = (1 + strategy_df['ret']).cumprod()

# plotting the cumulative strategy returns
plt.figure(figsize=(14, 7))
strategy_df['cum_return'].plot()

plt.title('Cumulative Strategy Return')
plt.xlabel('Date')
plt.ylabel('Cumulative Return')
plt.grid(True)
plt.show()

#calculating individual stock's KPIs
cagr = {}
sharpe_ratios = {}
max_drawdown = {}

for ticker in tickers:
    cagr[ticker] = CAGR(ohlc_dict[ticker])
    sharpe_ratios[ticker] =  sharpe(ohlc_dict[ticker],0.03)
    max_drawdown[ticker] =  max_drawdown(ohlc_dict[ticker])
    
KPI_df = pd.DataFrame([cagr,sharpe_ratios,max_drawdown],index=["Return","Sharpe Ratio","Max Drawdown"])      
KPI_df = KPI_df.T
print(KPI_df)