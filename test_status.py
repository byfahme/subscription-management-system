from datetime import date
from models import Subscription
from services import change_subscription_status

failures = 0


def check(name, ok):
    global failures
    print(("PASS  " if ok else "FAIL  ") + name)
    if not ok:
        failures += 1


def make(status="draft", start=date(2026, 11, 1)):
    return Subscription(status=status, start_date=start)


def rejects(sub, new_status):
    try:
        change_subscription_status(sub, new_status)
    except ValueError:
        return True
    return False


# 1. Full happy path
s = make()
for step in ["quotation", "confirmed", "active", "closed"]:
    change_subscription_status(s, step)
    check(f"moved to {step}", s.status == step)

# 2. Allowed shortcut
s = make()
change_subscription_status(s, "confirmed")
check("draft -> confirmed allowed", s.status == "confirmed")

# 3. Illegal jumps must be rejected AND leave the status unchanged
illegal = [
    ("draft", "active"), ("draft", "closed"),
    ("quotation", "active"), ("confirmed", "closed"),
    ("active", "draft"), ("closed", "active"), ("closed", "draft"),
]
for frm, to in illegal:
    s = make(frm)
    check(f"{frm} -> {to} rejected", rejects(s, to) and s.status == frm)

# 4. Unknown status
check("unknown status rejected", rejects(make(), "banana"))

# 5. next_billing_date on activation
s = make("confirmed")
change_subscription_status(s, "active")
check("next_billing_date = start_date on activate",
      s.next_billing_date == date(2026, 11, 1))

s = make("confirmed")
s.next_billing_date = date(2026, 12, 1)
change_subscription_status(s, "active")
check("existing next_billing_date kept",
      s.next_billing_date == date(2026, 12, 1))

# 6. Missing start date (warning, not a failure)
s = make("confirmed", start=None)
change_subscription_status(s, "active")
if s.next_billing_date is None:
    print("WARN  activating with no start_date leaves next_billing_date empty")

print()
print("ALL PASSED" if failures == 0 else f"{failures} FAILED")
