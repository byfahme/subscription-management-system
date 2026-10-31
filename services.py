from models import SUB_STATUSES

# Which status each one may move to next
ALLOWED_MOVES = {
    "draft": ["quotation", "confirmed"],
    "quotation": ["confirmed"],
    "confirmed": ["active"],
    "active": ["closed"],
    "closed": [],
}


def change_subscription_status(sub, new_status):
    """Change a subscription's status. Raises ValueError on an illegal move."""
    if new_status not in SUB_STATUSES:
        raise ValueError(f"Unknown status: {new_status}")

    if new_status not in ALLOWED_MOVES.get(sub.status, []):
        raise ValueError(f"Cannot move from {sub.status} to {new_status}")

    # When a subscription becomes active, billing starts on its start date
    if new_status == "active" and sub.next_billing_date is None:
        sub.next_billing_date = sub.start_date

    sub.status = new_status
    return sub
