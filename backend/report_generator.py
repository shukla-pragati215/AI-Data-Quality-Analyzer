"""
PDF Report Generator
Creates a professional data quality analysis report.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
from datetime import datetime


class ReportGenerator:
    """Generates a PDF report from analysis results."""

    # Colors
    PRIMARY = HexColor('#667eea')
    SECONDARY = HexColor('#764ba2')
    DARK = HexColor('#1a1a2e')
    SUCCESS = HexColor('#00c853')
    WARNING = HexColor('#ff9800')
    DANGER = HexColor('#ff1744')
    LIGHT_BG = HexColor('#f5f5f5')
    TEXT_COLOR = HexColor('#333333')
    MUTED = HexColor('#757575')

    def __init__(self, analysis_results: dict, recommendations: list):
        self.results = analysis_results
        self.recommendations = recommendations
        self.summary = analysis_results.get('summary', {})
        self.category_scores = analysis_results.get('category_scores', {})
        self.overall_score = analysis_results.get('overall_score', 0)

    def generate_pdf(self) -> bytes:
        """Generate the PDF report and return as bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=25 * mm,
            bottomMargin=20 * mm,
        )

        styles = self._create_styles()
        story = []

        # Title page
        story.extend(self._build_title_page(styles))
        story.append(PageBreak())

        # Summary section
        story.extend(self._build_summary_section(styles))
        story.append(Spacer(1, 10 * mm))

        # Quality scores
        story.extend(self._build_scores_section(styles))
        story.append(Spacer(1, 10 * mm))

        # Issues section
        story.extend(self._build_issues_section(styles))
        story.append(PageBreak())

        # Column analysis
        story.extend(self._build_column_section(styles))
        story.append(PageBreak())

        # Recommendations
        story.extend(self._build_recommendations_section(styles))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def _create_styles(self):
        """Create custom paragraph styles."""
        styles = getSampleStyleSheet()

        styles.add(ParagraphStyle(
            'ReportTitle',
            parent=styles['Title'],
            fontSize=28,
            textColor=self.PRIMARY,
            spaceAfter=10,
            alignment=TA_CENTER,
        ))

        styles.add(ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=self.MUTED,
            spaceAfter=20,
            alignment=TA_CENTER,
        ))

        styles.add(ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=self.PRIMARY,
            spaceBefore=15,
            spaceAfter=10,
            borderWidth=1,
            borderColor=self.PRIMARY,
            borderPadding=5,
        ))

        styles.add(ParagraphStyle(
            'SubHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=self.DARK,
            spaceBefore=10,
            spaceAfter=5,
        ))

        styles.add(ParagraphStyle(
            'BodyText2',
            parent=styles['Normal'],
            fontSize=10,
            textColor=self.TEXT_COLOR,
            spaceAfter=5,
            leading=14,
        ))

        styles.add(ParagraphStyle(
            'SmallMuted',
            parent=styles['Normal'],
            fontSize=8,
            textColor=self.MUTED,
        ))

        return styles

    def _build_title_page(self, styles):
        """Build the title page."""
        elements = []
        elements.append(Spacer(1, 60 * mm))
        elements.append(Paragraph("Data Quality Analysis Report", styles['ReportTitle']))
        elements.append(Spacer(1, 5 * mm))

        filename = self.summary.get('filename', 'Unknown')
        elements.append(Paragraph(f"Dataset: {filename}", styles['ReportSubtitle']))

        date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        elements.append(Paragraph(f"Generated on {date_str}", styles['ReportSubtitle']))

        elements.append(Spacer(1, 20 * mm))

        score_color = self._score_color(self.overall_score)
        elements.append(Paragraph(
            f'<font size="48" color="{score_color}">{self.overall_score}</font>'
            f'<font size="20" color="{self.MUTED}">/100</font>',
            ParagraphStyle('ScoreDisplay', parent=styles['Normal'], alignment=TA_CENTER, spaceAfter=5)
        ))
        elements.append(Paragraph("Overall Quality Score", styles['ReportSubtitle']))

        elements.append(Spacer(1, 30 * mm))
        elements.append(Paragraph(
            "Generated by AI Data Quality Analyzer",
            styles['SmallMuted']
        ))

        return elements

    def _build_summary_section(self, styles):
        """Build the dataset summary section."""
        elements = []
        elements.append(Paragraph("Dataset Summary", styles['SectionHeader']))

        data = [
            ['Metric', 'Value'],
            ['Filename', self.summary.get('filename', 'N/A')],
            ['Total Rows', f"{self.summary.get('total_rows', 0):,}"],
            ['Total Columns', str(self.summary.get('total_columns', 0))],
            ['Total Cells', f"{self.summary.get('total_cells', 0):,}"],
            ['Missing Cells', f"{self.summary.get('total_missing', 0):,} ({self.summary.get('missing_percentage', 0)}%)"],
            ['Duplicate Rows', f"{self.summary.get('total_duplicates', 0):,} ({self.summary.get('duplicate_percentage', 0)}%)"],
            ['Issues Found', str(self.summary.get('total_issues', 0))],
            ['Memory Usage', f"{self.summary.get('memory_usage_mb', 0)} MB"],
        ]

        table = Table(data, colWidths=[150, 300])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BACKGROUND', (0, 1), (-1, -1), self.LIGHT_BG),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, self.LIGHT_BG]),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ]))
        elements.append(table)

        return elements

    def _build_scores_section(self, styles):
        """Build the quality scores section."""
        elements = []
        elements.append(Paragraph("Quality Scores by Category", styles['SectionHeader']))

        data = [['Category', 'Score', 'Rating']]
        for cat, score in self.category_scores.items():
            rating = self._score_rating(score)
            data.append([cat.title(), f"{score}/100", rating])

        data.append(['Overall', f"{self.overall_score}/100", self._score_rating(self.overall_score)])

        table = Table(data, colWidths=[150, 100, 200])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, self.LIGHT_BG]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ]))
        elements.append(table)

        return elements

    def _build_issues_section(self, styles):
        """Build the issues breakdown section."""
        elements = []
        issues = self.results.get('issues', [])
        elements.append(Paragraph(f"Issues Detected ({len(issues)})", styles['SectionHeader']))

        if not issues:
            elements.append(Paragraph("No issues detected. The dataset is in good shape!", styles['BodyText2']))
            return elements

        severity_counts = {}
        for issue in issues:
            sev = issue['severity']
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        summary_data = [['Severity', 'Count']]
        for sev in ['critical', 'high', 'medium', 'low']:
            if sev in severity_counts:
                summary_data.append([sev.upper(), str(severity_counts[sev])])

        table = Table(summary_data, colWidths=[150, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, self.LIGHT_BG]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 5 * mm))

        # Detailed issues table (top 20)
        issue_data = [['#', 'Column', 'Issue', 'Severity', 'Affected']]
        for i, issue in enumerate(issues[:20], 1):
            issue_data.append([
                str(i),
                issue.get('column', 'N/A')[:20],
                issue.get('description', '')[:60],
                issue.get('severity', '').upper(),
                f"{issue.get('affected_pct', 0)}%",
            ])

        table = Table(issue_data, colWidths=[25, 80, 230, 60, 55])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 0), (4, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, self.LIGHT_BG]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ]))
        elements.append(table)

        if len(issues) > 20:
            elements.append(Paragraph(
                f"... and {len(issues) - 20} more issues",
                styles['SmallMuted']
            ))

        return elements

    def _build_column_section(self, styles):
        """Build the column analysis section."""
        elements = []
        profiles = self.results.get('column_profiles', {})
        elements.append(Paragraph("Column Analysis", styles['SectionHeader']))

        col_data = [['Column', 'Type', 'Missing', 'Unique', 'Issues']]
        for col_name, profile in profiles.items():
            missing_issues = [i for i in self.results.get('issues', []) if i.get('column') == col_name]
            col_data.append([
                col_name[:25],
                profile.get('inferred_type', 'unknown')[:15],
                f"{profile.get('missing_pct', 0)}%",
                f"{profile.get('unique_count', 0)}",
                str(len(missing_issues)),
            ])

        if len(col_data) > 1:
            table = Table(col_data, colWidths=[120, 80, 65, 65, 55])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, self.LIGHT_BG]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
            ]))
            elements.append(table)

        return elements

    def _build_recommendations_section(self, styles):
        """Build the AI recommendations section."""
        elements = []
        elements.append(Paragraph("AI Recommendations", styles['SectionHeader']))

        if not self.recommendations:
            elements.append(Paragraph("No specific recommendations — dataset quality is excellent!", styles['BodyText2']))
            return elements

        for i, rec in enumerate(self.recommendations[:15], 1):
            priority = rec.get('priority', 'low').upper()
            title = rec.get('title', '')
            explanation = rec.get('explanation', '')
            action = rec.get('action', '')

            elements.append(Paragraph(
                f"<b>{i}. [{priority}] {title}</b>",
                styles['SubHeader']
            ))
            elements.append(Paragraph(
                f"<i>Analysis:</i> {explanation}",
                styles['BodyText2']
            ))
            elements.append(Paragraph(
                f"<i>Recommended Action:</i> {action}",
                styles['BodyText2']
            ))
            elements.append(Spacer(1, 3 * mm))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#eeeeee')))
            elements.append(Spacer(1, 3 * mm))

        return elements

    def _score_color(self, score):
        if score >= 80:
            return '#00c853'
        elif score >= 60:
            return '#ff9800'
        else:
            return '#ff1744'

    def _score_rating(self, score):
        if score >= 90:
            return 'Excellent'
        elif score >= 80:
            return 'Good'
        elif score >= 70:
            return 'Fair'
        elif score >= 60:
            return 'Needs Improvement'
        elif score >= 40:
            return 'Poor'
        else:
            return 'Critical'
