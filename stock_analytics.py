import time
import json
from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
from datetime import datetime, timedelta
import threading
from collections import defaultdict, deque
import statistics
import traceback
import os
from dotenv import load_dotenv


class StockAnalyticsEngine:
    def __init__(self, kafka_servers='localhost:9092', topic='stock-ticks'):
        load_dotenv()

        self.kafka_servers = kafka_servers
        self.topic = topic
        self.running = False

        # In-memory storage for moving averages
        self.price_history = defaultdict(lambda: deque(maxlen=100))  # Last 100 prices per symbol
        self.volume_history = defaultdict(lambda: deque(maxlen=100))
        self.metrics_cache = defaultdict(dict)

        # InfluxDB setup
        try:
            self.influx_client = InfluxDBClient(
                url=os.getenv('INFLUXDB_URL', 'http://localhost:8086'),
                token=os.getenv('INFLUXDB_TOKEN'),
                org=os.getenv('INFLUXDB_ORG', 'myorg')
            )
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            self.influx_bucket = os.getenv('INFLUXDB_BUCKET', 'stock_data')
            self.influx_enabled = True
            print("✓ InfluxDB connection established")
        except Exception as e:
            print(f" InfluxDB not available: {e}")
            self.influx_enabled = False

        # Kafka setup
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.kafka_servers,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='latest',
                consumer_timeout_ms=1000
            )
            self.kafka_enabled = True
            print("✓ Kafka consumer initialized")
        except Exception as e:
            print(f"⚠ Kafka not available: {e}")
            self.kafka_enabled = False

    def calculate_metrics(self, symbol, price, volume, change_percent):
        """Calculate real-time metrics for a symbol"""
        # Add to history
        self.price_history[symbol].append(price)
        self.volume_history[symbol].append(volume)

        prices = list(self.price_history[symbol])
        volumes = list(self.volume_history[symbol])

        # Calculate moving averages
        ma_5 = statistics.mean(prices[-5:]) if len(prices) >= 5 else price
        ma_10 = statistics.mean(prices[-10:]) if len(prices) >= 10 else price
        ma_20 = statistics.mean(prices[-20:]) if len(prices) >= 20 else price

        # Calculate volatility (standard deviation of recent prices)
        volatility = statistics.stdev(prices[-10:]) if len(prices) >= 10 else 0.0

        # Volume averages
        vol_avg_5 = statistics.mean(volumes[-5:]) if len(volumes) >= 5 else volume
        vol_avg_10 = statistics.mean(volumes[-10:]) if len(volumes) >= 10 else volume

        # Anomaly detection (price deviates more than 2 standard deviations)
        is_anomaly = False
        if len(prices) >= 10 and volatility > 0:
            z_score = abs(price - ma_10) / volatility
            is_anomaly = z_score > 2.0

        metrics = {
            'symbol': symbol,
            'price': price,
            'volume': volume,
            'change_percent': change_percent,
            'ma_5': round(ma_5, 2),
            'ma_10': round(ma_10, 2),
            'ma_20': round(ma_20, 2),
            'volatility': round(volatility, 4),
            'vol_avg_5': int(vol_avg_5),
            'vol_avg_10': int(vol_avg_10),
            'is_anomaly': is_anomaly,
            'timestamp': datetime.now()
        }

        self.metrics_cache[symbol] = metrics
        return metrics

    def write_to_influxdb(self, metrics):
        """Write metrics to InfluxDB"""
        if not self.influx_enabled:
            return

        try:
            point = Point("stock_metrics") \
                .tag("symbol", metrics['symbol']) \
                .field("price", metrics['price']) \
                .field("volume", metrics['volume']) \
                .field("change_percent", metrics['change_percent']) \
                .field("ma_5", metrics['ma_5']) \
                .field("ma_10", metrics['ma_10']) \
                .field("ma_20", metrics['ma_20']) \
                .field("volatility", metrics['volatility']) \
                .field("vol_avg_5", metrics['vol_avg_5']) \
                .field("vol_avg_10", metrics['vol_avg_10']) \
                .field("is_anomaly", metrics['is_anomaly']) \
                .time(metrics['timestamp'])

            # Use the bucket from environment variable
            self.write_api.write(bucket=self.influx_bucket, record=point)

        except Exception as e:
            print(f"InfluxDB write error: {e}")

    def print_metrics(self, metrics):
        """Print metrics to console"""
        anomaly_flag = "🚨 ANOMALY" if metrics['is_anomaly'] else ""

        print(f"[{metrics['timestamp'].strftime('%H:%M:%S')}] "
              f"{metrics['symbol']}: ${metrics['price']:.2f} "
              f"(Vol: {metrics['volume']:,}) "
              f"MA5: ${metrics['ma_5']:.2f} "
              f"MA10: ${metrics['ma_10']:.2f} "
              f"Vol: {metrics['volatility']:.4f} "
              f"{anomaly_flag}")

    def process_kafka_message(self, message):
        """Process a single Kafka message"""
        try:
            data = message.value

            # Extract required fields
            symbol = data.get('symbol')
            price = data.get('price')
            volume = data.get('volume', 0)
            change_percent = data.get('change_percent', 0.0)

            if symbol and price is not None:
                # Calculate metrics
                metrics = self.calculate_metrics(symbol, price, volume, change_percent)

                # Output results
                self.print_metrics(metrics)
                self.write_to_influxdb(metrics)

        except Exception as e:
            print(f"Error processing message: {e}")

    def generate_dummy_data(self):
        """Generate dummy stock data for testing"""
        import random

        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
        base_prices = {'AAPL': 150, 'GOOGL': 2500, 'MSFT': 300, 'AMZN': 3200, 'TSLA': 800}

        while self.running:
            try:
                for symbol in symbols:
                    # Generate realistic price movement
                    base_price = base_prices[symbol]
                    price_change = random.uniform(-0.02, 0.02)  # ±2% change
                    new_price = base_price * (1 + price_change)

                    volume = random.randint(1000, 10000)
                    change_percent = price_change * 100

                    # Update base price slightly for next iteration
                    base_prices[symbol] = new_price

                    # Calculate and display metrics
                    metrics = self.calculate_metrics(symbol, new_price, volume, change_percent)
                    self.print_metrics(metrics)
                    self.write_to_influxdb(metrics)

                time.sleep(2)  # Generate data every 2 seconds

            except Exception as e:
                print(f"Error generating dummy data: {e}")
                break

    def start_analytics(self):
        """Start the analytics engine"""
        print("🚀 Starting Stock Analytics Engine...")
        self.running = True

        if self.kafka_enabled:
            print("📊 Processing real Kafka messages...")
            try:
                while self.running:
                    message_pack = self.consumer.poll(timeout_ms=1000)

                    if message_pack:
                        for topic_partition, messages in message_pack.items():
                            for message in messages:
                                self.process_kafka_message(message)
                    else:
                        print(".", end="", flush=True)  # Show we're waiting for data

            except KeyboardInterrupt:
                print("\n⏹ Stopping...")
            except Exception as e:
                print(f"\n❌ Kafka error: {e}")

        else:
            print("🔄 No Kafka available, generating dummy data...")
            try:
                self.generate_dummy_data()
            except KeyboardInterrupt:
                print("\n⏹ Stopping...")

    def stop(self):
        """Stop the analytics engine"""
        self.running = False
        try:
            if self.kafka_enabled:
                self.consumer.close()
            if self.influx_enabled:
                self.influx_client.close()
        except:
            pass
        print("✅ Analytics engine stopped")

    def get_summary(self):
        """Get summary of all tracked symbols"""
        print("\n📈 CURRENT SUMMARY:")
        print("-" * 80)

        if not self.metrics_cache:
            print("No data available yet...")
            return

        for symbol, metrics in self.metrics_cache.items():
            age = datetime.now() - metrics['timestamp']
            if age.total_seconds() < 60:  # Only show recent data
                status = "🚨" if metrics['is_anomaly'] else "✅"
                print(f"{status} {symbol}: ${metrics['price']:.2f} "
                      f"(MA5: ${metrics['ma_5']:.2f}, "
                      f"MA10: ${metrics['ma_10']:.2f}, "
                      f"Vol: {metrics['volatility']:.4f})")


def main():
    analytics = StockAnalyticsEngine()

    try:
        # Start analytics in a separate thread
        analytics_thread = threading.Thread(target=analytics.start_analytics)
        analytics_thread.daemon = True
        analytics_thread.start()

        print("\nPress Enter to see summary, Ctrl+C to quit...")

        while True:
            try:
                input()  # Wait for Enter key
                analytics.get_summary()
                print("\nPress Enter again for updated summary...")
            except KeyboardInterrupt:
                break

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

    finally:
        analytics.stop()


if __name__ == "__main__":
    main()