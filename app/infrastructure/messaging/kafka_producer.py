"""
Kafka Message Broker — Implementation of MessageBroker port.

Publishes domain events to Kafka topics:
- ticket.created → triggers notification + audit
- ticket.updated → triggers audit log
- ticket.closed → triggers notification + analytics
"""

from __future__ import annotations

import json
from typing import Any

from kafka import KafkaProducer
from kafka.errors import KafkaError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class KafkaMessageBroker:
    """Kafka implementation of the MessageBroker port."""

    def __init__(self, bootstrap_servers: list[str] | None = None):
        settings = get_settings()
        servers = bootstrap_servers or settings.kafka_bootstrap_servers_list

        try:
            self._producer = KafkaProducer(
                bootstrap_servers=servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1,  # Ensure ordering
            )
            logger.info("kafka_producer_initialized", servers=servers)
        except KafkaError as e:
            logger.error("kafka_producer_init_failed", error=str(e))
            self._producer = None

    def publish(self, topic: str, message: dict[str, Any]) -> None:
        """Publish a message to a Kafka topic."""
        if self._producer is None:
            logger.warning("kafka_producer_unavailable", topic=topic)
            return

        try:
            # Use ticket_id as key for partition ordering
            key = message.get("ticket_id", "")
            future = self._producer.send(topic, value=message, key=key)
            record_metadata = future.get(timeout=10)
            logger.info(
                "kafka_message_published",
                topic=topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
            )
        except KafkaError as e:
            logger.error("kafka_publish_failed", topic=topic, error=str(e))

    def close(self) -> None:
        """Flush and close the producer."""
        if self._producer:
            self._producer.flush()
            self._producer.close()
            logger.info("kafka_producer_closed")
