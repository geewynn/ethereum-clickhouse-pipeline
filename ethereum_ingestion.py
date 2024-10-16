import asyncio
import json
import logging
import os
from typing import Dict, Any

from dotenv import load_dotenv
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider
from confluent_kafka import Producer
from hexbytes import HexBytes

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EthereumIngestion:
    def __init__(self, quicknode_url: str, kafka_bootstrap_servers: str, kafka_topic: str):
        self.w3 = AsyncWeb3(AsyncHTTPProvider(quicknode_url))
        self.producer = Producer({
            'bootstrap.servers': kafka_bootstrap_servers,
            'client.id': 'ethereum_ingestion'
        })
        self.kafka_topic = kafka_topic

    async def log_loop(self, poll_interval: int):
        last_block = None
        while True:
            try:
                latest_block = await self.w3.eth.get_block('latest')
                if latest_block and (not last_block or latest_block['number'] > last_block['number']):
                    await self.handle_block(latest_block['number'])
                    last_block = latest_block
                await asyncio.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Error in log loop: {e}")
                await asyncio.sleep(poll_interval)

    async def handle_block(self, block_number: int):
        try:
            block = await self.w3.eth.get_block(block_number, full_transactions=True)
            block_data = await self.prepare_block_data(block)
            self.send_to_kafka(block_data)
        except Exception as e:
            logger.error(f"Error handling block {block_number}: {e}")

    async def prepare_block_data(self, block: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'number': block['number'],
            'hash': block['hash'].hex(),
            'parent_hash': block['parentHash'].hex(),
            'timestamp': block['timestamp'],
            'transactions': [await self.prepare_transaction_data(tx) for tx in block['transactions']]
        }

    async def prepare_transaction_data(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        receipt = await self.w3.eth.get_transaction_receipt(tx['hash'])
        return {
            'hash': tx['hash'].hex(),
            'from': tx['from'],
            'to': tx['to'],
            'value': str(tx['value']),
            'gas': tx['gas'],
            'gas_price': str(tx['gasPrice']),
            'input': self.hex_to_string(tx['input']),
            'status': receipt['status'],
            'gas_used': receipt['gasUsed'],
            'logs': [self.prepare_log_data(log) for log in receipt['logs']]
        }

    @staticmethod
    def prepare_log_data(log: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'address': log['address'],
            'topics': [topic.hex() for topic in log['topics']],
            'data': EthereumIngestion.hex_to_string(log['data'])
        }

    @staticmethod
    def hex_to_string(hex_str: Any) -> str:
        if isinstance(hex_str, HexBytes):
            return hex_str.hex()
        return hex_str

    def delivery_report(self, err, msg):
        if err is not None:
            logger.error(f'Message delivery failed: {err}')
        else:
            logger.info(f'Message delivered to {msg.topic()} [{msg.partition()}]')

    def send_to_kafka(self, data: Dict[str, Any]):
        try:
            self.producer.produce(
                self.kafka_topic,
                key=str(data['number']),
                value=json.dumps(data),
                callback=self.delivery_report
            )
            self.producer.poll(0)
        except Exception as e:
            logger.error(f"Failed to send block {data['number']} to Kafka: {e}")

    async def run(self):
        logger.info("Starting Ethereum block ingestion...")
        await self.log_loop(2)  # Poll every 2 seconds

async def main():
    logger.info(f"KAFKA_BOOTSTRAP_SERVERS: {os.getenv('KAFKA_BOOTSTRAP_SERVERS')}")
    logger.info(f"QUICKNODE_URL: {os.getenv('QUICKNODE_URL')}")
    logger.info(f"KAFKA_TOPIC: {os.getenv('KAFKA_TOPIC')}")
    
    quicknode_url = os.getenv('QUICKNODE_URL')
    kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS')
    kafka_topic = os.getenv('KAFKA_TOPIC')

    if not quicknode_url:
        logger.error("QUICKNODE_URL environment variable is not set")
        return

    ingestion = EthereumIngestion(quicknode_url, kafka_bootstrap_servers, kafka_topic)
    await ingestion.run()

if __name__ == "__main__":
    asyncio.run(main())