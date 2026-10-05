"""Order pricing service - a realistic 'application under test'.

Reads an order (JSON) from stdin and prints a price quote:

    echo '{"items": [{"sku": "BOOK", "price": 12.5, "qty": 2}], "coupon": "SAVE10", "country": "US"}' \
        | python sample_app/order_service.py quote

    ... | python sample_app/order_service.py quote --format text   (printable receipt)

Demo: set DEMO_BUG=1 to introduce a classic pricing bug (tax charged on the
price *before* the discount). The regression suite should catch it.
"""

import argparse
import json
import os
import sys
from decimal import ROUND_HALF_UP, Decimal

COUPONS = {"SAVE10": Decimal("0.10"), "SAVE20": Decimal("0.20")}
TAX_RATES = {"US": Decimal("0.08"), "UK": Decimal("0.20"), "IN": Decimal("0.18")}
CENT = Decimal("0.01")


class OrderError(Exception):
    """Raised for invalid orders; reported to the user with exit code 1."""


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def quote(order: dict) -> dict:
    items = order.get("items") or []
    if not items:
        raise OrderError("order has no items")

    subtotal = Decimal("0")
    for item in items:
        qty = int(item["qty"])
        if qty <= 0:
            raise OrderError(f"invalid quantity for {item['sku']}: {qty}")
        subtotal += Decimal(str(item["price"])) * qty

    coupon = order.get("coupon")
    if coupon and coupon not in COUPONS:
        raise OrderError(f"unknown coupon '{coupon}'")
    discount = money(subtotal * COUPONS.get(coupon, Decimal("0")))

    country = order.get("country", "US")
    if country not in TAX_RATES:
        raise OrderError(f"unsupported country '{country}'")

    taxable = subtotal - discount
    if os.environ.get("DEMO_BUG"):
        taxable = subtotal  # BUG: forgets to apply the discount before tax
    tax = money(taxable * TAX_RATES[country])

    return {
        "item_count": sum(int(item["qty"]) for item in items),
        "subtotal": float(money(subtotal)),
        "discount": float(discount),
        "tax": float(tax),
        "total": float(money(subtotal - discount + tax)),
        "currency": "USD",
        "country": country,
        "coupon": coupon,
    }


def format_receipt(order: dict, result: dict) -> str:
    width = 36
    lines = ["ORDER RECEIPT".center(width), "-" * width]
    for item in order["items"]:
        price = Decimal(str(item["price"]))
        left = f"{item['sku']:<10}{item['qty']:>3} x {price:>7.2f}"
        lines.append(f"{left}{money(price * int(item['qty'])):>{width - len(left)}.2f}")
    lines.append("-" * width)
    lines.append(f"{'Subtotal':<20}{result['subtotal']:>16.2f}")
    if result["discount"]:
        lines.append(f"{'Discount (' + result['coupon'] + ')':<20}{-result['discount']:>16.2f}")
    rate = int(TAX_RATES[result['country']] * 100)
    lines.append(f"{'Tax (' + result['country'] + ' ' + str(rate) + '%)':<20}{result['tax']:>16.2f}")
    lines.append("=" * width)
    lines.append(f"{'TOTAL':<20}{result['total']:>16.2f}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Order pricing service")
    parser.add_argument("action", choices=["quote"])
    parser.add_argument("--format", choices=["json", "text"], default="json")
    args = parser.parse_args()

    try:
        order = json.loads(sys.stdin.read())
    except json.JSONDecodeError as error:
        print(f"Error: invalid JSON input ({error.msg})", file=sys.stderr)
        return 2

    try:
        result = quote(order)
    except OrderError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(format_receipt(order, result) if args.format == "text" else json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
