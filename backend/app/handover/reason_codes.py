"""
Reason-code vocabulary for Human Handover events.

`HandoverReasonCode` (app/models.py) is the machine-readable value persisted
to the database. This module owns the human-readable labels the frontend
should display, plus a deterministic keyword classifier so every handover
gets a specific reason instead of a generic one — without an extra LLM call
on the hot request path.
"""

from __future__ import annotations

from app.models import HandoverReasonCode

REASON_CODE_LABELS: dict[HandoverReasonCode, str] = {
    HandoverReasonCode.CUSTOMER_REQUESTED_HUMAN: "Customer requested a human",
    HandoverReasonCode.DISCOUNT_NEGOTIATION: "Discount negotiation",
    HandoverReasonCode.BULK_ORDER: "Bulk order inquiry",
    HandoverReasonCode.PAYMENT_FAILURE: "Payment failure",
    HandoverReasonCode.ORDER_DISPUTE: "Order dispute",
    HandoverReasonCode.COMPLAINT: "Complaint",
    HandoverReasonCode.REFUND_REQUEST: "Refund request",
    HandoverReasonCode.DAMAGED_PRODUCT: "Damaged product",
    HandoverReasonCode.CUSTOM_ORDER: "Custom order request",
    HandoverReasonCode.ACCOUNT_ACCESS_REQUIRED: "Account access required",
    HandoverReasonCode.BUSINESS_RULE_TRIGGERED: "Business rule triggered",
}


def reason_label(reason_code: HandoverReasonCode) -> str:
    """Human-readable label for a reason code. Frontend should always render
    this, never the raw `reason_code` value."""
    return REASON_CODE_LABELS.get(reason_code, reason_code.value.replace("_", " ").title())


# Keyword -> reason code, checked in order (first match wins). Mirrors the
# existing `URGENT_KEYWORDS` heuristic in app/ai/service.py — same tradeoff:
# cheap, deterministic, no extra AI round-trip before a handover notification
# can go out.
_REASON_KEYWORDS: list[tuple[HandoverReasonCode, tuple[str, ...]]] = [
    (
        HandoverReasonCode.REFUND_REQUEST,
        ("refund", "rudisha pesa", "money back"),
    ),
    (
        HandoverReasonCode.DAMAGED_PRODUCT,
        ("damaged", "broken", "faulty", "defective"),
    ),
    (
        HandoverReasonCode.ORDER_DISPUTE,
        ("dispute", "never arrived", "wrong item", "missing item", "didn't receive"),
    ),
    (
        HandoverReasonCode.PAYMENT_FAILURE,
        ("payment failed", "mpesa failed", "transaction failed", "payment error"),
    ),
    (
        HandoverReasonCode.COMPLAINT,
        ("complaint", "malalamiko", "terrible", "angry", "hasira", "scam", "fraud"),
    ),
    (
        HandoverReasonCode.DISCOUNT_NEGOTIATION,
        ("discount", "lower price", "cheaper", "negotiate", "best price"),
    ),
    (
        HandoverReasonCode.BULK_ORDER,
        ("bulk", "wholesale", "in bulk", "large order", "many units"),
    ),
    (
        HandoverReasonCode.CUSTOM_ORDER,
        ("custom order", "custom made", "customize", "bespoke"),
    ),
    (
        HandoverReasonCode.ACCOUNT_ACCESS_REQUIRED,
        ("can't log in", "cannot log in", "account locked", "reset my password"),
    ),
    (
        HandoverReasonCode.CUSTOMER_REQUESTED_HUMAN,
        ("talk to a human", "speak to a person", "real person", "human agent", "ongea na mtu"),
    ),
]


def classify_handover_reason(customer_message: str) -> HandoverReasonCode:
    """Best-effort deterministic reason classification from the customer's
    triggering message. Falls back to BUSINESS_RULE_TRIGGERED when nothing
    matches — AISHA still decided a handover was warranted via the
    [HANDOVER_REQUIRED] tag, just not for a keyword-detectable reason."""
    text_lower = customer_message.lower()
    for code, keywords in _REASON_KEYWORDS:
        if any(keyword in text_lower for keyword in keywords):
            return code
    return HandoverReasonCode.BUSINESS_RULE_TRIGGERED
