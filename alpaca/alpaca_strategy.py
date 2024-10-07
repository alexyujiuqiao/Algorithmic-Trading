import os
import json
import numpy as np
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import REST, TimeFrame
import time

os.chdir("/Users/yujiuqiao/Desktop/Algorithmic-Trading/alpaca")

endpoint = "https://data.alpaca.markets/v2"
headers = json.loads(open("keys.txt",'r').read())
api = tradeapi.REST(headers["APCA-API-KEY-ID"], headers["APCA-API-SECRET-KEY"], base_url='https://paper-api.alpaca.markets')
tickers = ["SQQQ", "TQQQ", "IBIT"]
max_pos = 100000 #max position size for each ticker
stoch_signal = {}
for ticker in tickers:
    stoch_signal[ticker] = ""

# get historical ticker bar data
def hist_data(symbols, start_date ="2024-05-01", timeframe="Minute"):
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

def EMA(df_dict, span):
    for df in df_dict:
        df_dict[df]["ema"] = df_dict[df]["close"].ewm(span=span, adjust=False).mean()
    return df_dict

# function to calculate MACD
# typical values a(fast moving average) = 12; 
# b(slow moving average) =26; 
# c(signal line ma window) =9
def MACD(df_dict, a=12 ,b=26, c=9):
    for df in df_dict:
        df_dict[df]["ma_fast"] = df_dict[df]["close"].ewm(span=a, min_periods=a).mean()
        df_dict[df]["ma_slow"] = df_dict[df]["close"].ewm(span=b, min_periods=b).mean()
        df_dict[df]["macd"] = df_dict[df]["ma_fast"] - df_dict[df]["ma_slow"]
        df_dict[df]["signal"] = df_dict[df]["macd"].ewm(span=c, min_periods=c).mean()
        df_dict[df].drop(["ma_fast","ma_slow"], axis=1, inplace=True)

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

# calculate relative strength index (RSI)
def RSI(df_dict, n=14):
    for df in df_dict:
        df_dict[df]["change"] = df_dict[df]["close"] - df_dict[df]["close"].shift(1)
        df_dict[df]["gain"] = np.where(df_dict[df]["change"]>=0, df_dict[df]["change"], 0)
        df_dict[df]["loss"] = np.where(df_dict[df]["change"]<0, -1*df_dict[df]["change"], 0)
        df_dict[df]["avgGain"] = df_dict[df]["gain"].ewm(alpha=1/n, min_periods=n).mean()
        df_dict[df]["avgLoss"] = df_dict[df]["loss"].ewm(alpha=1/n, min_periods=n).mean()
        df_dict[df]["rs"] = df_dict[df]["avgGain"]/df_dict[df]["avgLoss"]
        df_dict[df]["rsi"] = 100 - (100 / (1 + df_dict[df]["rs"]))
        df_dict[df].drop(["change","gain","loss","avgGain","avgLoss","rs"], axis=1, inplace=True)
    return df_dict

# function to calculate Stochastic Oscillator
# lookback = lookback period
# k and d = moving average window for %K and %D
def stochastic(df_dict, lookback=14, k=3, d=3):
    for df in df_dict:
        df_dict[df]["HH"] = df_dict[df]["high"].rolling(lookback).max()
        df_dict[df]["LL"] = df_dict[df]["low"].rolling(lookback).min()
        df_dict[df]["%K"] = (100 * (df_dict[df]["close"] - df_dict[df]["LL"]) / (df_dict[df]["HH"]-df_dict[df]["LL"])).rolling(k).mean()
        df_dict[df]["%D"] = df_dict[df]["%K"].rolling(d).mean()
        df_dict[df].drop(["HH","LL"], axis=1, inplace=True)

# trend-following strategy
def main():
    global stoch_signal
    historicalData = hist_data(tickers, start_date = time.strftime("%Y-%m-%d"), timeframe="Minute") 

    MACD(historicalData)
    stochastic(historicalData,5,3,3)
    ADX(historicalData)
    EMA(historicalData, 30)
    RSI(historicalData)
    positions = api.list_positions()
    
    for ticker in tickers:
        historicalData[ticker].dropna(inplace=True)
        existing_pos = False

        # historicalData[ticker]["rsi"].iloc[-1] < 30 and \
        if historicalData[ticker]["%K"].iloc[-1] < 25 and \
            historicalData[ticker]["%K"].iloc[-1] > historicalData[ticker]["%D"].iloc[-1] and \
            historicalData[ticker]["ADX"].iloc[-1] > 25:
                stoch_signal[ticker] = "oversold"
        elif historicalData[ticker]["%K"].iloc[-1] > 80 and \
            historicalData[ticker]["%K"].iloc[-1] < historicalData[ticker]["%D"].iloc[-1] and \
            historicalData[ticker]["ADX"].iloc[-1] > 25:
                stoch_signal[ticker] = "overbought"

        for position in positions:
            if len(positions) > 0:
                if position.symbol == ticker and position.qty != 0:
                    print("existing position of {} stocks in {}...skipping".format(position.qty, ticker))
                    existing_pos = True

        if historicalData[ticker]["macd"].iloc[-1] > historicalData[ticker]["signal"].iloc[-1] and \
            historicalData[ticker]["macd"].iloc[-1] > 0 and \
            historicalData[ticker]["close"].iloc[-1] > historicalData[ticker]["ema"].iloc[-1] and \
            stoch_signal[ticker]=="oversold" and existing_pos == False:
                print("buy signal detected for {}".format(ticker))
                api.submit_order(ticker, max(1,int(max_pos/historicalData[ticker]["close"].iloc[-1])), "buy", "market", "ioc")
                print("bought {} stocks in {}".format(int(max_pos/historicalData[ticker]["close"].iloc[-1]),ticker))
                time.sleep(2)
                try:
                    filled_qty = api.get_position(ticker).qty
                    time.sleep(1)
                    api.submit_order(ticker, int(filled_qty), "sell", "trailing_stop", "day", trail_percent = "1.5")
                except Exception as e:
                    print(ticker, e)
        
        elif historicalData[ticker]["macd"].iloc[-1] < historicalData[ticker]["signal"].iloc[-1] and \
            historicalData[ticker]["macd"].iloc[-1] < 0 and \
            historicalData[ticker]["close"].iloc[-1] < historicalData[ticker]["ema"].iloc[-1] and \
            stoch_signal[ticker] == "overbought" and existing_pos == False:
            print("sell signal detected for {}".format(ticker))
            api.submit_order(ticker, max(1, int(max_pos / historicalData[ticker]["close"].iloc[-1])), "sell", "market", "ioc")
            print("shorted {} stocks in {}".format(int(max_pos / historicalData[ticker]["close"].iloc[-1]), ticker))
            time.sleep(2)
            try:
                filled_qty = api.get_position(ticker).qty
                stop_loss_price = historicalData[ticker]["close"].iloc[-1] * 0.98
                time.sleep(1)
                api.submit_order(ticker, -int(filled_qty), "buy", "trailing_stop", "day", trail_percent = "1")
            except Exception as e:
                print(ticker, e)

starttime = time.time()
timeout = starttime + 120*60*1
while time.time() <= timeout:
    print("starting iteration at {}".format(time.strftime("%Y-%m-%d %H:%M:%S")))
    main()
    time.sleep(60 - ((time.time() - starttime) % 60)) 

#close out all positions and orders    
api.close_all_positions()
time.sleep(5)
api.cancel_all_orders()
time.sleep(5)