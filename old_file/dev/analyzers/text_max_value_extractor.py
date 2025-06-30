#!/usr/bin/env python3
"""
テキスト最大値抽出ツール - OCR専用
画面下部に表示されている「最大値：XXXX」のテキストをOCRで抽出
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import glob
from pathlib import Path
import json
from datetime import datetime
import re

class TextMaxValueExtractor:
    def __init__(self):
        self.results = []
    
    def preprocess_for_ocr(self, img):
        """OCR用の画像前処理"""
        # PILに変換
        if isinstance(img, np.ndarray):
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        else:
            img_pil = img
        
        # コントラスト強化
        enhancer = ImageEnhance.Contrast(img_pil)
        img_pil = enhancer.enhance(2.0)
        
        # シャープ化
        img_pil = img_pil.filter(ImageFilter.SHARPEN)
        
        # リサイズ（OCR精度向上）
        width, height = img_pil.size
        img_pil = img_pil.resize((width * 2, height * 2), Image.LANCZOS)
        
        return img_pil
    
    def extract_max_value_from_text(self, img_path):
        """画像からテキストの最大値を抽出"""
        img = cv2.imread(img_path)
        if img is None:
            return None, None, "画像読み込み失敗"
        
        height, width = img.shape[:2]
        
        # グラフ下部のテキスト領域を特定（下部30%程度）
        text_region_top = int(height * 0.7)
        text_region = img[text_region_top:, :]
        
        # OCR用前処理
        text_img_pil = self.preprocess_for_ocr(text_region)
        
        try:
            # 日本語+英語でOCR実行
            ocr_config = '--oem 3 --psm 6 -l jpn+eng'
            text = pytesseract.image_to_string(text_img_pil, config=ocr_config)
            
            # 最大値パターンを検索
            max_value_patterns = [
                r'最大値[：:\s]*([0-9,]+)',
                r'最大[：:\s]*([0-9,]+)',
                r'MAX[：:\s]*([0-9,]+)',
                r'max[：:\s]*([0-9,]+)'
            ]
            
            max_value = None
            matched_pattern = None
            
            for pattern in max_value_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # カンマを除去して数値に変換
                    max_value = int(matches[0].replace(',', ''))
                    matched_pattern = pattern
                    break
            
            # 追加の統計情報も抽出
            stats = {}
            
            # スタート回数
            start_patterns = [
                r'スタート[：:\s]*([0-9,]+)',
                r'累計スタート[：:\s]*([0-9,]+)'
            ]
            for pattern in start_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    stats['start_count'] = int(matches[0].replace(',', ''))
                    break
            
            # 大当り回数
            jackpot_patterns = [
                r'大当り回数[：:\s]*([0-9,]+)',
                r'大当り[：:\s]*([0-9,]+)回'
            ]
            for pattern in jackpot_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    stats['jackpot_count'] = int(matches[0].replace(',', ''))
                    break
            
            # 確率
            prob_patterns = [
                r'大当り確率[：:\s]*1/([0-9,]+)',
                r'確率[：:\s]*1/([0-9,]+)'
            ]
            for pattern in prob_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    stats['probability'] = f"1/{matches[0]}"
                    break
            
            # 最高出玉
            max_payout_patterns = [
                r'最高出玉[：:\s]*([0-9,]+)',
                r'最高[：:\s]*([0-9,]+)'
            ]
            for pattern in max_payout_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    stats['max_payout'] = int(matches[0].replace(',', ''))
                    break
            
            return max_value, stats, text
            
        except Exception as e:
            return None, None, f"OCR処理エラー: {str(e)}"
    
    def process_all_images(self):
        """全画像のテキスト最大値を抽出"""
        original_files = glob.glob("graphs/original/*.jpg")
        
        print(f"🔍 テキスト最大値抽出開始: {len(original_files)}枚の画像")
        print("=" * 60)
        
        for img_file in original_files:
            file_name = Path(img_file).stem
            print(f"処理中: {file_name}")
            
            max_value, stats, raw_text = self.extract_max_value_from_text(img_file)
            
            result = {
                'file_name': file_name,
                'max_value': max_value,
                'statistics': stats or {},
                'raw_ocr_text': raw_text,
                'image_path': img_file
            }
            
            self.results.append(result)
            
            if max_value is not None:
                print(f"  ✅ 最大値: {max_value:,}")
                if stats:
                    for key, value in stats.items():
                        print(f"     {key}: {value}")
            else:
                print(f"  ❌ 最大値検出失敗")
                print(f"     OCRテキスト: {raw_text[:100]}...")
        
        return self.results
    
    def save_results(self):
        """結果をJSON形式で保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"text_max_values_{timestamp}.json"
        
        successful = [r for r in self.results if r['max_value'] is not None]
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_images': len(self.results),
            'successful_extractions': len(successful),
            'success_rate': len(successful) / len(self.results) * 100,
            'results': self.results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 結果保存: {output_file}")
        return output_file
    
    def create_html_report(self):
        """HTMLレポート生成"""
        successful_results = [r for r in self.results if r['max_value'] is not None]
        
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📋 テキスト最大値抽出レポート</title>
    <style>
        body {{
            font-family: 'Hiragino Sans', 'Meiryo', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }}
        .results-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
        }}
        .result-card {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
        }}
        .success {{
            border-left: 5px solid #4ecdc4;
        }}
        .failure {{
            border-left: 5px solid #ff6b6b;
        }}
        .max-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #4ecdc4;
            margin: 10px 0;
        }}
        .stats-detail {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.2);
        }}
        .stats-detail div {{
            margin: 5px 0;
        }}
        .ocr-text {{
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 8px;
            font-size: 0.8em;
            margin-top: 10px;
            max-height: 100px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 パチンコ画面テキスト最大値抽出レポート</h1>
            <p>OCRによる画面下部テキスト解析結果</p>
            <p>作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>📊 総画像数</h3>
                <div style="font-size: 2em;">{len(self.results)}</div>
            </div>
            <div class="stat-card">
                <h3>✅ 抽出成功</h3>
                <div style="font-size: 2em;">{len(successful_results)}</div>
            </div>
            <div class="stat-card">
                <h3>🎯 成功率</h3>
                <div style="font-size: 2em;">{len(successful_results)/len(self.results)*100:.1f}%</div>
            </div>
            <div class="stat-card">
                <h3>🏆 最高値</h3>
                <div style="font-size: 2em;">{max([r['max_value'] for r in successful_results], default=0):,}</div>
            </div>
        </div>
        
        <h2>📋 画像別テキスト抽出結果</h2>
        <div class="results-grid">
"""
        
        for result in self.results:
            file_name = result['file_name']
            max_value = result['max_value']
            stats = result['statistics']
            ocr_text = result['raw_ocr_text']
            
            card_class = "success" if max_value is not None else "failure"
            
            html_content += f"""
            <div class="result-card {card_class}">
                <h3>📷 {file_name}</h3>
"""
            
            if max_value is not None:
                html_content += f"""
                <div class="max-value">最大値: {max_value:,}</div>
                <div class="stats-detail">
                    <h4>📈 抽出された統計情報:</h4>
"""
                if stats:
                    for key, value in stats.items():
                        key_name = {
                            'start_count': 'スタート回数',
                            'jackpot_count': '大当り回数', 
                            'probability': '大当り確率',
                            'max_payout': '最高出玉'
                        }.get(key, key)
                        html_content += f"<div>• {key_name}: {value}</div>"
                else:
                    html_content += "<div>その他の統計情報は検出されませんでした</div>"
                
                html_content += "</div>"
            else:
                html_content += """
                <div style="color: #ff6b6b; font-weight: bold;">❌ 最大値の検出に失敗しました</div>
"""
            
            if ocr_text:
                html_content += f"""
                <div class="ocr-text">
                    <strong>OCR生テキスト:</strong><br>
                    {ocr_text[:200]}{'...' if len(ocr_text) > 200 else ''}
                </div>
"""
            
            html_content += "</div>"
        
        html_content += """
        </div>
    </div>
</body>
</html>"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"text_max_values_{timestamp}.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 HTMLレポート保存: {output_file}")
        return output_file

if __name__ == "__main__":
    extractor = TextMaxValueExtractor()
    
    # 全画像のテキスト最大値を抽出
    results = extractor.process_all_images()
    
    # 結果サマリー
    successful = [r for r in results if r['max_value'] is not None]
    print("\n" + "=" * 60)
    print(f"✅ OCRテキスト抽出完了")
    print(f"📊 総画像数: {len(results)}")
    print(f"🎯 成功数: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
    
    if successful:
        max_values = [r['max_value'] for r in successful]
        print(f"📈 最高値: {max(max_values):,}")
        print(f"📊 平均値: {int(np.mean(max_values)):,}")
    
    # 結果を保存
    extractor.save_results()
    extractor.create_html_report()
    
    print("=" * 60)