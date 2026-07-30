"""add handover notifications settings + handover_events table

Revision ID: f7a3c9d21b48
Revises: dd29d05b1f5b
Create Date: 2026-07-30 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a3c9d21b48"
down_revision: str | Sequence[str] | None = "dd29d05b1f5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

handover_event_status_enum = sa.Enum(
    "WAITING", "ACCEPTED", "RESOLVED", "CLOSED", name="handovereventstatus"
)
handover_reason_code_enum = sa.Enum(
    "CUSTOMER_REQUESTED_HUMAN",
    "DISCOUNT_NEGOTIATION",
    "BULK_ORDER",
    "PAYMENT_FAILURE",
    "ORDER_DISPUTE",
    "COMPLAINT",
    "REFUND_REQUEST",
    "DAMAGED_PRODUCT",
    "CUSTOM_ORDER",
    "ACCOUNT_ACCESS_REQUIRED",
    "BUSINESS_RULE_TRIGGERED",
    name="handoverreasoncode",
)

DEFAULT_HANDOVER_NOTIFICATIONS_JSON = (
    '{"dashboard": {"enabled": true, "delay_minutes": 0}, '
    '"whatsapp": {"enabled": true, "delay_minutes": 0}, '
    '"email": {"enabled": true, "delay_minutes": 5}}'
)


def upgrade() -> None:
    """Upgrade schema."""
    # --- users.handover_notifications ---
    op.add_column(
        "users",
        sa.Column(
            "handover_notifications",
            sa.JSON(),
            nullable=False,
            server_default=sa.text(f"'{DEFAULT_HANDOVER_NOTIFICATIONS_JSON}'::json"),
        ),
    )

    # --- handover_events ---
    # Enums are created implicitly by `op.create_table` below (Postgres has
    # no `CREATE TYPE IF NOT EXISTS`, so they must only run once).
    op.create_table(
        "handover_events",
        sa.Column(
            "id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "business_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "conversation_state_id",
            sa.UUID(),
            sa.ForeignKey("conversation_states.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("customer_name", sa.String(100), nullable=True),
        sa.Column("customer_phone", sa.String(20), nullable=False),
        sa.Column("reason_code", handover_reason_code_enum, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("customer_last_message", sa.Text(), nullable=False),
        sa.Column(
            "waiting_start_time",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "status",
            handover_event_status_enum,
            nullable=False,
            server_default="WAITING",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index("ix_handover_events_business_id", "handover_events", ["business_id"])
    op.create_index(
        "ix_handover_events_conversation_state_id", "handover_events", ["conversation_state_id"]
    )
    op.create_index("ix_handover_events_customer_id", "handover_events", ["customer_id"])
    op.create_index("ix_handover_events_status", "handover_events", ["status"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_handover_events_status", table_name="handover_events")
    op.drop_index("ix_handover_events_customer_id", table_name="handover_events")
    op.drop_index("ix_handover_events_conversation_state_id", table_name="handover_events")
    op.drop_index("ix_handover_events_business_id", table_name="handover_events")
    op.drop_table("handover_events")
    handover_event_status_enum.drop(op.get_bind(), checkfirst=True)
    handover_reason_code_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_column("users", "handover_notifications")
