# events/pdf_views.py
# =============================================
#  PDF Ticket Download — the most impressive
#  visual feature. Generates a professional
#  PDF ticket with QR code embedded.
#
#  Install first:  pip install reportlab qrcode[pil]
# =============================================

import io
import qrcode
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units    import mm
from reportlab.lib.colors   import HexColor, white, black
from reportlab.pdfgen       import canvas as pdf_canvas
from reportlab.lib.utils    import ImageReader

from .models import Registration


@login_required
def download_ticket_pdf(request, registration_pk):
    """
    Generates and streams a beautifully designed PDF ticket.
    The ticket includes: event details, QR code, check-in code.
    """
    reg   = get_object_or_404(Registration, pk=registration_pk, user=request.user)
    event = reg.event

    # ── Set up the PDF response ──
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="eventify-ticket-{reg.check_in_code}.pdf"'
    )

    # ── Create the canvas (A4 landscape, ticket-style) ──
    # Ticket dimensions: 200mm wide × 85mm tall (credit card ratio)
    W, H = 200 * mm, 85 * mm
    c = pdf_canvas.Canvas(response, pagesize=(W, H))

    # ── COLOUR PALETTE ──
    BRAND   = HexColor('#FF4D6D')
    DARK    = HexColor('#0A0A0A')
    SURFACE = HexColor('#111111')
    BORDER  = HexColor('#242424')
    MUTED   = HexColor('#888888')
    WHITE   = white

    # ── BACKGROUND ──
    c.setFillColor(DARK)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── LEFT COLOUR STRIP (brand accent) ──
    c.setFillColor(BRAND)
    c.rect(0, 0, 6 * mm, H, fill=1, stroke=0)

    # ── TEAR LINE (dashed vertical) ──
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.setDash(3, 4)
    c.line(148 * mm, 5 * mm, 148 * mm, H - 5 * mm)
    c.setDash()   # Reset dash

    # ── LOGO / BRAND ──
    c.setFillColor(BRAND)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(12 * mm, H - 14 * mm, '⚡ EVENTIFY')

    # ── EVENT TITLE ──
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 16)
    # Truncate long titles
    title = event.title[:35] + ('...' if len(event.title) > 35 else '')
    c.drawString(12 * mm, H - 26 * mm, title)

    # ── EVENT DETAILS ──
    c.setFont('Helvetica', 9)
    c.setFillColor(MUTED)

    details = [
        ('📅', event.date.strftime('%A, %B %d, %Y')),
        ('🕐', event.date.strftime('%I:%M %p')),
        ('📍', event.location[:45] + ('...' if len(event.location) > 45 else '')),
        ('💰', 'Free' if event.price == 0 else f'KES {event.price}'),
        ('👤', f'Registered: {reg.user.get_full_name() or reg.user.username}'),
    ]

    y = H - 36 * mm
    for icon, text in details:
        c.setFillColor(BRAND)
        c.drawString(12 * mm, y, icon)
        c.setFillColor(MUTED)
        c.drawString(20 * mm, y, text)
        y -= 7 * mm

    # ── DIVIDER DOTS ──
    c.setFillColor(BORDER)
    for i in range(10):
        dot_y = H / 2 + (i - 4.5) * 6 * mm
        c.circle(148 * mm, dot_y, 1.5 * mm, fill=1, stroke=0)

    # ── RIGHT SIDE: QR CODE ──
    qr = qrcode.QRCode(box_size=4, border=2, error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(reg.check_in_code)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color='#FF4D6D', back_color='#0A0A0A')

    # Convert QR image to bytes for ReportLab
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    # Draw QR code on the right side of the ticket
    qr_size = 48 * mm
    qr_x    = 152 * mm
    qr_y    = (H - qr_size) / 2

    # White background for QR
    c.setFillColor(HexColor('#0A0A0A'))
    c.roundRect(qr_x - 2 * mm, qr_y - 2 * mm, qr_size + 4 * mm, qr_size + 4 * mm, 2 * mm, fill=1, stroke=0)

    c.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size)

    # ── CHECK-IN CODE below QR ──
    c.setFont('Helvetica-Bold', 10)
    c.setFillColor(BRAND)
    code_x = qr_x + qr_size / 2
    c.drawCentredString(code_x, qr_y - 8 * mm, reg.check_in_code)
    c.setFont('Helvetica', 7)
    c.setFillColor(MUTED)
    c.drawCentredString(code_x, qr_y - 13 * mm, 'Show at the door')

    # ── BOTTOM STRIP ──
    c.setFillColor(HexColor('#1A1A1A'))
    c.rect(0, 0, W, 10 * mm, fill=1, stroke=0)

    c.setFillColor(BRAND)
    c.setFont('Helvetica', 7)
    c.drawString(12 * mm, 3.5 * mm, f'Ticket ID: {reg.check_in_code}  •  Issued: {timezone.now().strftime("%d %b %Y")}  •  eventify.co.ke')

    c.setFillColor(MUTED)
    c.drawRightString(W - 12 * mm, 3.5 * mm, 'This ticket is non-transferable')

    # ── Save ──
    c.save()
    return response
