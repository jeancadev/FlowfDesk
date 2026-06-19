"""
Kafka Consumers — Process domain events asynchronously.

NotificationConsumer: Sends notifications on ticket events.
AuditConsumer: Records change history for audit trail.

These run as separate processes alongside the main API.
"""

from __future__ import annotations

import json
import signal
import sys
from datetime import UTC, datetime
from typing import Any

from kafka import KafkaConsumer

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


class BaseConsumer:
    """Base class for Kafka consumers with graceful shutdown."""

    def __init__(
        self,
        topics: list[str],
        group_id: str,
        bootstrap_servers: list[str] | None = None,
    ):
        settings = get_settings()
        servers = bootstrap_servers or settings.kafka_bootstrap_servers_list

        self._consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=servers,
            group_id=group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        self._running = True

        # Graceful shutdown on SIGTERM/SIGINT
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, signum: int, frame: Any) -> None:
        logger.info("consumer_shutting_down", signal=signum)
        self._running = False

    def start(self) -> None:
        """Start consuming messages. Override `process_message` in subclasses."""
        logger.info("consumer_started", consumer=self.__class__.__name__)
        try:
            for message in self._consumer:
                if not self._running:
                    break
                try:
                    self.process_message(
                        topic=message.topic,
                        value=message.value,
                    )
                except Exception as e:
                    logger.error(
                        "consumer_message_processing_error",
                        topic=message.topic,
                        error=str(e),
                    )
        finally:
            self._consumer.close()
            logger.info("consumer_stopped")

    def process_message(self, topic: str, value: dict[str, Any]) -> None:
        """Override in subclasses to handle specific message types."""
        raise NotImplementedError


class NotificationConsumer(BaseConsumer):
    """
    Consumes ticket events and sends notifications.

    In production, this would integrate with email/Slack/push notification services.
    For now, it logs simulated notifications.
    """

    def __init__(self, bootstrap_servers: list[str] | None = None):
        super().__init__(
            topics=["ticket.created", "ticket.closed"],
            group_id="notification-group",
            bootstrap_servers=bootstrap_servers,
        )

    def process_message(self, topic: str, value: dict[str, Any]) -> None:
        ticket_id = value.get("ticket_id", "unknown")

        if topic == "ticket.created":
            logger.info(
                "notification_sent",
                type="ticket_created",
                ticket_id=ticket_id,
                message=(
                    "📧 [NOTIFICATION] New ticket created: "
                    f"{value.get('title', 'N/A')} "
                    f"(Priority: {value.get('priority', 'N/A')})"
                ),
            )
        elif topic == "ticket.closed":
            logger.info(
                "notification_sent",
                type="ticket_closed",
                ticket_id=ticket_id,
                message=f"📧 [NOTIFICATION] Ticket closed: {ticket_id}",
            )


class AuditConsumer(BaseConsumer):
    """
    Consumes all ticket events and records an audit trail.

    In production, this would persist to a dedicated audit_log table.
    For now, it logs structured audit entries.
    """

    def __init__(self, bootstrap_servers: list[str] | None = None):
        super().__init__(
            topics=["ticket.created", "ticket.updated", "ticket.closed"],
            group_id="audit-group",
            bootstrap_servers=bootstrap_servers,
        )

    def process_message(self, topic: str, value: dict[str, Any]) -> None:
        audit_entry = {
            "event_type": topic,
            "ticket_id": value.get("ticket_id"),
            "payload": value,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        logger.info("audit_log_entry", **audit_entry)


# ─── CLI Entrypoints ─────────────────────────────────────────────────


def run_notification_consumer() -> None:
    """Entrypoint for the notification consumer process."""
    setup_logging("INFO")
    consumer = NotificationConsumer()
    consumer.start()


def run_audit_consumer() -> None:
    """Entrypoint for the audit consumer process."""
    setup_logging("INFO")
    consumer = AuditConsumer()
    consumer.start()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "audit":
        run_audit_consumer()
    else:
        run_notification_consumer()
