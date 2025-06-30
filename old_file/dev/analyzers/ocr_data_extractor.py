#!/usr/bin/env python3
"""
元画像からOCRでデータ内容を取得
パチンコ機の統計情報やテキストデータを抽出
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import json
import glob
from pathlib import Path
import re
from datetime import datetime

class OCRDataExtractor:
    def __init__(self):
        # Tesseractの設定（日本語対応）
        self.tesseract_config = '--psm 6 -l jpn+eng'
        self.results = []
        
    def preprocess_image_for_ocr(self, img_path):
        """OCR用の画像前処理"""
        # PIL Imageで読み込み
        pil_img = Image.open(img_path)
        
        # グレースケール変換
        gray_img = pil_img.convert('L')
        
        # コントラスト強化
        enhancer = ImageEnhance.Contrast(gray_img)
        enhanced_img = enhancer.enhance(2.0)
        
        # シャープ化
        sharp_img = enhanced_img.filter(ImageFilter.SHARPEN)
        
        # OpenCV形式に変換
        cv_img = cv2.cvtColor(np.array(sharp_img), cv2.COLOR_GRAY2BGR)
        
        return cv_img, sharp_img
    
    def extract_text_regions(self, img_path):
        """画像から複数の領域のテキストを抽出"""
        cv_img, pil_img = self.preprocess_image_for_ocr(img_path)
        height, width = cv_img.shape[:2]
        
        # 領域定義（画像の相対位置で指定）
        regions = {
            'top_left': (0, 0, width//3, height//4),           # 左上（機種名など）
            'top_center': (width//3, 0, 2*width//3, height//4), # 上中央（店舗情報など）
            'top_right': (2*width//3, 0, width, height//4),     # 右上（日時など）
            'bottom_left': (0, 3*height//4, width//2, height),  # 左下（統計情報）
            'bottom_right': (width//2, 3*height//4, width, height), # 右下（統計情報）
            'center': (width//4, height//4, 3*width//4, 3*height//4), # 中央（グラフ周辺）
        }
        
        extracted_data = {}
        
        for region_name, (x1, y1, x2, y2) in regions.items():
            # 領域を切り出し
            region_img = pil_img.crop((x1, y1, x2, y2))
            
            # OCR実行
            try:
                text = pytesseract.image_to_string(region_img, config=self.tesseract_config)
                # 空白行を除去して整理
                cleaned_text = '\n'.join([line.strip() for line in text.split('\n') if line.strip()])
                extracted_data[region_name] = cleaned_text
            except Exception as e:
                extracted_data[region_name] = f"OCRエラー: {str(e)}"
        
        return extracted_data
    
    def parse_pachinko_data(self, text_data):
        """パチンコ固有のデータを解析"""
        parsed_data = {
            'machine_model': None,      # 機種名
            'store_name': None,         # 店舗名
            'date_time': None,          # 日時
            'total_spins': None,        # 総回転数
            'big_bonus': None,          # 大当たり回数
            'probability': None,        # 大当たり確率
            'payout_rate': None,        # 出玉率
            'play_time': None,          # 遊技時間
            'current_balance': None,    # 現在差玉
            'other_stats': []           # その他の統計
        }
        
        # 全テキストを結合
        all_text = '\n'.join(text_data.values())
        
        # パターンマッチングで数値データを抽出
        patterns = {
            'total_spins': r'(?:総回転|回転数|スピン).*?(\d{1,5})',
            'big_bonus': r'(?:大当たり|BIG|ビッグ).*?(\d{1,3})',
            'probability': r'(?:確率|1/).*?(\d{1,4})',
            'payout_rate': r'(?:出玉率|払出率).*?(\d{1,3}\.?\d*)%?',
            'play_time': r'(?:時間|TIME).*?(\d{1,2}:\d{2})',
            'current_balance': r'(?:差玉|現在).*?([+-]?\d{1,6})',
        }
        
        for key, pattern in patterns.items():
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            if matches:
                parsed_data[key] = matches[0]
        
        # 機種名の推定（カタカナの連続）
        machine_matches = re.findall(r'[ア-ヴー]{3,}', all_text)
        if machine_matches:
            parsed_data['machine_model'] = machine_matches[0]
        
        # 日時の推定
        date_matches = re.findall(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2})', all_text)
        if date_matches:
            parsed_data['date_time'] = date_matches[0]
        
        return parsed_data
    
    def extract_from_image(self, img_path):
        """単一画像からデータを抽出"""
        print(f"OCR処理中: {img_path}")
        
        # テキスト領域抽出
        text_regions = self.extract_text_regions(img_path)
        
        # パチンコデータ解析
        parsed_data = self.parse_pachinko_data(text_regions)
        
        result = {
            'image_path': img_path,
            'file_name': Path(img_path).stem,
            'text_regions': text_regions,
            'parsed_data': parsed_data,
            'extraction_time': datetime.now().isoformat()
        }
        
        return result
    
    def process_multiple_images(self, image_pattern):
        """複数画像の一括OCR処理"""
        image_files = glob.glob(image_pattern)
        
        print(f"OCR対象: {len(image_files)}個の画像")
        
        for img_file in image_files:
            try:
                result = self.extract_from_image(img_file)
                self.results.append(result)
                
                # 抽出された主要データを表示
                parsed = result['parsed_data']
                print(f"  -> {result['file_name']}")
                if parsed['machine_model']:
                    print(f"     機種: {parsed['machine_model']}")
                if parsed['total_spins']:
                    print(f"     総回転数: {parsed['total_spins']}")
                if parsed['current_balance']:
                    print(f"     差玉: {parsed['current_balance']}")
                    
            except Exception as e:
                print(f"  -> エラー: {img_file} - {str(e)}")
        
        return self.results
    
    def save_results(self, output_file="ocr_extracted_data.json"):
        """結果をJSONファイルに保存"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"OCR結果を保存: {output_file}")
        return output_file
    
    def generate_ocr_report(self, output_file="ocr_analysis_report.html"):
        """OCR結果のHTMLレポートを生成"""
        
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCRデータ抽出レポート</title>
    <style>
        body {{
            font-family: 'Hiragino Sans', 'Meiryo', sans-serif;
            background: linear-gradient(135deg, #2c3e50, #3498db);
            color: #fff;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            background: linear-gradient(45deg, #e74c3c, #f39c12);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .summary-card {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }}
        
        .ocr-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
        }}
        
        .ocr-item {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .ocr-header {{
            background: linear-gradient(45deg, #9b59b6, #8e44ad);
            padding: 15px;
            font-weight: bold;
            font-size: 1.1em;
        }}
        
        .ocr-content {{
            padding: 20px;
        }}
        
        .original-image {{
            width: 100%;
            border-radius: 10px;
            margin-bottom: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }}
        
        .parsed-data {{
            background: rgba(46, 204, 113, 0.2);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
            border-left: 4px solid #2ecc71;
        }}
        
        .text-regions {{
            background: rgba(52, 152, 219, 0.2);
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #3498db;
        }}
        
        .region-text {{
            background: rgba(255,255,255,0.1);
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            font-family: monospace;
            font-size: 0.9em;
            white-space: pre-wrap;
        }}
        
        .data-item {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .data-label {{
            font-weight: bold;
            color: #2ecc71;
        }}
        
        .data-value {{
            color: #ecf0f1;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>OCRデータ抽出レポート</h1>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>処理画像数</h3>
                <div style="font-size: 2em; font-weight: bold;">{len(self.results)}</div>
            </div>
            <div class="summary-card">
                <h3>機種名検出数</h3>
                <div style="font-size: 2em; font-weight: bold;">{len([r for r in self.results if r['parsed_data']['machine_model']])}</div>
            </div>
            <div class="summary-card">
                <h3>統計データ検出数</h3>
                <div style="font-size: 2em; font-weight: bold;">{len([r for r in self.results if r['parsed_data']['total_spins']])}</div>
            </div>
        </div>
        
        <div class="ocr-grid">
"""
        
        # 各画像のOCR結果
        for i, result in enumerate(self.results):
            file_name = result['file_name']
            parsed = result['parsed_data']
            text_regions = result['text_regions']
            
            html_content += f"""
            <div class="ocr-item">
                <div class="ocr-header">
                    #{i+1}: {file_name}
                </div>
                <div class="ocr-content">
                    <img src="{result['image_path']}" alt="元画像" class="original-image">
                    
                    <div class="parsed-data">
                        <h4>抽出データ</h4>
"""
            
            # パースされたデータを表示
            data_items = [
                ('機種名', parsed['machine_model']),
                ('総回転数', parsed['total_spins']),
                ('大当たり回数', parsed['big_bonus']),
                ('確率', parsed['probability']),
                ('出玉率', parsed['payout_rate']),
                ('遊技時間', parsed['play_time']),
                ('現在差玉', parsed['current_balance']),
                ('日時', parsed['date_time'])
            ]
            
            for label, value in data_items:
                if value:
                    html_content += f"""
                        <div class="data-item">
                            <span class="data-label">{label}:</span>
                            <span class="data-value">{value}</span>
                        </div>"""
            
            html_content += """
                    </div>
                    
                    <div class="text-regions">
                        <h4>領域別テキスト</h4>
"""
            
            # 領域別テキストを表示
            for region_name, text in text_regions.items():
                if text and len(text.strip()) > 0:
                    html_content += f"""
                        <h5>{region_name}:</h5>
                        <div class="region-text">{text}</div>"""
            
            html_content += """
                    </div>
                </div>
            </div>
"""
        
        html_content += """
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"OCRレポートを生成: {output_file}")
        return output_file

if __name__ == "__main__":
    extractor = OCRDataExtractor()
    
    # 元画像からOCRデータ抽出
    image_pattern = "graphs/original/*.jpg"
    results = extractor.process_multiple_images(image_pattern)
    
    # 結果を保存
    json_file = extractor.save_results()
    html_file = extractor.generate_ocr_report()
    
    print(f"\n=== OCR処理完了 ===")
    print(f"処理画像数: {len(results)}")
    print(f"JSONファイル: {json_file}")
    print(f"HTMLレポート: {html_file}")