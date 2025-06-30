#!/usr/bin/env python3
"""
0ライン基準最大値抽出ツール
0ラインから一定距離の場所にある「最大値：XXXX」テキストを抽出
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

class ZeroLineBasedMaxExtractor:
    def __init__(self):
        self.results = []
    
    def detect_zero_line(self, img):
        """ゼロライン検出（既存の手法）"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        search_top = height // 3
        search_bottom = height * 2 // 3
        search_region = gray[search_top:search_bottom, :]
        
        # 水平線検出
        edges = cv2.Canny(search_region, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=int(width*0.3))
        
        zero_candidates = []
        
        if lines is not None:
            for rho, theta in lines[0]:
                if abs(theta) < 0.1 or abs(theta - np.pi) < 0.1:
                    y = int(rho / np.sin(theta)) if abs(np.sin(theta)) > 0.1 else search_top
                    if 0 < y < search_region.shape[0]:
                        zero_candidates.append(search_top + y)
        
        # 濃い水平線検出
        for y in range(search_top, search_bottom):
            row = gray[y, :]
            dark_pixels = np.sum(row < 100)
            if dark_pixels > width * 0.7:
                zero_candidates.append(y)
        
        if zero_candidates:
            return int(np.median(zero_candidates))
        else:
            return 250  # デフォルト値
    
    def extract_max_value_from_zero_line(self, img_path):
        """0ラインからの相対位置で最大値テキストを抽出"""
        img = cv2.imread(img_path)
        if img is None:
            return None, "画像読み込み失敗"
        
        height, width = img.shape[:2]
        zero_y = self.detect_zero_line(img)
        
        print(f"    0ライン検出位置: Y={zero_y}")
        
        # 0ラインから下方向に最大値テキストを探索
        # 通常、0ラインの下60-120px程度の位置にある
        text_search_offsets = [60, 80, 100, 120, 140]  # 0ラインからの下方向オフセット
        
        max_value = None
        best_confidence = 0
        best_text = ""
        
        for offset in text_search_offsets:
            text_y = zero_y + offset
            
            # テキスト領域を設定（0ラインの下の特定位置）
            text_region_height = 40  # テキスト領域の高さ
            
            if text_y + text_region_height > height:
                continue
            
            # 最大値テキストがありそうな右側を重点的に
            text_left = int(width * 0.4)  # 右寄り
            text_region = img[text_y:text_y + text_region_height, text_left:]
            
            # OCR前処理
            text_img_pil = self.preprocess_for_ocr(text_region)
            
            try:
                # 数字と最大値文字に特化したOCR
                ocr_config = '--oem 3 --psm 8 -l jpn+eng -c tessedit_char_whitelist=0123456789：:最大値'
                text = pytesseract.image_to_string(text_img_pil, config=ocr_config)
                
                print(f"      オフセット{offset}px: '{text.strip()}'")
                
                # 最大値パターンマッチング
                patterns = [
                    r'最大値[：:\s]*([0-9,]+)',
                    r'最大[：:\s]*([0-9,]+)',
                    r'([0-9,]+)',  # 数字のみ
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, text)
                    if matches:
                        try:
                            value = int(matches[0].replace(',', ''))
                            # 妥当な範囲の値かチェック（0-100000程度）
                            if 0 <= value <= 100000:
                                confidence = len(text.strip())  # テキストの長さを信頼度とする
                                if confidence > best_confidence:
                                    max_value = value
                                    best_confidence = confidence
                                    best_text = text
                                    print(f"        ✅ 候補値: {value:,} (信頼度: {confidence})")
                                break
                        except ValueError:
                            continue
                            
            except Exception as e:
                print(f"        OCRエラー: {str(e)}")
                continue
        
        return max_value, best_text
    
    def preprocess_for_ocr(self, img):
        """OCR用画像前処理"""
        if isinstance(img, np.ndarray):
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        else:
            img_pil = img
        
        # 強いコントラスト強化
        enhancer = ImageEnhance.Contrast(img_pil)
        img_pil = enhancer.enhance(3.0)
        
        # 大幅リサイズ
        width, height = img_pil.size
        img_pil = img_pil.resize((width * 4, height * 4), Image.LANCZOS)
        
        return img_pil
    
    def process_all_images(self):
        """全画像を処理"""
        original_files = glob.glob("graphs/original/*.jpg")
        
        print(f"🎯 0ライン基準最大値抽出開始: {len(original_files)}枚")
        print("=" * 60)
        
        for img_file in original_files:
            file_name = Path(img_file).stem
            print(f"処理中: {file_name}")
            
            max_value, ocr_text = self.extract_max_value_from_zero_line(img_file)
            
            result = {
                'file_name': file_name,
                'max_value': max_value,
                'ocr_text': ocr_text,
                'image_path': img_file
            }
            
            self.results.append(result)
            
            if max_value is not None:
                print(f"  ✅ 最大値: {max_value:,}")
            else:
                print(f"  ❌ 最大値検出失敗")
            print()
        
        return self.results
    
    def save_results(self):
        """結果保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"zero_line_max_values_{timestamp}.json"
        
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
        
        print(f"📄 結果保存: {output_file}")
        return output_file
    
    def create_html_report(self):
        """HTMLレポート生成"""
        successful_results = [r for r in self.results if r['max_value'] is not None]
        
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 0ライン基準最大値抽出レポート</title>
    <style>
        body {{
            font-family: 'Hiragino Sans', 'Meiryo', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
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
            font-size: 2em;
            font-weight: bold;
            color: #4ecdc4;
            margin: 15px 0;
        }}
        .method-badge {{
            background: rgba(76, 175, 80, 0.8);
            color: white;
            padding: 4px 8px;
            border-radius: 10px;
            font-size: 0.8em;
            margin-left: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 0ライン基準最大値抽出レポート</h1>
            <p>0ラインからの相対位置による高精度テキスト抽出</p>
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
        
        <h2>📋 画像別抽出結果</h2>
        <div class="results-grid">
"""
        
        for result in self.results:
            file_name = result['file_name']
            max_value = result['max_value']
            ocr_text = result['ocr_text']
            
            card_class = "success" if max_value is not None else "failure"
            
            html_content += f"""
            <div class="result-card {card_class}">
                <h3>📷 {file_name}</h3>
"""
            
            if max_value is not None:
                html_content += f"""
                <div class="max-value">
                    {max_value:,}
                    <span class="method-badge">0ライン基準</span>
                </div>
                <div>検出テキスト: "{ocr_text.strip()}"</div>
"""
            else:
                html_content += """
                <div style="color: #ff6b6b; font-weight: bold; font-size: 1.2em;">
                    ❌ 最大値検出失敗
                </div>
"""
            
            html_content += "</div>"
        
        html_content += """
        </div>
    </div>
</body>
</html>"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"zero_line_max_values_{timestamp}.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 HTMLレポート保存: {output_file}")
        return output_file

if __name__ == "__main__":
    extractor = ZeroLineBasedMaxExtractor()
    
    # 全画像処理
    results = extractor.process_all_images()
    
    # 結果サマリー
    successful = [r for r in results if r['max_value'] is not None]
    print("=" * 60)
    print(f"✅ 0ライン基準抽出完了")
    print(f"📊 総画像数: {len(results)}")
    print(f"🎯 成功数: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
    
    if successful:
        max_values = [r['max_value'] for r in successful]
        print(f"📈 最高値: {max(max_values):,}")
        print(f"📊 平均値: {int(np.mean(max_values)):,}")
    
    # 結果保存
    extractor.save_results()
    extractor.create_html_report()
    
    print("=" * 60)