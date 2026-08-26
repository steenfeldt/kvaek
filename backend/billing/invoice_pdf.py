"""Simple A4 invoice PDF (reportlab — no system dependencies)."""

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _kr(ore: int) -> str:
    kroner, rest = divmod(ore, 100)
    return f"{kroner:,}".replace(",", ".") + f",{rest:02d} kr."


def render_invoice_pdf(inv) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    left, right = 22 * mm, width - 22 * mm

    y = height - 28 * mm
    c.setFillColorRGB(0.70, 0.33, 0.20)  # clay
    c.setFont("Helvetica-Bold", 24)
    c.drawString(left, y, "Faktura")
    c.setFillColorRGB(0.17, 0.13, 0.09)
    c.setFont("Helvetica", 10)
    c.drawRightString(right, y + 4 * mm, f"Fakturanr.: {inv.number}")
    c.drawRightString(right, y - 1 * mm, f"Dato: {inv.issued_at:%d-%m-%Y}")

    y -= 18 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, "Sælger")
    c.drawString(width / 2, y, "Køber")
    c.setFont("Helvetica", 9)
    seller_lines = [
        inv.seller_name,
        f"CVR: {inv.seller_cvr}" if inv.seller_cvr else "CVR: under registrering",
        inv.seller_address,
        inv.seller_email,
    ]
    buyer_lines = [inv.buyer_company, f"CVR: {inv.buyer_cvr}" if inv.buyer_cvr else "", inv.buyer_email]
    yy = y
    for line in seller_lines:
        if line:
            yy -= 4.6 * mm
            c.drawString(left, yy, line)
    yy = y
    for line in buyer_lines:
        if line:
            yy -= 4.6 * mm
            c.drawString(width / 2, yy, line)

    y -= 32 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left, y, "Beskrivelse")
    c.drawRightString(right, y, "Beløb")
    y -= 2 * mm
    c.setLineWidth(0.5)
    c.line(left, y, right, y)
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    c.drawString(left, y, inv.description[:90])
    c.drawRightString(right, y, _kr(inv.net_ore))

    y -= 10 * mm
    c.line(width / 2, y, right, y)
    y -= 6 * mm
    c.drawString(width / 2, y, "Subtotal (ekskl. moms)")
    c.drawRightString(right, y, _kr(inv.net_ore))
    y -= 5.5 * mm
    c.drawString(width / 2, y, "Moms (25%)")
    c.drawRightString(right, y, _kr(inv.vat_ore))
    y -= 6.5 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(width / 2, y, "Total")
    c.drawRightString(right, y, _kr(inv.gross_ore))

    y -= 16 * mm
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.42, 0.36, 0.31)
    c.drawString(left, y, "Beløbet er betalt via Mollie. Denne faktura er kvittering for købet.")

    c.showPage()
    c.save()
    return buf.getvalue()
