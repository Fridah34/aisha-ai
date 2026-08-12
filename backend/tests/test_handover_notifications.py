"""
Unit tests for the Human Handover Notification system's pure-function
building blocks: reason classification, waiting-duration formatting, and
settings validation. No DB/AI/Redis/network side effects.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.handover.reason_codes import classify_handover_reason, reason_label
from app.handover.schemas import (
    HandoverChannelSettings,
    HandoverNotificationSettings,
)
from app.handover.utils import format_waiting_duration
from app.models import HandoverReasonCode


class TestClassifyHandoverReason:
    def test_refund_request(self):
        assert (
            classify_handover_reason("I want a refund for this order")
            == HandoverReasonCode.REFUND_REQUEST
        )

    def test_damaged_product(self):
        assert (
            classify_handover_reason("The item I received is damaged")
            == HandoverReasonCode.DAMAGED_PRODUCT
        )

    def test_discount_negotiation(self):
        assert (
            classify_handover_reason("Can you give me a discount on this?")
            == HandoverReasonCode.DISCOUNT_NEGOTIATION
        )

    def test_bulk_order(self):
        assert (
            classify_handover_reason("I'd like to place a bulk order of 500 units")
            == HandoverReasonCode.BULK_ORDER
        )

    def test_customer_requested_human(self):
        assert (
            classify_handover_reason("I want to talk to a human please")
            == HandoverReasonCode.CUSTOMER_REQUESTED_HUMAN
        )

    def test_fallback_to_business_rule_triggered(self):
        assert (
            classify_handover_reason("asdkjfhaskjdfh random unrelated text")
            == HandoverReasonCode.BUSINESS_RULE_TRIGGERED
        )

    def test_every_reason_code_has_a_label(self):
        for code in HandoverReasonCode:
            label = reason_label(code)
            assert label and label != code.value


class TestFormatWaitingDuration:
    def test_just_now(self):
        now = datetime.now(timezone.utc)
        assert format_waiting_duration(now, now=now) == "Just now"

    def test_minutes_only(self):
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=7)
        assert format_waiting_duration(start, now=now) == "7 minutes"

    def test_singular_minute(self):
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=1)
        assert format_waiting_duration(start, now=now) == "1 minute"

    def test_hours_and_minutes(self):
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=1, minutes=12)
        assert format_waiting_duration(start, now=now) == "1 hour 12 minutes"

    def test_exact_hour_no_minutes_suffix(self):
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=2)
        assert format_waiting_duration(start, now=now) == "2 hours"


class TestHandoverNotificationSettingsValidation:
    def test_delay_minutes_defaults(self):
        settings = HandoverNotificationSettings()
        assert settings.dashboard.delay_minutes == 0
        assert settings.whatsapp.delay_minutes == 0
        assert settings.email.delay_minutes == 5

    def test_delay_minutes_within_range_is_valid(self):
        assert HandoverChannelSettings(enabled=True, delay_minutes=120).delay_minutes == 120
        assert HandoverChannelSettings(enabled=True, delay_minutes=0).delay_minutes == 0

    def test_delay_minutes_over_120_is_rejected(self):
        with pytest.raises(ValidationError):
            HandoverChannelSettings(enabled=True, delay_minutes=121)

    def test_delay_minutes_negative_is_rejected(self):
        with pytest.raises(ValidationError):
            HandoverChannelSettings(enabled=True, delay_minutes=-1)
