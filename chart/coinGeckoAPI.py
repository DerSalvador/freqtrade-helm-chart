# --- Do not remove these libs ---
import time
from functools import reduce
from datetime import datetime
from dateutil import parser
import os
import sys
import requests
import json
import argparse
from binance.client import Client
import pandas as pd

import logging, threading
import warnings

class CoinGeckoAPI():

    coinGeckoAPIKey = None
    filelog = None
    apikey = None
    apisecret = None
    bias_determination = None
    status_table_informative_pairs = "BTC/USDT:USDT"
    spot_pair_delay = 5

    def log(self, msg: str):
        # self.filelog.info(msg)
        print(msg)

    def check_equal_strings(self, pair, bias1, bias2, biasBTC, binanceBTC, greedAndFear):
        self.bias_determination = self.getBiasDetermination()
        self.log(f"New Bias Determination {self.bias_determination}")
        if pair is not None and pair in self.status_table_informative_pairs:
            if biasBTC == binanceBTC and binanceBTC == greedAndFear:
                return True
        if self.bias_determination == "loose-short":
            if binanceBTC == greedAndFear and biasBTC in ("short") and bias1 in ("short") and bias2 in ("short"):
                return True
        if self.bias_determination == "loose":
            if biasBTC == binanceBTC and binanceBTC == greedAndFear:
                return True
        elif self.bias_determination == "restrictive":
            if biasBTC == binanceBTC and binanceBTC == greedAndFear and greedAndFear == bias1 and bias1 == bias2:
                return True
            elif biasBTC == binanceBTC and binanceBTC == greedAndFear and (bias1 == "neutral" or bias2 == "neutral"):
                return True
        # elif str1 == str2 and str2 == str4:
        #     return True
        # elif str1 == str3 and str3 == str4:
        #     return True
        # elif str2 == str3 and str3 == str4:
        #     return True
        return False

    @staticmethod
    def make_get_request_with_retry(self, url, auth, retries=20, sleep_time=10):
        lock = threading.Lock()
        lock.acquire()
        response = None
        time.sleep(self.spot_pair_delay)
        s = ""
        # Acquire a lock for the label to ensure only one thread processes it
        try:
            attempt = 0
            for attempt in range(0, retries):
                try:
                    time.sleep(self.spot_pair_delay)
                    requests.adapters.HTTPAdapter(pool_maxsize = 500, pool_connections=100, max_retries=10)
                    response = requests.get(url, auth=auth, timeout=120)
                    response.raise_for_status()  # Ensure we notice bad responses
                    s = f"Successful request to endpoint {url}"
                    attempt = 0
                    return response  # Break the loop and return response if successful
                except Exception as ex:
                    s = f"Retries exhausted, giving up on request {url}"
                    self.log(f"Attempt {attempt + 1} failed. Error: {ex}, {s}")
                    time.sleep(sleep_time)
        except Exception as e:
            self.log(s)
        finally:
            lock.release()
            self.log(s)

    def getBiasDetermination(self):
        url = "https://filekeys.com/BiasDetermination"
        headers = {
            "user-agent": "curl/8.4.0",
            "accept": "*/*"
        }
        try:
            response = requests.get(url, auth=None, headers=headers, timeout=120)
            response.raise_for_status()  # Check for HTTP errors            
            # response = CoinGeckoAPI.make_get_request_with_retry(self, url, None)
            if response.status_code == 200:
                content = response.text.strip()
                if not content or content == "":
                    return "empty"
                self.log(f"Returning bias determination {content} of url {url}")
                return content
            else:
                s = f"bias determination url returned {response.status_code} for url {url}"
                self.log(s)
                raise Exception(s)
        except Exception as e:
            self.log(f"Exception: Bias not found, returning neutral {e}")
            raise e

    def get_file_sentiment(self, pair: str, apikey, apisecret):
        # url = "https://filekeys.com/tradingaas/index.html"
        url = "https://filekeys.com/market_bias"
        headers = {
            "user-agent": "curl/8.4.0",
            "accept": "*/*"
        }
        try:
            bias1 = self.coinGeckoBias1()
            bias2 = self.coinGeckoBias2()
            biasBTC = self.coinGeckoBiasBTC()
            binanceBTC = self.getBinanceTrend(self.apikey, self.apisecret)
            greedAndFear = self.get_market_sentiment_alternative_greed_and_fear()
            self.log(f"Checking market bias for pair {pair}, greedAndFear={greedAndFear} bias1={bias1}, bias2={bias2}, biasBTC={biasBTC}, binanceBTC={binanceBTC}")
            if self.check_equal_strings(pair, bias1, bias2, biasBTC, binanceBTC, greedAndFear):
                return biasBTC
            # elif bias1 == bias2 == biasBTC == "short":
            #     return "short"
            return "neutral"
            
        except Exception as e:
            self.log(f"Exception get_file_sentiment: {e}")
            raise e

    def get_crypto_market_data(self):
        url = f"https://pro-api.coingecko.com/api/v3/coins/markets?x_cg_pro_api_key={self.coinGeckoAPIKey}"
        # print(f"Url coinGeckoAPI {url}")
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 10,
            'page': 1,
            'sparkline': False
        }
        response = requests.get(url, params=params)
        data = response.json()
        return data

    def calculate_trend_bias(self, market_data):
        total_positive = 0
        total_negative = 0
        try:
            for crypto in market_data:
                if crypto['price_change_percentage_24h'] is not None:
                    if crypto['price_change_percentage_24h'] >= 0:
                        total_positive += 1
                    else:
                        total_negative += 1
            print(f"total_positive: {total_positive}, total_negative: {total_negative}")    
            if total_positive > total_negative:
                return "long"
            elif total_positive < total_negative:
                return "short"
            else:
                return "neutral"
        except Exception as e:
            s = f"Exception calculate_trend_bias: {e}"
            self.log(s)
            return s

    def coinGeckoBias1(self):
        trend_bias = "neutral"
        try:
            market_data = self.get_crypto_market_data()
            # print(market_data)
            trend_bias = self.calculate_trend_bias(market_data)
        except Exception as e:
            s = f"Exception coinGeckoBias1 {e}"
            self.log(s)
            trend_bias = s
        finally:
            return trend_bias

    def coinGeckoBias2(self):
        market_trend_bias = "neutral"
        # API endpoint to retrieve data
        try:
            url = f"https://pro-api.coingecko.com/api/v3/global?x_cg_pro_api_key={self.coinGeckoAPIKey}"
            # print(f"coinGeckoBias2 : {url}")

            # Make a GET request to the API endpoint
            response = requests.get(url)

            # Check if the request was successful
            if response.status_code == 200:
                data = response.json()
                
                # Extract relevant data from the JSON response
                market_cap_change_percentage_24h_usd = data["data"]["market_cap_change_percentage_24h_usd"]
                # sys.stderr.write(f"market_cap_change_percentage_24h_usd: {market_cap_change_percentage_24h_usd}")
                
                # Determine market trend bias based on the percentage change in market capitalization
                if market_cap_change_percentage_24h_usd > 0:
                    market_trend_bias = "long" 
                elif  market_cap_change_percentage_24h_usd < 0:
                    market_trend_bias = "short" 
                
                # Print the market trend bias
                return market_trend_bias
        except Exception as e:
            market_trend_bias = f"Exception in coinGeckoBias2: {e}"
            self.log(market_trend_bias)
        finally:
            return market_trend_bias

    def get_bitcoin_data(self):
        # API endpoint and key for CoinGecko
        API_URL = "https://pro-api.coingecko.com/api/v3"
        API_KEY = "CG-AgEZRgMf3iLk1S8CwyCKp7N3"        
        endpoint = f"{API_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": "bitcoin",
            "order": "market_cap_desc",
            "per_page": 1,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h,7d",
            "x_cg_pro_api_key": API_KEY,
        }
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None
        except Exception as e:
            self.log(f"Error fetching Bitcoin data: {e}")
            raise e

    # Function to analyze market trend bias (bullish or bearish)
    def analyze_trend(self, data):
        change_24h = data.get("price_change_percentage_24h", 0)
        change_7d = data.get("price_change_percentage_7d_in_currency", 0)
        volume = data.get("total_volume", 0)

        # Determine bias based on 24-hour and 7-day changes
        if change_24h > 0 and change_7d > 0:
            trend = "long"
        elif change_24h < 0 and change_7d < 0:
            trend = "short"
        else:
            trend = "neutral"

        return trend

    def analyze_trend_day(self, data):
        change_24h = data.get("price_change_percentage_24h", 0)
        # change_7d = data.get("price_change_percentage_7d_in_currency", 0)
        volume = data.get("total_volume", 0)

        # Determine bias based on 24-hour and 7-day changes
        if change_24h > 0: # and change_7d > 0:
            trend = "long"
        elif change_24h < 0: # and change_7d < 0:
            trend = "short"
        else:
            trend = "neutral"
     
        return trend

    def coinGeckoBiasBTC(self):
        trend_bias = "exception"
        try:
            bitcoin_data = self.get_bitcoin_data()
            if bitcoin_data:
                trend_bias = self.analyze_trend_day(bitcoin_data)
            else:
                return f"exception: get_bitcoin_data"
        except Exception as e:
            self.log(f"Exception coinGeckoBiasBTC {e}")
            trend_bias = f"exception {e}"
        finally:
            return trend_bias

##########################################

    # Function to fetch historical candlestick data
    def get_candlestick_data(self, client, symbol, interval, limit=100):
        """
        Fetch candlestick (OHLC) data for a given symbol and interval.

        Args:
            client (Client): Binance API client.
            symbol (str): The trading pair (e.g., 'BTCUSDT').
            interval (str): Timeframe (e.g., '1d' for daily, '1h' for hourly).
            limit (int): Number of candles to fetch.

        Returns:
            pandas.DataFrame: Candlestick data.
        """
        candles = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        
        # Convert data to DataFrame
        df = pd.DataFrame(candles, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'num_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Keep only relevant columns and convert to numeric
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    # Function to calculate SMA and detect trends
    def detect_trend(self, df):
        df['SMA_20'] = df['close'].rolling(window=20).mean()  # 20-day SMA
        df['SMA_50'] = df['close'].rolling(window=50).mean()  # 50-day SMA

        # Determine trend
        def trend_logic(row):
            if row['SMA_20'] > row['SMA_50']:
                return "long"
            elif row['SMA_20'] < row['SMA_50']:
                return "short"
            else:
                return "neutral"

        df['trend'] = df.apply(trend_logic, axis=1)
        return df

    def getBinanceTrend(self, apikey, apisecret):
        latest_trend = "neutral"
        try:
            # Initialize Binance API client
            client = Client(apikey, apisecret)

            # Fetch BTC/USDT daily data
            symbol = "BTCUSDT"
            interval = "1d"
            df = self.get_candlestick_data(client, symbol, interval)

            # Calculate SMA and detect trends
            df = self.detect_trend(df)

            # Display the last few rows
            # print(df.tail())

            # Example: Check today's trend
            latest_trend = df.iloc[-1]['trend']
        except Exception as e:
            self.log(f"Exception in getBinanceTrend {e}")
            latest_trend = f"exception {e}"
        finally:
            return latest_trend
######################

    def get_market_sentiment_alternative_greed_and_fear(self):
        url = "https://api.alternative.me/fng/?limit=100"
        ret = "None"
        try:
            # Fetch the data from the API
            response = requests.get(url)
            response.raise_for_status()  # Raise an error if the request fails
            
            data = response.json()
            if 'data' not in data:
                raise ValueError("Unexpected response structure: 'data' key not found.")
            
            # Extract the value_classification
            classifications = [entry['value_classification'].lower() for entry in data['data']]
            
            # Count occurrences of 'greed' and 'fear'
            greed_count = sum(1 for c in classifications if 'greed' in c)
            fear_count = sum(1 for c in classifications if 'fear' in c)
            total = len(classifications)
            
            # Check if 80% of the classifications are greed or fear
            if greed_count / total >= 0.8:
                ret = "long"
            elif fear_count / total >= 0.8:
                ret = "short"
            else:
                ret = "neutral"
        
        except Exception as e:
            ret = f"get_market_sentiment_alternative_greed_and_fear: {e}"
            self.log(ret)
        finally:
            return ret

