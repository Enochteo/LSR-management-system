"""Reporting service — CSV and PDF export.

Both formats are produced from the same shared query so totals
and row counts always match between the two export types.
"""

import csv
import io
import logging
from datetime import date, datetime

from database.models import AttendanceRecord
from extensions import db
from services.admin_service import AdminService

logger = logging.getLogger(__name__)

_admin_svc = AdminService()

# Column definitions shared by CSV and PDF.
_COLUMNS = [
    ("Student Name", "student_name"),
    ("Student ID", "student_id"),
    ("Room", "room_name"),
    ("Sign-In Time", "sign_in_time"),
    ("Sign-Out Time", "sign_out_time"),
    ("Duration (min)", "duration"),
    ("Status", "status"),
]


class ReportService:
    """Produce daily attendance reports in CSV and PDF formats."""

    def get_daily_sessions(self, target_date: date | None = None) -> list[dict]:
        """Return session rows for *target_date* (defaults to today)."""
        return _admin_svc.get_daily_sessions(target_date)

    def render_daily_csv(self, target_date: date | None = None) -> bytes:
        """Return UTF-8 encoded CSV bytes for the daily attendance report."""
        sessions = self.get_daily_sessions(target_date)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([col for col, _ in _COLUMNS])
        for s in sessions:
            writer.writerow([s.get(key, "") or "" for _, key in _COLUMNS])
        return output.getvalue().encode("utf-8")

    def render_daily_pdf(self, target_date: date | None = None) -> bytes:
        """Return PDF bytes for the daily attendance report using ReportLab."""
        try:
            return self._build_pdf(target_date)
        except ImportError:
            logger.error("reportlab is not installed; PDF export unavailable.")
            raise RuntimeError(
                "PDF generation requires the 'reportlab' package. "
                "Run: pip install reportlab"
            )

    # ------------------------------------------------------------------ #
    # PDF internals                                                        #
    # ------------------------------------------------------------------ #

    def _build_pdf(self, target_date: date | None) -> bytes:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        sessions = self.get_daily_sessions(target_date)
        label_date = target_date or datetime.utcnow().date()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(
            Paragraph(
                f"Daily Attendance Report — {label_date.strftime('%B %d, %Y')}",
                styles["Title"],
            )
        )
        elements.append(
            Paragraph(
                f"Total sessions: {len(sessions)}",
                styles["Normal"],
            )
        )
        elements.append(Spacer(1, 0.25 * inch))

        # Table data
        header_row = [col for col, _ in _COLUMNS]
        data_rows = [
            [str(s.get(key) or "—") for _, key in _COLUMNS]
            for s in sessions
        ]
        table_data = [header_row] + data_rows

        col_widths = [1.6 * inch, 1.1 * inch, 1.4 * inch, 1.6 * inch, 1.6 * inch, 1.0 * inch, 1.0 * inch]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3c5e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f9")]),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        elements.append(table)
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
