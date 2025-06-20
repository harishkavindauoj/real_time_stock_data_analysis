import json
import os
import time
import random
from datetime import datetime
from kafka import KafkaProducer
from alpha_vantage.timeseries import TimeSeries
import logging
from dotenv import load_dotenv


class StockDataProducer:
    def __init__(self, kafka_bootstrap_servers='localhost:9092', topic='stock-ticks'):
        load_dotenv()

        kafka_servers = os.getenv('KAFKA_SERVERS', 'localhost:9092')
        self.topic = os.getenv('KAFKA_TOPIC', 'stock-ticks')

        self.producer = KafkaProducer(
            bootstrap_servers=kafka_servers.split(','),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8')
        )

        self.symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
        self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY')

    def simulate_stock_tick(self, symbol):
        """Simulate real-time stock data"""
        base_price = {'AAPL': 150, 'GOOGL': 2500, 'MSFT': 300, 'AMZN': 3200, 'TSLA': 800}

        # Simulate price movement
        change = random.uniform(-0.02, 0.02)  # ±2% change
        price = base_price[symbol] * (1 + change)

        tick_data = {
            'symbol': symbol,
            'price': round(price, 2),
            'volume': random.randint(100, 10000),
            'timestamp': datetime.now().isoformat(),
            'change_percent': round(change * 100, 2)
        }
        return tick_data

    def fetch_real_data(self, api_key, symbol):
        """Fetch real data from Alpha Vantage"""
        try:
            ts = TimeSeries(key=api_key, output_format='json')
            data, meta_data = ts.get_quote_endpoint(symbol=symbol)

            tick_data = {
                'symbol': symbol,
                'price': float(data['05. price']),
                'volume': int(data['06. volume']),
                'timestamp': datetime.now().isoformat(),
                'change_percent': float(data['10. change percent'].strip('%'))
            }
            return tick_data
        except Exception as e:
            logging.error(f"Error fetching data for {symbol}: {e}")
            return self.simulate_stock_tick(symbol)

    def start_streaming(self, use_real_data=False, api_key=None, interval=60):
        """Start streaming stock data to Kafka"""
        print(f"Starting stock data streaming to topic: {self.topic}")

        try:
            while True:
                for symbol in self.symbols:
                    if use_real_data and api_key:
                        tick_data = self.fetch_real_data(api_key, symbol)
                        time.sleep(12)  # 5 requests/min = 1 request every 12s
                    else:
                        tick_data = self.simulate_stock_tick(symbol)

                    self.producer.send(self.topic, key=symbol, value=tick_data)
                    print(f"Sent: {tick_data}")

                self.producer.flush()

        except KeyboardInterrupt:
            print("Stopping producer...")
        finally:
            self.producer.close()


if __name__ == "__main__":
    # Initialize producer
    producer = StockDataProducer()

    # Start streaming (use simulated data)
    #producer.start_streaming(use_real_data=False, interval=2)

    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')

    # For real data, uncomment and add your Alpha Vantage API key:
    producer.start_streaming(use_real_data=True, api_key=api_key, interval=60)