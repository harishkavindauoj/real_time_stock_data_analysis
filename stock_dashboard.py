import os

import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
from kafka import KafkaConsumer
import json
import threading
import time
from dotenv import load_dotenv


class StockDashboard:
    def __init__(self):
        load_dotenv()

        # Configuration from environment
        self.kafka_servers = os.getenv('KAFKA_SERVERS', 'localhost:9092').split(',')
        self.kafka_topic = os.getenv('KAFKA_TOPIC', 'stock-ticks')
        self.update_interval = int(os.getenv('UPDATE_INTERVAL', 2)) * 1000  # Convert to milliseconds

        self.app = dash.Dash(__name__)
        self.stock_data = {}
        self.anomalies = []

        self.setup_layout()
        self.start_data_consumer()



    def setup_layout(self):
        """Setup dashboard layout"""
        self.app.layout = html.Div([
            html.H1("Real-Time Stock Market Analytics",
                    style={'textAlign': 'center', 'marginBottom': 30}),

            dcc.Interval(
                id='interval-component',
                interval=self.update_interval,  # Use env variable
                n_intervals=0
            ),

            html.Div([
                html.Div([
                    dcc.Graph(id='live-price-chart')
                ], className="six columns"),

                html.Div([
                    dcc.Graph(id='volume-chart')
                ], className="six columns"),
            ], className="row"),

            html.Div([
                html.Div([
                    dcc.Graph(id='moving-averages')
                ], className="six columns"),

                html.Div([
                    dcc.Graph(id='volatility-chart')
                ], className="six columns"),
            ], className="row"),

            html.Div([
                html.H3("Recent Anomalies"),
                html.Div(id='anomaly-alerts')
            ], style={'margin': '20px'}),

            # Add configuration info
            html.Div([
                html.P(f"Kafka Topic: {self.kafka_topic}"),
                html.P(f"Update Interval: {self.update_interval / 1000}s"),
                html.P(f"Kafka Servers: {', '.join(self.kafka_servers)}")
            ], style={'margin': '20px', 'fontSize': '12px', 'color': 'gray'})
        ])

    def consume_kafka_data(self):
        """Background thread to consume Kafka data"""
        try:
            consumer = KafkaConsumer(
                self.kafka_topic,
                bootstrap_servers=self.kafka_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest'
            )

            print(f"✓ Connected to Kafka: {self.kafka_servers}")
            print(f"✓ Consuming from topic: {self.kafka_topic}")

            for message in consumer:
                data = message.value
                symbol = data['symbol']

                if symbol not in self.stock_data:
                    self.stock_data[symbol] = {
                        'timestamps': [],
                        'prices': [],
                        'volumes': [],
                        'ma_5min': [],
                        'volatility': []
                    }

                # Keep only last 100 points for performance
                if len(self.stock_data[symbol]['timestamps']) > 100:
                    for key in self.stock_data[symbol]:
                        self.stock_data[symbol][key] = self.stock_data[symbol][key][-100:]

                # Add new data point
                self.stock_data[symbol]['timestamps'].append(
                    datetime.fromisoformat(data['timestamp'].replace('Z', ''))
                )
                self.stock_data[symbol]['prices'].append(data['price'])
                self.stock_data[symbol]['volumes'].append(data['volume'])

                # Calculate simple moving average (last 10 points)
                if len(self.stock_data[symbol]['prices']) >= 10:
                    ma = sum(self.stock_data[symbol]['prices'][-10:]) / 10
                    self.stock_data[symbol]['ma_5min'].append(ma)
                else:
                    self.stock_data[symbol]['ma_5min'].append(data['price'])

                # Calculate volatility (standard deviation of last 10 changes)
                if len(self.stock_data[symbol]['prices']) >= 2:
                    changes = [abs(self.stock_data[symbol]['prices'][i] -
                                   self.stock_data[symbol]['prices'][i - 1])
                               for i in range(1, len(self.stock_data[symbol]['prices']))]
                    if len(changes) >= 10:
                        volatility = pd.Series(changes[-10:]).std()
                    else:
                        volatility = pd.Series(changes).std()
                    self.stock_data[symbol]['volatility'].append(volatility)
                else:
                    self.stock_data[symbol]['volatility'].append(0)

        except Exception as e:
            print(f"❌ Kafka consumer error: {e}")

    def start_data_consumer(self):
        """Start Kafka consumer in background thread"""
        consumer_thread = threading.Thread(target=self.consume_kafka_data)
        consumer_thread.daemon = True
        consumer_thread.start()

    def create_price_chart(self):
        """Create live price chart"""
        fig = go.Figure()
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

        for i, (symbol, data) in enumerate(self.stock_data.items()):
            if data['timestamps']:
                fig.add_trace(go.Scatter(
                    x=data['timestamps'],
                    y=data['prices'],
                    mode='lines+markers',
                    name=symbol,
                    line=dict(color=colors[i % len(colors)], width=2)
                ))

        fig.update_layout(
            title="Live Stock Prices",
            xaxis_title="Time",
            yaxis_title="Price ($)",
            hovermode='x unified',
            height=400
        )
        return fig

    def create_volume_chart(self):
        """Create volume chart"""
        fig = go.Figure()

        for symbol, data in self.stock_data.items():
            if data['timestamps']:
                fig.add_trace(go.Bar(
                    x=data['timestamps'],
                    y=data['volumes'],
                    name=f"{symbol} Volume",
                    opacity=0.7
                ))

        fig.update_layout(
            title="Trading Volume",
            xaxis_title="Time",
            yaxis_title="Volume",
            height=400
        )

        return fig

    def create_ma_chart(self):
        """Create moving averages chart"""
        fig = go.Figure()

        for symbol, data in enumerate(self.stock_data.items()):
            symbol_name, symbol_data = data
            if symbol_data['timestamps']:
                # Actual price
                fig.add_trace(go.Scatter(
                    x=symbol_data['timestamps'],
                    y=symbol_data['prices'],
                    mode='lines',
                    name=f"{symbol_name} Price",
                    line=dict(width=1)
                ))

                # Moving average
                fig.add_trace(go.Scatter(
                    x=symbol_data['timestamps'],
                    y=symbol_data['ma_5min'],
                    mode='lines',
                    name=f"{symbol_name} MA",
                    line=dict(width=2, dash='dash')
                ))

        fig.update_layout(
            title="Price vs Moving Average",
            xaxis_title="Time",
            yaxis_title="Price ($)",
            height=400
        )

        return fig

    def create_volatility_chart(self):
        """Create volatility chart"""
        fig = go.Figure()

        for symbol, data in self.stock_data.items():
            if data['timestamps'] and data['volatility']:
                fig.add_trace(go.Scatter(
                    x=data['timestamps'],
                    y=data['volatility'],
                    mode='lines+markers',
                    name=f"{symbol} Volatility",
                    fill='tonexty' if symbol != list(self.stock_data.keys())[0] else None
                ))

        fig.update_layout(
            title="Price Volatility",
            xaxis_title="Time",
            yaxis_title="Volatility",
            height=400
        )

        return fig

    def setup_callbacks(self):
        """Setup Dash callbacks"""
        @callback(
            [Output('live-price-chart', 'figure'),
             Output('volume-chart', 'figure'),
             Output('moving-averages', 'figure'),
             Output('volatility-chart', 'figure'),
             Output('anomaly-alerts', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_charts(n):
            # Create charts (using existing methods)
            price_fig = self.create_price_chart()
            volume_fig = self.create_volume_chart()
            ma_fig = self.create_ma_chart()
            volatility_fig = self.create_volatility_chart()

            # Anomaly detection with configurable threshold
            threshold = float(os.getenv('ANOMALY_THRESHOLD', 5.0))
            alerts = []

            for symbol, data in self.stock_data.items():
                if data['prices'] and len(data['prices']) > 1:
                    current_price = data['prices'][-1]
                    prev_price = data['prices'][-2]
                    change = abs((current_price - prev_price) / prev_price * 100)

                    if change > threshold:
                        alerts.append(
                            html.Div([
                                html.Strong(f"{symbol}: "),
                                f"Large price movement: {change:.2f}% change",
                                html.Br()
                            ], style={'color': 'red', 'margin': '5px'})
                        )

            if not alerts:
                alerts = [html.Div("No anomalies detected", style={'color': 'green'})]

            return price_fig, volume_fig, ma_fig, volatility_fig, alerts

    def run(self):
        """Run the dashboard"""
        host = os.getenv('DASHBOARD_HOST', '127.0.0.1')
        port = int(os.getenv('DASHBOARD_PORT', 8050))
        debug = os.getenv('DASHBOARD_DEBUG', 'True').lower() == 'true'

        self.setup_callbacks()
        print(f"🚀 Starting dashboard at http://{host}:{port}")
        self.app.run_server(debug=debug, host=host, port=port)


if __name__ == "__main__":
    dashboard = StockDashboard()
    dashboard.run()

