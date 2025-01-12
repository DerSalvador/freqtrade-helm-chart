import requests, sys

def get_crypto_market_data():
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 10,
        'page': 1,
        'sparkline': False
    }
    response = requests.get(url, params=params)
    data = response.json()
    #sys.stderr.write(str(data))
    return data

def calculate_trend_bias(market_data):
    total_positive = 0
    total_negative = 0
    for crypto in market_data:
        if crypto['price_change_percentage_24h'] is not None:
            if crypto['price_change_percentage_24h'] >= 0:
                total_positive += 1
            else:
                total_negative += 1
    
    if total_positive > total_negative:
        return "long"
    elif total_positive < total_negative:
        return "short"
    else:
        return "neutral"

if __name__ == '__main__':
    market_data = get_crypto_market_data()
    trend_bias = calculate_trend_bias(market_data)
    print(trend_bias)

