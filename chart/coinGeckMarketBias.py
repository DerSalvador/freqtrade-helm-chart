import requests, sys

def get_crypto_market_data():
    url = 'https://pro-api.coingecko.com/api/v3/coins/markets?x_cg_pro_api_key=CG-AgEZRgMf3iLk1S8CwyCKp7N3'
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

def calculate_trend_bias(market_data):
    total_positive = 0
    total_negative = 0
    sys.stderr.write(str(market_data))
    for crypto in market_data:
        sys.stderr.write(str(crypto))
        if crypto['price_change_percentage_24h'] is not None:
            if crypto['price_change_percentage_24h'] >= 0:
                total_positive += 1
            else:
                total_negative += 1
    
    sys.stderr.write(f"\ntotal_positive: {total_positive}\ntotal_negative: {total_negative}\nprice_change_percentage_24={crypto['price_change_percentage_24h']}\n")
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

