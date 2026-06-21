"""
PDF Report Generator for Lupe CTI.

Professional email analysis reports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lupe.models import EmailAnalysisResult

import re
from datetime import datetime
from pathlib import Path

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# A.D.S Security Color Palette
COLOR_ACCENT = HexColor("#00D4FF")  # cyan A.D.S
COLOR_RED = HexColor("#FF3B30")
COLOR_YELLOW = HexColor("#FFD60A")
COLOR_GREEN = HexColor("#30D158")
COLOR_GRAY = HexColor("#8E8E93")
COLOR_DARK = HexColor("#1C1C1E")  # section headers
COLOR_BG_ROW = HexColor("#F2F2F7")  # table alternating rows


class ScoreBar(Flowable):
    """Custom flowable for drawing a visual score bar."""

    def __init__(self, score: float, width: float = 400, height: float = 16):
        super().__init__()
        self.score = score
        self.width = width
        self.height = height

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        return (self.width, self.height)

    def draw(self) -> None:
        # Determine color based on score
        if self.score >= 7:
            fill_color = COLOR_RED
        elif self.score >= 4:
            fill_color = COLOR_YELLOW
        else:
            fill_color = COLOR_GREEN

        # Draw background bar (gray)
        self.canv.setFillColor(COLOR_GRAY)
        self.canv.rect(0, 0, self.width, self.height, fill=True, stroke=False)

        # Draw filled portion
        filled_width = (self.score / 10) * self.width
        self.canv.setFillColor(fill_color)
        self.canv.rect(0, 0, filled_width, self.height, fill=True, stroke=False)

        # Draw border
        self.canv.setStrokeColor(COLOR_DARK)
        self.canv.rect(0, 0, self.width, self.height, fill=False, stroke=True)


def _get_auth_status_color(status: str | None) -> HexColor:
    """Get color for authentication status."""
    if status is None:
        return COLOR_GRAY
    status_lower = status.lower()
    if status_lower in ("pass", "passe", "ok"):
        return COLOR_GREEN
    elif status_lower in ("fail", "failed", "error", "permerror"):
        return COLOR_RED
    elif status_lower in ("softfail", "temperror", "neutral"):
        return COLOR_YELLOW
    else:
        return COLOR_GRAY


def _get_severity_color(severity: str) -> HexColor:
    """Get color for severity level."""
    severity_lower = severity.lower()
    if severity_lower in ("critical", "high"):
        return COLOR_RED
    elif severity_lower == "medium":
        return COLOR_YELLOW
    elif severity_lower == "info":
        return COLOR_GREEN
    else:
        return COLOR_GRAY


def _create_circle_bullet(color: HexColor) -> str:
    """Create a colored circle bullet for table display."""
    return f'<font color="{color.hexval()}">&#9679;</font>'


def _escape_xml(text: str) -> str:
    """Escape text for safe inclusion in ReportLab Paragraph XML."""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_email_report(result: EmailAnalysisResult, output_dir: str) -> str:
    """Generate PDF report of phishing email analysis.

    Args:
        result: EmailAnalysisResult with all analysis data
        output_dir: Directory to save the PDF file

    Returns:
        Path to the generated PDF file
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate filename from subject
    subject_raw = result.headers.subject or "email"
    subject_slug = re.sub(r"[^\w\-]", "_", subject_raw[:30]).strip("_") or "email"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"email_analysis_{subject_slug}_{timestamp}.pdf"
    filepath = output_path / filename

    # Create document
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=2 * 28.35,  # 2cm in points
        leftMargin=2 * 28.35,
        topMargin=2 * 28.35,
        bottomMargin=2 * 28.35,
    )

    # Container for elements
    elements: list = []
    styles = getSampleStyleSheet()

    # Section title style
    section_title_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        textColor=white,
        backColor=COLOR_DARK,
        spaceAfter=8,
        spaceBefore=16,
        leftIndent=6,
        rightIndent=6,
        fontSize=11,
        leading=14,
    )

    label_style = ParagraphStyle(
        "Label", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9
    )

    # ========== HEADER ==========
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    header_data = [
        [
            Paragraph(
                "<b>A.D.S Security</b>",
                ParagraphStyle(
                    "HeaderTitle",
                    parent=styles["Heading1"],
                    textColor=COLOR_ACCENT,
                    fontSize=18,
                ),
            ),
            Paragraph(
                f"<b>INFORME DE ANALISIS DE EMAIL SOSPECHOSO</b><br/>"
                f'<font size="9">Fecha: {current_date}</font><br/>'
                f'<font size="9">Archivo: {_escape_xml(result.file_path)}</font>',
                ParagraphStyle("HeaderRight", parent=styles["Normal"], alignment=2, fontSize=10),
            ),
        ]
    ]

    header_table = Table(header_data, colWidths=[250, 250])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=2, color=COLOR_ACCENT))
    elements.append(Spacer(1, 12))

    # ========== SECTION 1: EMAIL METADATA ==========
    elements.append(Paragraph("1. DATOS DEL EMAIL", section_title_style))

    from_addr = result.headers.from_addr or "N/A"
    to_addr = ", ".join(result.headers.to_addr) if result.headers.to_addr else "N/A"
    subject = result.headers.subject or "N/A"
    date = result.headers.date or "N/A"
    reply_to = result.headers.reply_to or "N/A"
    message_id = result.headers.message_id or "N/A"

    # Check reply-to discrepancy
    reply_to_warning = ""
    reply_to_color = black
    if result.headers.reply_to and result.headers.from_addr:
        reply_domain = (
            result.headers.reply_to.split("@")[-1] if "@" in result.headers.reply_to else ""
        )
        from_domain = (
            result.headers.from_addr.split("@")[-1] if "@" in result.headers.from_addr else ""
        )
        if reply_domain and from_domain and reply_domain != from_domain:
            reply_to_warning = " &#9888; DOMINIO DIFERENTE"
            reply_to_color = COLOR_RED

    metadata_data = [
        [Paragraph("De:", label_style), Paragraph(_escape_xml(from_addr), styles["Normal"])],
        [Paragraph("Para:", label_style), Paragraph(_escape_xml(to_addr), styles["Normal"])],
        [Paragraph("Asunto:", label_style), Paragraph(_escape_xml(subject), styles["Normal"])],
        [Paragraph("Fecha:", label_style), Paragraph(_escape_xml(date), styles["Normal"])],
        [
            Paragraph("Reply-To:", label_style),
            Paragraph(
                f'<font color="{reply_to_color.hexval()}">'
                f"{_escape_xml(reply_to)}{reply_to_warning}</font>",
                styles["Normal"],
            ),
        ],
        [
            Paragraph("Message-ID:", label_style),
            Paragraph(_escape_xml(message_id), styles["Normal"]),
        ],
    ]

    metadata_table = Table(metadata_data, colWidths=[100, 400])
    metadata_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(metadata_table)

    # ========== SECTION 2: AUTHENTICATION ==========
    elements.append(Paragraph("2. AUTENTICACION", section_title_style))

    spf_color = _get_auth_status_color(result.auth.spf)
    dkim_color = _get_auth_status_color(result.auth.dkim)
    dmarc_color = _get_auth_status_color(result.auth.dmarc)

    auth_data = [
        [
            Paragraph("<b>SPF</b>", styles["Normal"]),
            Paragraph("<b>DKIM</b>", styles["Normal"]),
            Paragraph("<b>DMARC</b>", styles["Normal"]),
        ],
        [
            Paragraph(_create_circle_bullet(spf_color), styles["Normal"]),
            Paragraph(_create_circle_bullet(dkim_color), styles["Normal"]),
            Paragraph(_create_circle_bullet(dmarc_color), styles["Normal"]),
        ],
        [
            Paragraph(result.auth.spf or "N/A", styles["Normal"]),
            Paragraph(result.auth.dkim or "N/A", styles["Normal"]),
            Paragraph(result.auth.dmarc or "N/A", styles["Normal"]),
        ],
    ]

    auth_table = Table(auth_data, colWidths=[150, 150, 150], hAlign="CENTER")
    auth_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(auth_table)

    # ========== SECTION 3: PHISHING SCORE ==========
    elements.append(Paragraph("3. SCORE DE PHISHING", section_title_style))

    score = result.phishing_score.total if result.phishing_score else 0.0
    score_color = COLOR_RED if score >= 7 else COLOR_YELLOW if score >= 4 else COLOR_GREEN

    score_text = f"<b>{score:.1f} / 10</b>"
    elements.append(
        Paragraph(
            score_text,
            ParagraphStyle(
                "ScoreValue",
                parent=styles["Heading1"],
                textColor=score_color,
                fontSize=24,
                alignment=1,
            ),
        )
    )

    # Score bar
    elements.append(Spacer(1, 8))
    elements.append(ScoreBar(score))
    elements.append(Spacer(1, 12))

    # Indicators list (indicators is list[str] in the model)
    if result.phishing_score and result.phishing_score.indicators:
        elements.append(Paragraph("<b>Indicadores:</b>", label_style))
        for indicator in result.phishing_score.indicators:
            elements.append(Paragraph(f"  - {_escape_xml(indicator)}", styles["Normal"]))
        elements.append(Spacer(1, 4))

    # Score breakdown (breakdown is dict[str, float])
    if result.phishing_score and result.phishing_score.breakdown:
        breakdown_data = [
            [Paragraph("<b>Componente</b>", label_style), Paragraph("<b>Puntaje</b>", label_style)]
        ]
        for component, value in result.phishing_score.breakdown.items():
            breakdown_data.append(
                [
                    Paragraph(_escape_xml(component), styles["Normal"]),
                    Paragraph(f"{value:.1f}", styles["Normal"]),
                ]
            )

        breakdown_table = Table(breakdown_data, colWidths=[300, 200])
        breakdown_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLOR_BG_ROW]),
                ]
            )
        )
        elements.append(breakdown_table)

    # ========== SECTION 4: IOCS ==========
    elements.append(Paragraph("4. IOCs ENCONTRADOS", section_title_style))

    if result.iocs_found and len(result.iocs_found) > 0:
        # Build enrichment lookup: ioc_value -> list of EnrichmentResult
        enrichment_lookup: dict = {}
        if result.enrichments:
            for _source, enrichment_list in result.enrichments.items():
                for er in enrichment_list:
                    enrichment_lookup.setdefault(er.ioc_value, []).append(er)

        iocs_data = [
            [
                Paragraph("<b>Tipo</b>", label_style),
                Paragraph("<b>Valor</b>", label_style),
                Paragraph("<b>Severidad</b>", label_style),
            ]
        ]
        for ioc in result.iocs_found:
            ioc_type = ioc.type.value if hasattr(ioc.type, "value") else str(ioc.type)
            ioc_value = ioc.value or "N/A"

            # Try to get severity from enrichments
            severity = "info"
            enrichments_for_ioc = enrichment_lookup.get(ioc_value, [])
            if enrichments_for_ioc:
                # Use the highest severity found
                sev_order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
                best = max(enrichments_for_ioc, key=lambda e: sev_order.get(e.severity.value, 0))
                severity = (
                    best.severity.value if hasattr(best.severity, "value") else str(best.severity)
                )

            severity_color = _get_severity_color(severity)
            iocs_data.append(
                [
                    Paragraph(_escape_xml(ioc_type), styles["Normal"]),
                    Paragraph(_escape_xml(ioc_value), styles["Normal"]),
                    Paragraph(
                        f'<font color="{severity_color.hexval()}">'
                        f"{_escape_xml(severity.upper())}</font>",
                        styles["Normal"],
                    ),
                ]
            )

        iocs_table = Table(iocs_data, colWidths=[100, 300, 100])
        iocs_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLOR_BG_ROW]),
                ]
            )
        )
        elements.append(iocs_table)
    else:
        elements.append(Paragraph("No se encontraron IOCs.", styles["Normal"]))

    # ========== SECTION 5: AI ANALYSIS ==========
    elements.append(Paragraph("5. ANALISIS DE IA", section_title_style))

    if result.ai_classification:
        ai_data = [
            [
                Paragraph("<b>Clasificacion:</b>", label_style),
                Paragraph(_escape_xml(result.ai_classification), styles["Normal"]),
            ],
            [
                Paragraph("<b>Confianza:</b>", label_style),
                Paragraph(
                    f"{result.ai_confidence:.0%}" if result.ai_confidence is not None else "N/A",
                    styles["Normal"],
                ),
            ],
        ]

        ai_table = Table(ai_data, colWidths=[120, 380])
        ai_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(ai_table)

        # Techniques
        if result.ai_techniques:
            elements.append(Spacer(1, 8))
            elements.append(Paragraph("<b>Tecnicas detectadas:</b>", label_style))
            for technique in result.ai_techniques:
                elements.append(Paragraph(f"  - {_escape_xml(technique)}", styles["Normal"]))

        # Recommendations
        if result.ai_recommendations:
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("<b>Recomendaciones:</b>", label_style))
            rec_data = [[Paragraph("Recomendacion", label_style)]]
            for rec in result.ai_recommendations:
                rec_data.append([Paragraph(f"- {_escape_xml(rec)}", styles["Normal"])])

            rec_table = Table(rec_data, colWidths=[500])
            rec_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
                        ("TEXTCOLOR", (0, 0), (-1, 0), white),
                    ]
                )
            )
            elements.append(rec_table)
    else:
        elements.append(Paragraph("No hay analisis de IA disponible.", styles["Normal"]))

    # ========== SECTION 6: ATTACHMENTS ==========
    elements.append(Paragraph("6. ADJUNTOS", section_title_style))

    if result.attachments and len(result.attachments) > 0:
        att_data = [
            [
                Paragraph("<b>Nombre</b>", label_style),
                Paragraph("<b>Tipo MIME</b>", label_style),
                Paragraph("<b>Tamano</b>", label_style),
                Paragraph("<b>SHA256</b>", label_style),
                Paragraph("<b>Riesgo</b>", label_style),
            ]
        ]
        for att in result.attachments:
            name = att.filename or "N/A"
            mime = att.mime_type or "N/A"
            size = att.size_bytes or 0
            sha256 = att.sha256 or ""
            is_exec = att.is_executable

            risk_display = (
                f'<font color="{COLOR_RED.hexval()}">EJECUTABLE</font>' if is_exec else "Bajo"
            )

            size_str = f"{size:,} bytes" if size else "N/A"
            sha_short = sha256[:16] + "..." if sha256 else "N/A"

            att_data.append(
                [
                    Paragraph(_escape_xml(name), styles["Normal"]),
                    Paragraph(_escape_xml(mime), styles["Normal"]),
                    Paragraph(size_str, styles["Normal"]),
                    Paragraph(sha_short, styles["Normal"]),
                    Paragraph(risk_display, styles["Normal"]),
                ]
            )

        att_table = Table(att_data, colWidths=[120, 100, 80, 120, 80])
        att_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLOR_BG_ROW]),
                ]
            )
        )
        elements.append(att_table)
    else:
        elements.append(Paragraph("No hay adjuntos.", styles["Normal"]))

    # ========== SECTION 7: RECEIVED CHAIN ==========
    elements.append(Paragraph("7. CADENA DE RECEPCION (Received)", section_title_style))

    if result.received_chain and len(result.received_chain) > 0:
        for idx, hop in enumerate(result.received_chain, 1):
            hop_from = _escape_xml(hop.from_host or "unknown")
            hop_by = _escape_xml(hop.by_host or "unknown")
            hop_ts = f" | {_escape_xml(hop.timestamp)}" if hop.timestamp else ""
            hop_country = f" [{_escape_xml(hop.country_code)}]" if hop.country_code else ""

            warning = (
                f' <font color="{COLOR_RED.hexval()}">&#9888; SOSPECHOSO</font>'
                if hop.is_suspicious
                else ""
            )

            elements.append(
                Paragraph(
                    f"<b>{idx}.</b> From: {hop_from} | By: {hop_by}{hop_ts}{hop_country}{warning}",
                    styles["Normal"],
                )
            )
    else:
        elements.append(Paragraph("No hay datos de cadena de recepcion.", styles["Normal"]))

    # ========== FOOTER CALLBACK ==========
    def add_footer(canvas: Canvas, doc):
        canvas.saveState()
        footer_text = (
            f"CONFIDENCIAL -- Lupe CTI | Generado por Lupe CTI v1.0.0 | "
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        canvas.setFillColor(COLOR_GRAY)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(A4[0] / 2, 30, footer_text)
        canvas.restoreState()

    # Build PDF with footer
    try:
        doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    except Exception as e:
        # If build fails, return error info but don't crash the pipeline
        raise RuntimeError(f"Error generating PDF report: {e}") from e

    return str(filepath)
