import pandas as pd
import numpy as np
import re
import sys
import matplotlib.pyplot as plt

def parse_line(line):
    key_value_pairs = re.findall(r'(\w+)=([^ ]+)', line)
    return {key: value for key, value in key_value_pairs}

def calculate_adx(df, period=14):
    df['TR'] = abs(df['HIGH'] - df['LOW'])
    df['+DM'] = df['HIGH'].diff()
    df['-DM'] = df['LOW'].diff()
    df['+DM'] = df['+DM'].where((df['+DM'] > 0) & (df['+DM'] > df['-DM']), 0)
    df['-DM'] = df['-DM'].where((df['-DM'] > 0) & (df['-DM'] > df['+DM']), 0)
    df['TR_smooth'] = df['TR'].rolling(window=period, min_periods=1).sum()
    df['+DM_smooth'] = df['+DM'].rolling(window=period, min_periods=1).sum()
    df['-DM_smooth'] = df['-DM'].rolling(window=period, min_periods=1).sum()
    df['+DI'] = 100 * df['+DM_smooth'] / df['TR_smooth']
    df['-DI'] = 100 * df['-DM_smooth'] / df['TR_smooth']
    df['DX'] = 100 * abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI'])
    df['ADX'] = df['DX'].rolling(window=period, min_periods=1).mean()
    return df

def calculate_smi(df, period=14, smooth_k=3, smooth_d=3):
    df['L14'] = df['LOW'].rolling(window=period).min()
    df['H14'] = df['HIGH'].rolling(window=period).max()
    df['%K'] = 100 * (df['CLOSE'] - df['L14']) / (df['H14'] - df['L14'])
    df['%D'] = df['%K'].rolling(window=smooth_k).mean()
    df['SMI'] = df['%D'].rolling(window=smooth_d).mean()
    return df

def generate_trading_signals(df):
    conditions = [
        (df['ADX'] > 25) & (df['SMI'] > 40),
        (df['ADX'] > 25) & (df['SMI'] < -40)
    ]
    choices = ['Long', 'Short']
    df['Signal'] = np.select(conditions, choices, default='Hold')
    return df

def analyze_groups(df):
    grouped = df.groupby('PAIR')

    #for name, group in grouped:
    #    print(f"\nAnalysis for {name}:\n")
    #    print(group[['TIMESTAMP', 'OPEN_RATE', 'CURRENT_RATE', 'ADX', 'SMI', 'Signal']].describe())
    #    
    #    plt.figure(figsize=(14, 7))
    #    plt.plot(group['TIMESTAMP'], group['CURRENT_RATE'], label='Current Rate', marker='o')
    #    plt.scatter(group['TIMESTAMP'][group['Signal'] == 'Long'], group['CURRENT_RATE'][group['Signal'] == 'Long'], color='green', label='Long Signal', marker='^', alpha=1)
    #    plt.scatter(group['TIMESTAMP'][group['Signal'] == 'Short'], group['CURRENT_RATE'][group['Signal'] == 'Short'], color='red', label='Short Signal', marker='v', alpha=1)
    #    plt.xlabel('Timestamp')
    #    plt.ylabel('Price')
    #    plt.title(f'Time Series for {name}')
    #    plt.legend()
    #    plt.grid(True)
    #    plt.show()

def main(file_path):
    data = pd.read_csv(file_path, header=None)
    parsed_data = data.iloc[:, 0].apply(parse_line).tolist()
    df = pd.DataFrame(parsed_data)
    
    df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'], format='%Y-%m-%d:%H:%M:%S')
    numeric_columns = ['PROFIT_ABS', 'OPEN_RATE', 'CURRENT_RATE', 'MAX_STAKE_AMOUNT', 'PROFIT_TO_TAKE']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df['HIGH'] = df[['OPEN_RATE', 'CURRENT_RATE']].max(axis=1)
    df['LOW'] = df[['OPEN_RATE', 'CURRENT_RATE']].min(axis=1)
    df['CLOSE'] = df['CURRENT_RATE']
    
    df = calculate_adx(df)
    df = calculate_smi(df)
    
    df['SMI'] = df['SMI'].interpolate()
    df = generate_trading_signals(df)
    
    # Print the latest signal for each pair
    latest_signals = df.sort_values('TIMESTAMP').groupby('PAIR').tail(1)
    for index, row in latest_signals.iterrows():
        print(f"{row['PAIR']}={row['Signal']}")
    
    # Analyze groups and generate plots
    analyze_groups(df)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python trading_signals.py <file_path>")
    else:
        file_path = sys.argv[1]
        main(file_path)

