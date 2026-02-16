# pdf_generator.py - 就業規則PDF出力モジュール
"""
就業規則の構造化JSONデータからプロフェッショナルなPDFを生成する。
既存のFlaskアプリ（app_full.py）に組み込んで使用。

使い方:
    from pdf_generator import add_pdf_routes
    add_pdf_routes(app, db)
    
    これで以下のルートが追加される:
    - /regulation/{id}/pdf          → PDFダウンロード（最新版）
    - /regulation/{id}/pdf/version/2 → PDFダウンロード（指定バージョン）
    - /regulation/{id}/pdf/preview   → ブラウザ内プレビュー
"""

import io
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether, Frame, PageTemplate
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# CIDフォント登録（日本語対応）
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))      # 明朝体（本文）
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))   # ゴシック体（見出し）

# フォント名の定数
FONT_MINCHO = 'HeiseiMin-W3'
FONT_GOTHIC = 'HeiseiKakuGo-W5'


class RegulationPDFGenerator:
    """就業規則PDF生成クラス"""

    def __init__(self):
        self._setup_styles()

    def _setup_styles(self):
        """スタイル定義"""
        # タイトル（就業規則）
        self.style_title = ParagraphStyle(
            'Title',
            fontName=FONT_GOTHIC,
            fontSize=18,
            leading=28,
            alignment=TA_CENTER,
            spaceAfter=6 * mm,
        )

        # 会社名
        self.style_company = ParagraphStyle(
            'Company',
            fontName=FONT_GOTHIC,
            fontSize=12,
            leading=18,
            alignment=TA_CENTER,
            spaceAfter=10 * mm,
        )

        # 章タイトル
        self.style_chapter = ParagraphStyle(
            'Chapter',
            fontName=FONT_GOTHIC,
            fontSize=13,
            leading=22,
            alignment=TA_CENTER,
            spaceBefore=12 * mm,
            spaceAfter=6 * mm,
        )

        # 条タイトル
        self.style_article_title = ParagraphStyle(
            'ArticleTitle',
            fontName=FONT_GOTHIC,
            fontSize=10.5,
            leading=18,
            alignment=TA_LEFT,
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
            leftIndent=0,
        )

        # 条文本文
        self.style_body = ParagraphStyle(
            'Body',
            fontName=FONT_MINCHO,
            fontSize=10.5,
            leading=18,
            alignment=TA_JUSTIFY,
            leftIndent=5 * mm,
            rightIndent=0,
            spaceAfter=1 * mm,
        )

        # 項（号）
        self.style_item = ParagraphStyle(
            'Item',
            fontName=FONT_MINCHO,
            fontSize=10.5,
            leading=18,
            alignment=TA_LEFT,
            leftIndent=10 * mm,
            spaceAfter=0.5 * mm,
        )

        # 附則タイトル
        self.style_appendix = ParagraphStyle(
            'Appendix',
            fontName=FONT_GOTHIC,
            fontSize=11,
            leading=18,
            alignment=TA_CENTER,
            spaceBefore=10 * mm,
            spaceAfter=4 * mm,
        )

        # 附則の各行
        self.style_appendix_body = ParagraphStyle(
            'AppendixBody',
            fontName=FONT_MINCHO,
            fontSize=10.5,
            leading=18,
            alignment=TA_LEFT,
            leftIndent=5 * mm,
            spaceAfter=1 * mm,
        )

        # フッター（ページ番号）
        self.style_footer = ParagraphStyle(
            'Footer',
            fontName=FONT_MINCHO,
            fontSize=9,
            alignment=TA_CENTER,
        )

        # バージョン情報（右上の小さい文字）
        self.style_version_info = ParagraphStyle(
            'VersionInfo',
            fontName=FONT_MINCHO,
            fontSize=8,
            leading=12,
            alignment=TA_RIGHT,
            textColor=colors.Color(0.5, 0.5, 0.5),
        )

    def generate(
        self,
        regulation_data,
        company_name="○○株式会社",
        regulation_name="就業規則",
        version=None,
        appendix_history=None,
        include_version_info=True,
        include_toc=False,
    ) -> bytes:
        """
        就業規則PDFを生成してbytesで返す

        Args:
            regulation_data: 構造化JSON（chaptersのリスト or dict）
            company_name: 会社名
            regulation_name: 規程名（就業規則、賃金規程 等）
            version: バージョン番号（None=表示しない）
            appendix_history: 附則の施行履歴リスト（例:
                ["本規則は、平成２５年１月１日から施行する。",
                 "本規則は、令和３年４月１日に改定し、令和３年４月１日より施行する。"]
            ）
            include_version_info: バージョン情報をフッターに含むか
            include_toc: 目次を含むか

        Returns:
            PDF のバイトデータ
        """
        buffer = io.BytesIO()

        # ページ設定
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=25 * mm,
            bottomMargin=25 * mm,
            leftMargin=25 * mm,
            rightMargin=20 * mm,
        )

        # メタ情報をクロージャで保持
        meta = {
            "company_name": company_name,
            "regulation_name": regulation_name,
            "version": version,
            "include_version_info": include_version_info,
        }

        # ヘッダー・フッター描画用コールバック
        def on_page(canvas_obj, doc_obj):
            self._draw_header_footer(canvas_obj, doc_obj, meta)

        # ストーリー（コンテンツ）組み立て
        story = []

        # --- 表紙的なヘッダー ---
        story.append(Spacer(1, 15 * mm))
        story.append(Paragraph(regulation_name, self.style_title))
        story.append(Paragraph(company_name, self.style_company))
        story.append(Spacer(1, 5 * mm))

        # --- 章の構造を解析 ---
        chapters = self._extract_chapters(regulation_data)

        if not chapters:
            story.append(Paragraph("（規程データがありません）", self.style_body))

        # --- 目次（オプション） ---
        if include_toc and chapters:
            story.extend(self._build_toc(chapters))
            story.append(PageBreak())

        # --- 本文 ---
        for chapter in chapters:
            story.extend(self._build_chapter(chapter))

        # --- 附則（施行履歴） ---
        # まず regulation_data 内の附則を確認
        appendix_from_data = self._extract_appendix(regulation_data)
        # 引数で渡された附則履歴を優先
        appendix_lines = appendix_history or appendix_from_data

        if appendix_lines:
            story.append(Spacer(1, 8 * mm))
            story.append(Paragraph("附　則", self.style_appendix))
            for line in appendix_lines:
                story.append(Paragraph(self._escape(line), self.style_appendix_body))

        # PDF生成
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

        buffer.seek(0)
        return buffer.read()

    def generate_to_file(self, filepath, **kwargs):
        """ファイルに直接出力"""
        pdf_bytes = self.generate(**kwargs)
        with open(filepath, 'wb') as f:
            f.write(pdf_bytes)
        return filepath

    def _draw_header_footer(self, canvas_obj, doc_obj, meta):
        """各ページのヘッダー・フッター描画"""
        canvas_obj.saveState()
        width, height = A4

        # フッター: ページ番号
        page_num = canvas_obj.getPageNumber()
        canvas_obj.setFont(FONT_MINCHO, 9)
        canvas_obj.drawCentredString(width / 2, 15 * mm, f"- {page_num} -")

        # ヘッダー右上: バージョン情報（2ページ目以降）
        if meta["include_version_info"] and page_num > 1:
            canvas_obj.setFont(FONT_MINCHO, 8)
            canvas_obj.setFillColor(colors.Color(0.6, 0.6, 0.6))
            info_text = meta["regulation_name"]
            if meta["version"]:
                info_text += f"（v{meta['version']}）"
            canvas_obj.drawRightString(width - 20 * mm, height - 15 * mm, info_text)

        canvas_obj.restoreState()

    def _extract_chapters(self, regulation_data):
        """regulation_dataからchaptersリストを抽出"""
        if isinstance(regulation_data, list):
            return regulation_data
        elif isinstance(regulation_data, dict):
            if "chapters" in regulation_data:
                return regulation_data["chapters"]
            elif "structure" in regulation_data:
                struct = regulation_data["structure"]
                if isinstance(struct, list):
                    return struct
                elif isinstance(struct, dict) and "chapters" in struct:
                    return struct["chapters"]
        return []

    def _extract_appendix(self, regulation_data):
        """附則を抽出"""
        if isinstance(regulation_data, dict):
            appendix = regulation_data.get("appendix", [])
            if appendix:
                return appendix if isinstance(appendix, list) else [appendix]
        return []

    def _build_toc(self, chapters):
        """目次を生成"""
        elements = []
        elements.append(Paragraph("目　次", self.style_chapter))
        elements.append(Spacer(1, 5 * mm))

        toc_style = ParagraphStyle(
            'TOC',
            fontName=FONT_MINCHO,
            fontSize=10.5,
            leading=20,
            leftIndent=10 * mm,
        )

        toc_article_style = ParagraphStyle(
            'TOCArticle',
            fontName=FONT_MINCHO,
            fontSize=9.5,
            leading=16,
            leftIndent=20 * mm,
            textColor=colors.Color(0.4, 0.4, 0.4),
        )

        for chapter in chapters:
            if not isinstance(chapter, dict):
                continue
            ch_num = chapter.get('number', '')
            ch_title = chapter.get('title', '')
            elements.append(Paragraph(
                f"{self._escape(ch_num)}　{self._escape(ch_title)}",
                toc_style
            ))

            articles = chapter.get('articles', [])
            for article in articles:
                if not isinstance(article, dict):
                    continue
                art_num = article.get('number', '')
                art_title = article.get('title', '')
                if art_title:
                    elements.append(Paragraph(
                        f"{self._escape(art_num)}（{self._escape(art_title)}）",
                        toc_article_style
                    ))

        return elements

    def _build_chapter(self, chapter):
        """章のコンテンツを生成"""
        elements = []

        if not isinstance(chapter, dict):
            return elements

        ch_number = chapter.get('number', '')
        ch_title = chapter.get('title', '')
        if ch_number or ch_title:
            chapter_text = f"{self._escape(ch_number)}　{self._escape(ch_title)}"
            elements.append(Paragraph(chapter_text, self.style_chapter))

        articles = chapter.get('articles', [])
        for article in articles:
            elements.extend(self._build_article(article))

        return elements

    def _build_article(self, article):
        """条のコンテンツを生成"""
        elements = []

        if not isinstance(article, dict):
            return elements

        art_number = article.get('number', '')
        art_title = article.get('title', '')

        if art_title:
            title_text = f"{self._escape(art_number)}（{self._escape(art_title)}）"
        else:
            title_text = self._escape(art_number)

        elements.append(Paragraph(title_text, self.style_article_title))

        content = article.get('content', [])
        if isinstance(content, str):
            content = [content]

        for para in content:
            if isinstance(para, str) and para.strip():
                elements.append(Paragraph(self._escape(para), self.style_body))

        items = article.get('items', [])
        for item in items:
            if isinstance(item, dict):
                item_num = item.get('number', '')
                item_text = item.get('text', '')
                if item_text:
                    formatted = f"{self._escape(str(item_num))}　{self._escape(item_text)}"
                    elements.append(Paragraph(formatted, self.style_item))
            elif isinstance(item, str) and item.strip():
                elements.append(Paragraph(self._escape(item), self.style_item))

        return elements

    def _escape(self, text):
        """ReportLab用にXMLエスケープ"""
        if not text:
            return ""
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text


# ---- Flask ルート用ヘルパー ----

def add_pdf_routes(app, db):
    """
    FlaskアプリにPDF出力ルートを追加する

    使い方（app_full.py に追加）:
        from pdf_generator import add_pdf_routes
        add_pdf_routes(app, db)
    """
    from flask import send_file, abort

    generator = RegulationPDFGenerator()

    @app.route('/regulation/<regulation_id>/pdf')
    @app.route('/regulation/<regulation_id>/pdf/version/<int:version_number>')
    def download_regulation_pdf(regulation_id, version_number=None):
        """就業規則をPDFでダウンロード"""

        regulation = db.get_regulation(regulation_id)
        if not regulation:
            abort(404, "規程が見つかりません")

        company = db.get_company(regulation.get('company_id', ''))
        company_name = company.get('name', '○○会社') if company else '○○会社'

        if version_number:
            content = db.get_regulation_content(regulation_id, version=version_number)
            version = version_number
        else:
            content = db.get_regulation_content(regulation_id)
            version = regulation.get('current_version', 1)

        if not content:
            abort(404, "規程データが見つかりません")

        regulation_data = content.get('content_json') or content.get('structure', [])

        pdf_bytes = generator.generate(
            regulation_data=regulation_data,
            company_name=company_name,
            regulation_name=regulation.get('name', '就業規則'),
            version=version,
            appendix_history=regulation.get('appendix_history'),
            include_toc=True,
        )

        filename = f"{company_name}_{regulation.get('name', '就業規則')}_v{version}.pdf"

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename,
        )

    @app.route('/regulation/<regulation_id>/pdf/preview')
    def preview_regulation_pdf(regulation_id):
        """ブラウザでPDFプレビュー（ダウンロードではなく表示）"""

        regulation = db.get_regulation(regulation_id)
        if not regulation:
            abort(404)

        company = db.get_company(regulation.get('company_id', ''))
        company_name = company.get('name', '○○会社') if company else '○○会社'

        content = db.get_regulation_content(regulation_id)
        if not content:
            abort(404)

        regulation_data = content.get('content_json') or content.get('structure', [])

        pdf_bytes = generator.generate(
            regulation_data=regulation_data,
            company_name=company_name,
            regulation_name=regulation.get('name', '就業規則'),
            version=regulation.get('current_version', 1),
            appendix_history=regulation.get('appendix_history'),
        )

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=False,
        )
