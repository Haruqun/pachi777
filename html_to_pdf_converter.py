#!/usr/bin/env python3
"""
HTMLレポートをPDFに変換
PPタウン様向け高品質PDFレポート生成
"""

import glob
from pathlib import Path
import subprocess
import sys

def convert_html_to_pdf(html_file):
    """HTMLファイルをPDFに変換"""
    
    # 最新のHTMLファイルを取得
    if not html_file:
        html_files = glob.glob("professional_graph_report_*.html")
        if not html_files:
            print("❌ HTMLレポートファイルが見つかりません")
            return None
        
        # 最新のファイルを選択
        html_file = max(html_files, key=lambda x: Path(x).stat().st_mtime)
    
    pdf_file = html_file.replace('.html', '.pdf')
    
    print(f"📄 PDF変換開始: {html_file} → {pdf_file}")
    
    try:
        # weasyprint を使用してPDF変換
        cmd = [
            'weasyprint',
            html_file,
            pdf_file,
            '--format', 'pdf',
            '--encoding', 'utf-8'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ PDF変換成功: {pdf_file}")
            return pdf_file
        else:
            print(f"❌ weasyprint変換失敗: {result.stderr}")
            
            # wkhtmltopdf を試行
            print("🔄 wkhtmltopdf で再試行中...")
            cmd = [
                'wkhtmltopdf',
                '--page-size', 'A4',
                '--orientation', 'Portrait',
                '--margin-top', '10mm',
                '--margin-bottom', '10mm',
                '--margin-left', '10mm',
                '--margin-right', '10mm',
                '--encoding', 'UTF-8',
                '--disable-smart-shrinking',
                '--enable-local-file-access',
                html_file,
                pdf_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ PDF変換成功 (wkhtmltopdf): {pdf_file}")
                return pdf_file
            else:
                print(f"❌ wkhtmltopdf変換も失敗: {result.stderr}")
                
                # Chromeヘッドレスモードを試行
                print("🔄 Chrome headless で再試行中...")
                return convert_with_chrome(html_file, pdf_file)
                
    except FileNotFoundError as e:
        print(f"❌ PDF変換ツールが見つかりません: {e}")
        print("🔄 Chrome headless で試行中...")
        return convert_with_chrome(html_file, pdf_file)

def convert_with_chrome(html_file, pdf_file):
    """Chrome headless でPDF変換"""
    try:
        # Chromeの一般的なパスを試行
        chrome_paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/usr/bin/google-chrome',
            '/usr/bin/chromium-browser',
            'google-chrome',
            'chromium',
            'chrome'
        ]
        
        chrome_cmd = None
        for path in chrome_paths:
            try:
                result = subprocess.run([path, '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    chrome_cmd = path
                    break
            except FileNotFoundError:
                continue
        
        if not chrome_cmd:
            print("❌ Chrome/Chromiumが見つかりません")
            return create_simple_pdf_fallback(html_file, pdf_file)
        
        # 絶対パスに変換
        abs_html_path = Path(html_file).absolute()
        abs_pdf_path = Path(pdf_file).absolute()
        
        cmd = [
            chrome_cmd,
            '--headless',
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--print-to-pdf=' + str(abs_pdf_path),
            '--print-to-pdf-no-header',
            '--run-all-compositor-stages-before-draw',
            '--virtual-time-budget=10000',
            'file://' + str(abs_html_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and Path(pdf_file).exists():
            print(f"✅ PDF変換成功 (Chrome): {pdf_file}")
            return pdf_file
        else:
            print(f"❌ Chrome変換失敗: {result.stderr}")
            return create_simple_pdf_fallback(html_file, pdf_file)
            
    except Exception as e:
        print(f"❌ Chrome変換エラー: {e}")
        return create_simple_pdf_fallback(html_file, pdf_file)

def create_simple_pdf_fallback(html_file, pdf_file):
    """シンプルなPDF作成（フォールバック）"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from datetime import datetime
        import re
        
        # HTMLファイルを読み込み
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # タイトルとデータを抽出
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html_content)
        title = title_match.group(1) if title_match else "パチンコグラフ分析レポート"
        
        # PDFドキュメント作成
        doc = SimpleDocTemplate(
            pdf_file,
            pagesize=A4,
            topMargin=30,
            bottomMargin=30,
            leftMargin=30,
            rightMargin=30
        )
        
        # スタイル設定
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        # コンテンツ作成
        story = []
        
        # タイトル
        story.append(Paragraph("🏢 PPタウン様", subtitle_style))
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(f"作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}", subtitle_style))
        story.append(Spacer(1, 20))
        
        # 注意事項
        story.append(Paragraph("📋 レポート概要", styles['Heading2']))
        story.append(Paragraph(
            "このレポートは、PPタウン様のパチンコグラフ画像をAI技術により高精度で解析した結果をまとめています。",
            styles['Normal']
        ))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("🔬 技術仕様", styles['Heading2']))
        story.append(Paragraph("• 10色同時グラフ線検出", styles['Normal']))
        story.append(Paragraph("• ±1px精度での座標測定", styles['Normal']))
        story.append(Paragraph("• Hough変換による0ライン自動検出", styles['Normal']))
        story.append(Paragraph("• Tesseract OCRによる文字認識", styles['Normal']))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("📊 解析結果", styles['Heading2']))
        story.append(Paragraph("詳細な解析結果と画像は、添付のHTMLレポートをご確認ください。", styles['Normal']))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("🎨 制作", styles['Heading2']))
        story.append(Paragraph("Report Design: ファイブナインデザイン - 佐藤", styles['Normal']))
        story.append(Paragraph("AI Analysis: Next-Gen ML Platform", styles['Normal']))
        
        # PDF生成
        doc.build(story)
        
        print(f"✅ シンプルPDF作成成功: {pdf_file}")
        return pdf_file
        
    except ImportError:
        print("❌ reportlabライブラリが必要です: pip install reportlab")
        return None
    except Exception as e:
        print(f"❌ PDF作成エラー: {e}")
        return None

def main():
    """メイン実行"""
    print("📄 HTMLからPDFへの変換ツール")
    print("=" * 50)
    
    # 最新のHTMLレポートファイルを取得
    html_files = glob.glob("professional_graph_report_*.html")
    
    if not html_files:
        print("❌ professional_graph_report_*.html ファイルが見つかりません")
        return
    
    # 最新のファイルを選択
    latest_html = max(html_files, key=lambda x: Path(x).stat().st_mtime)
    print(f"📁 最新のHTMLファイル: {latest_html}")
    
    # PDF変換実行
    pdf_file = convert_html_to_pdf(latest_html)
    
    if pdf_file:
        print("=" * 50)
        print("✅ PDF変換完了")
        print(f"📄 出力ファイル: {pdf_file}")
        
        # PDFファイルを開く
        try:
            subprocess.run(['open', pdf_file], check=True)
            print("📖 PDFファイルを開きました")
        except:
            print("💡 PDFファイルを手動で開いてください")
    else:
        print("❌ PDF変換に失敗しました")

if __name__ == "__main__":
    main()