"""Create PDF documents for exported orders."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable

from fpdf import FPDF
from service.utils.exporting.models import OrderExportRow


class OrdersPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Order export", ln=True)
        self.ln(2)


def _format_currency(value: Decimal) -> str:
    normalized = value.quantize(Decimal("0.01"))
    return f"{normalized:,.2f}"


def _format_date(value: datetime | None) -> str:
    if not value:
        return "-"

    return value.strftime("%Y-%m-%d %H:%M:%S")


def render_orders_pdf(orders: Iterable[OrderExportRow]) -> bytes:
    pdf = OrdersPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.set_title("Orders export")
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)

    rows = list(orders)
    if not rows:
        pdf.cell(0, 6, "No orders match the current filters", ln=True)
        return pdf.output(dest="S").encode("latin-1")

    for index, order in enumerate(rows, start=1):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, f"{index}. Order {order.order_number}", ln=True)
        pdf.set_font("Helvetica", size=10)
        pdf.cell(
            0,
            5,
            (
                f"Status: {order.status} | Payment status: {order.payment_status} | "
                f"Payment method: {order.payment_method}"
            ),
            ln=True,
        )
        pdf.cell(
            0,
            5,
            (
                f"Delivery type: {order.delivery_type} | Total: {_format_currency(order.total)} | "
                f"Delivery cost: {_format_currency(order.delivery_cost)}"
            ),
            ln=True,
        )
        pdf.cell(
            0,
            5,
            f"Subtotal: {_format_currency(order.subtotal)} | Promo discount: {_format_currency(order.promo_discount)} | "
            f"Bonus discount: {_format_currency(order.bonus_discount)}",
            ln=True,
        )
        pdf.cell(
            0,
            5,
            (
                f"Recipient: {order.recipient_name} | Email: {order.recipient_email or '-'} | "
                f"Phone: {order.recipient_phone or '-'}"
            ),
            ln=True,
        )
        pdf.cell(
            0,
            5,
            f"City: {order.delivery_city or '-'} | Address: {order.delivery_address or '-'}",
            ln=True,
        )
        pdf.cell(0, 5, f"Created: {_format_date(order.created_at)}", ln=True)
        pdf.ln(2)

    return pdf.output(dest="S").encode("latin-1")
