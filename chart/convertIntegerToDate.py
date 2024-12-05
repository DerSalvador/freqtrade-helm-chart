import argparse
import datetime

# Define the parser and add the timestamp argument
parser = argparse.ArgumentParser(description='Convert a timestamp to a date')
parser.add_argument('timestamp', type=int, help='Timestamp to convert to date')

# Parse the command line arguments
args = parser.parse_args()

# Convert the timestamp to seconds
timestamp = args.timestamp / 1000  # Convert milliseconds to seconds

# Convert the timestamp to a date
date = datetime.datetime.fromtimestamp(timestamp)
print(date)
