# Real-Time Stock Market Analytics System

A comprehensive real-time stock market data streaming and analytics platform built with Kafka, InfluxDB, and Python. This system provides live stock data ingestion, real-time analytics processing, and interactive web dashboards.

## 🏗️ Architecture

```
Stock Data Producer → Kafka → Analytics Engine → InfluxDB
                                     ↓
                            Web Dashboard (Dash/Plotly)
```

## 🚀 Features

- **Real-time Data Streaming**: Ingest stock data from Alpha Vantage API or simulated data
- **Live Analytics**: Calculate moving averages, volatility, and anomaly detection
- **Interactive Dashboard**: Web-based visualization with live charts
- **Scalable Architecture**: Built on Kafka for high-throughput streaming
- **Time-Series Storage**: InfluxDB for efficient time-series data storage
- **Anomaly Detection**: Automatic detection of unusual price movements
- **Multi-Symbol Support**: Track multiple stocks simultaneously

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.8+
- Alpha Vantage API key (optional, for real data)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd stock-analytics-system
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install kafka-python influxdb-client pandas dash plotly python-dotenv alpha-vantage
```

### 3. Configure Environment Variables

Create a `.env` file in your project root:

```bash
# .env file - DO NOT commit to version control
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-influxdb-token-here
INFLUXDB_ORG=myorg
INFLUXDB_BUCKET=stock_data

KAFKA_SERVERS=localhost:9092
KAFKA_TOPIC=stock-ticks

# Optional: For real stock data
ALPHA_VANTAGE_API_KEY=your-api-key-here

# Dashboard settings
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8050
DASHBOARD_DEBUG=True

# Analytics settings
UPDATE_INTERVAL=2
ANOMALY_THRESHOLD=2.0
```

**Security Note**: Add `.env` to your `.gitignore` file to prevent committing sensitive credentials.

### 4. Start Infrastructure Services

Create a `docker-compose.yml` file:

```yaml
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.4.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  influxdb:
    image: influxdb:2.0
    ports:
      - "8086:8086"
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: admin
      DOCKER_INFLUXDB_INIT_PASSWORD: password
      DOCKER_INFLUXDB_INIT_ORG: myorg
      DOCKER_INFLUXDB_INIT_BUCKET: stock_data
```

Start the services:

```bash
docker-compose up -d
```

### 5. Get Your InfluxDB Token

After starting InfluxDB, get your token for the `.env` file:

```bash
# Access InfluxDB UI at http://localhost:8086
# Login with: admin / password
# Go to Data > Tokens > Generate Token
# Copy the token to your .env file
```

## 🎯 Usage

### 1. Start the Data Producer

The producer generates stock tick data and streams it to Kafka:

```bash
python stock_producer.py
```

**Configuration Options:**
- **Simulated Data**: Default mode, generates realistic stock price movements
- **Real Data**: Requires Alpha Vantage API key for live market data

```python
# For simulated data
producer.start_streaming(use_real_data=False, interval=2)

# For real data (add your API key)
producer.start_streaming(use_real_data=True, api_key="YOUR_API_KEY", interval=60)
```

### 2. Start the Analytics Engine

The analytics engine processes streaming data and calculates real-time metrics:

```bash
python stock_analytics.py
```

**Features:**
- Moving averages (5, 10, 20 periods)
- Price volatility calculation
- Volume analysis
- Anomaly detection (Z-score > 2.0)
- Real-time console output
- InfluxDB storage

### 3. Launch the Web Dashboard

Start the interactive web dashboard:

```bash
python stock_dashboard.py
```

Access the dashboard at: `http://localhost:8050`

**Dashboard Features:**
- Live price charts
- Volume analysis
- Moving averages visualization
- Volatility tracking
- Anomaly alerts
- Auto-refresh every 2 seconds

## 📊 Components

### Stock Data Producer (`stock_producer.py`)
- Generates or fetches real-time stock data
- Supports multiple data sources (Alpha Vantage API, simulated)
- Publishes data to Kafka topics
- Configurable streaming intervals

### Analytics Engine (`stock_analytics.py`)
- Consumes data from Kafka
- Calculates real-time metrics:
  - Moving averages (MA5, MA10, MA20)
  - Price volatility (standard deviation)
  - Volume averages
  - Anomaly detection using Z-scores
- Stores results in InfluxDB
- Provides console output and summary reports

### Web Dashboard (`stock_dashboard.py`)
- Real-time web interface built with Dash/Plotly
- Interactive charts and visualizations
- Live anomaly alerts
- Responsive design
- Auto-updating displays

## 🔧 Configuration

### Customization

**Add New Stock Symbols:**
```python
# In stock_producer.py
self.symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META']
```

**Adjust Analytics Parameters:**
```python
# In stock_analytics.py
self.price_history = defaultdict(lambda: deque(maxlen=200))  # Increase history
```

**Modify Anomaly Detection:**
```python
# Adjust Z-score threshold
is_anomaly = z_score > 1.5  # More sensitive detection
```

## 📈 Metrics and Analytics

### Real-Time Metrics
- **Price**: Current stock price
- **Volume**: Trading volume
- **Moving Averages**: MA5, MA10, MA20
- **Volatility**: Standard deviation of recent prices
- **Volume Averages**: 5 and 10-period volume averages
- **Anomaly Detection**: Statistical outlier identification

### Anomaly Detection Algorithm
The system uses Z-score analysis to detect price anomalies:
```
Z-score = |current_price - moving_average| / volatility
Anomaly threshold: Z-score > 2.0
```

## 🐛 Troubleshooting

### Common Issues

**Kafka Connection Failed:**
```bash
# Check if Kafka is running
docker-compose ps
# Restart services
docker-compose restart kafka
```

**InfluxDB Connection Issues:**
```bash
# Verify InfluxDB is accessible
curl http://localhost:8086/health
# Check logs
docker-compose logs influxdb
```

**Dashboard Not Loading:**
```bash
# Check if all dependencies are installed
pip install -r requirements.txt
# Verify port 8050 is available
netstat -an | grep 8050
```

### Performance Optimization

**For High-Frequency Data:**
- Increase Kafka partition count
- Adjust consumer batch sizes
- Optimize InfluxDB write batching

**For Large-Scale Deployment:**
- Use Kafka clusters
- Implement horizontal scaling
- Add monitoring and alerting

## 🔒 Security Considerations

- Use environment variables for API keys
- Implement authentication for web dashboard
- Secure Kafka and InfluxDB endpoints
- Add input validation and sanitization

## 📝 API Endpoints

### InfluxDB Queries
```sql
-- Get latest prices
SELECT last("price") FROM "stock_metrics" GROUP BY "symbol"

-- Get price history
SELECT "price", "ma_10" FROM "stock_metrics" 
WHERE "symbol" = 'AAPL' AND time > now() - 1h
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Alpha Vantage for stock market data API
- Apache Kafka for streaming platform
- InfluxDB for time-series database
- Plotly/Dash for visualization framework

---

**Note**: This system is for educational and research purposes. Do not use for actual trading decisions without proper validation and risk management.
