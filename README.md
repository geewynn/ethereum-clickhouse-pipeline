# Ethereum Block Data Pipeline

This project sets up a data pipeline to ingest Ethereum block data into ClickHouse using Apache Kafka and Kafka Connect.

## Project Overview

This pipeline does the following:
1. Ingests Ethereum block data into a Kafka topic
2. Uses Kafka Connect with a ClickHouse sink connector to transfer data from Kafka to ClickHouse
3. Stores the Ethereum block data in a ClickHouse table for further analysis

## Prerequisites

- Docker and Docker Compose
- curl (for API requests)
- Git (for version control)

## Environment Setup

Create a `.env` file in the project root with the following content:
```
CLICKHOUSE_DB=ethereum
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=your_strong_password
CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1
```

## Setup

1. Clone the repository:
```bash 
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```
2. Create a `.env` file as described in the Environment Setup section.


3. Download the ClickHouse Kafka Connect Sink connector:

```bash
curl -LO https://github.com/ClickHouse/clickhouse-kafka-connect/releases/latest/download/clickhouse-kafka-connect-dist.zip

unzip clickhouse-kafka-connect-dist.zip -d clickhouse-kafka-connector
```

4. Create a `clickhouse-sink.json` file with the following content (adjust as needed):
```json
{
    "name": "clickhouse-sink",
    "config": {
        "connector.class": "com.clickhouse.kafka.connect.ClickHouseSinkConnector",
        "tasks.max": "1",
        "topics": "<your-topic-name>",
        "hostname": "clickhouse",
        "database": "ethereum",
        "username": "<clickhouse-username>",
        "password": "<clickhouse-password>",
        "ssl": "false",
        "port": "8123",
        "dialect": "http",
        "table": "blocks",
        "key.converter": "org.apache.kafka.connect.storage.StringConverter",
        "value.converter": "org.apache.kafka.connect.json.JsonConverter",
        "value.converter.schemas.enable": "false"
    }
}
```

5. Start the services using Docker Compose:

```bash
docker-compose up -d
```


6. Create the ClickHouse table:

```
docker-compose exec clickhouse clickhouse-client -u <username> --password <password> --query "
CREATE TABLE ethereum.blocks
(
    number UInt64,
    hash String,
    parent_hash String,
    timestamp DateTime,
    transactions Array(String)
)
ENGINE = MergeTree
ORDER BY (timestamp, number)
"
```

Create the Kafka Connect sink:

```bash
curl -X POST -H "Content-Type: application/json" --data @clickhouse-sink.json http://localhost:8083/connectors
```

## Usage:
1. To check the status of the Kafka Connect sink:

```bash 
curl http://localhost:8083/connectors/clickhouse-sink/status
```

2. To verify data in ClickHouse:
```bash
docker-compose exec clickhouse clickhouse-client -u admin --password strongpassword --query "SELECT count() FROM ethereum.blocks"
```


3. To view recent data:

```bash
docker-compose exec clickhouse clickhouse-client -u admin --password strongpassword --query "SELECT * FROM ethereum.blocks ORDER BY timestamp DESC LIMIT 5"
```

