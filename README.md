# Algorithmic-Trading

This is a project about algorithmic trading. 

## Project Description

This project includes the following main components:
1. **Data Collection**: Collect historical and real-time market data from various financial data sources (e.g., Yahoo Finance, Alpha Vantage, Alpaca API). And also retrieve market data through ``websocket_streaming.py``
2. **Data Processing**: Clean, process, and analyze the collected data using Pandas and NumPy.
3. **Strategy Development**: Develop trading strategies based on technical indicators (e.g., moving averages, relative strength index) and machine learning models (e.g., regression models, neural networks).
4. **Backtesting**: Evaluate the performance of trading strategies using historical data based on the backtesting platform in ``backtest.py``.
5. **Execution**: Deploy trading strategies (``alpaca_strategy.py``) to a live trading environment using APIs (e.g., Alpaca API) to achieve automated trading. I have implemented some commonly seen trend-following and mean-reversion trading strategies. 

## Techniques and Tools Used

- **Programming Language**: Python
- **Data Streaming**: WebSocket
- **Data Processing**: Pandas, NumPy
- **Machine Learning**: Scikit-learn, TensorFlow, Keras
- **Backtesting Framework**: Backtrader
- **Trading API**: Alpaca API

For analytic report, please refer to ``Trading Report.ipynb``.

## Warning !!!
Algorithmic trading involves significant risk and may not be suitable for all investors. The strategies developed in this project are for educational purposes only and should not be considered as financial advice. Past performance is not indicative of future results. Always conduct your own research and consult with a professional financial advisor before making any trading decisions.