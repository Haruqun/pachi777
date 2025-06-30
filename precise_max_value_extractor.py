#!/usr/bin/env python3
"""
精密最大値抽出ツール
0ラインから正確な距離で「最大値：XXXX」パターンのみを抽出
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

class PreciseMaxValueExtractor:
    def __init__(self):
        self.results = []
    
    def detect_zero_line(self, img):
        """ゼロライン検出"""
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
    
    def extract_precise_max_value(self, img_path):
        """最大値を正確に抽出"""
        img = cv2.imread(img_path)
        if img is None:
            return None, None, "画像読み込み失敗"
        
        height, width = img.shape[:2]
        zero_y = self.detect_zero_line(img)
        
        print(f"    0ライン検出位置: Y={zero_y}")
        
        # 最大値テキストの正確な位置（0ラインから30-70px下）
        max_value_offsets = [30, 40, 45, 50, 60, 70]
        region_height = 25  # テキスト領域の高さ
        
        best_result = None
        best_confidence = 0
        
        for offset in max_value_offsets:
            text_y = zero_y + offset
            
            if text_y + region_height > height:
                continue
            
            # 右側中央付近（最大値テキストの位置）
            left_x = int(width * 0.3)
            right_x = int(width * 0.8)
            
            text_region = img[text_y:text_y + region_height, left_x:right_x]
            
            # より大きな領域で処理（広い範囲）
            extended_region = img[text_y-10:text_y + region_height+10, int(width * 0.2):int(width * 0.9)]
            
            # 両方の領域でOCRを試行
            for region, region_name in [(text_region, "標準"), (extended_region, "拡張")]:
                if region.size == 0:
                    continue
                
                try:
                    # 高精度OCR前処理
                    processed_img = self.advanced_preprocess(region)
                    
                    # より包括的なOCR設定
                    ocr_config = '--oem 3 --psm 6 -l jpn+eng'
                    text = pytesseract.image_to_string(processed_img, config=ocr_config)
                    
                    print(f"      オフセット{offset}px ({region_name}): '{text.strip()}'")
                    
                    # 最大値パターンを厳密にマッチング
                    patterns = [
                        r'最大値[：:\s]*([0-9,]+)',  # 最大値：XXXX
                        r'最大[：:\s]*([0-9,]+)',    # 最大：XXXX
                        r'MAX[：:\s]*([0-9,]+)',     # MAX：XXXX
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, text)
                        if matches:
                            try:
                                value = int(matches[0].replace(',', ''))
                                # 妥当な範囲チェック（100-50000程度）
                                if 100 <= value <= 50000:
                                    # 「最大値」という文字列が含まれているかで信頼度を決定
                                    confidence = 10 if '最大値' in text else 5
                                    if '最大' in text:
                                        confidence += 3
                                    
                                    if confidence > best_confidence:
                                        best_result = {
                                            'value': value,
                                            'text': text.strip(),
                                            'offset': offset,
                                            'region': region_name,
                                            'confidence': confidence
                                        }
                                        best_confidence = confidence
                                        print(f"        ✅ 最大値候補: {value:,} (信頼度: {confidence})")
                                    break
                            except ValueError:
                                continue
                
                except Exception as e:
                    print(f"        OCRエラー ({region_name}): {str(e)}")
                    continue
        
        if best_result:
            return best_result['value'], best_result, None
        else:
            return None, None, "最大値パターンが見つかりません"
    
    def advanced_preprocess(self, img):
        """高度なOCR前処理"""
        if isinstance(img, np.ndarray):
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        else:
            img_pil = img
        
        # グレースケール変換
        img_pil = img_pil.convert('L')
        
        # コントラスト大幅強化
        enhancer = ImageEnhance.Contrast(img_pil)
        img_pil = enhancer.enhance(4.0)
        
        # 大幅リサイズ
        width, height = img_pil.size
        img_pil = img_pil.resize((width * 6, height * 6), Image.LANCZOS)
        
        # シャープ化
        img_pil = img_pil.filter(ImageFilter.SHARPEN)
        
        return img_pil
    
    def process_all_images(self):
        """全画像を処理"""
        original_files = glob.glob("graphs/original/*.jpg")
        
        print(f"🎯 精密最大値抽出開始: {len(original_files)}枚")
        print("=" * 70)
        
        for img_file in original_files:
            file_name = Path(img_file).stem
            print(f"処理中: {file_name}")
            
            max_value, details, error = self.extract_precise_max_value(img_file)
            
            result = {
                'file_name': file_name,
                'max_value': max_value,
                'details': details,
                'error': error,
                'image_path': img_file
            }
            
            self.results.append(result)
            
            if max_value is not None:
                print(f"  ✅ 最大値: {max_value:,}")
                if details:
                    print(f"     検出テキスト: '{details['text']}'")
                    print(f"     位置: オフセット{details['offset']}px ({details['region']}領域)")
            else:
                print(f"  ❌ 最大値検出失敗: {error}")
            print()
        
        return self.results
    
    def save_results(self):
        """結果保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"precise_max_values_{timestamp}.json"
        
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
    <title>🎯 精密最大値抽出レポート</title>
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
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
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
            font-size: 2.2em;
            font-weight: bold;
            color: #4ecdc4;
            margin: 15px 0;
        }}
        .details {{
            background: rgba(0,0,0,0.2);
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
        }}
        .confidence-badge {{
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
            <h1>🎯 精密最大値抽出レポート</h1>
            <p>「最大値：XXXX」パターン厳密マッチング</p>
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
            details = result['details']
            error = result['error']
            
            card_class = "success" if max_value is not None else "failure"
            
            html_content += f"""
            <div class="result-card {card_class}">
                <h3>📷 {file_name}</h3>
"""
            
            if max_value is not None:
                confidence = details['confidence'] if details else 0
                html_content += f"""
                <div class="max-value">
                    {max_value:,}
                    <span class="confidence-badge">信頼度: {confidence}</span>
                </div>
                <div class="details">
                    <div><strong>検出テキスト:</strong> "{details['text']}"</div>
                    <div><strong>位置:</strong> 0ライン+{details['offset']}px ({details['region']}領域)</div>
                </div>
"""
            else:
                html_content += f"""
                <div style="color: #ff6b6b; font-weight: bold; font-size: 1.2em;">
                    ❌ 最大値検出失敗
                </div>
                <div style="margin-top: 10px; opacity: 0.8;">
                    {error}
                </div>
"""
            
            html_content += "</div>"
        
        html_content += """
        </div>
    </div>
</body>
</html>"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"precise_max_values_{timestamp}.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 HTMLレポート保存: {output_file}")
        return output_file

if __name__ == "__main__":
    extractor = PreciseMaxValueExtractor()
    
    # 全画像処理
    results = extractor.process_all_images()
    
    # 結果サマリー
    successful = [r for r in results if r['max_value'] is not None]
    print("=" * 70)
    print(f"✅ 精密抽出完了")
    print(f"📊 総画像数: {len(results)}")
    print(f"🎯 成功数: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
    
    if successful:
        max_values = [r['max_value'] for r in successful]
        print(f"📈 最高値: {max(max_values):,}")
        print(f"📊 平均値: {int(np.mean(max_values)):,}")
        
        # 信頼度別統計
        high_confidence = [r for r in successful if r['details']['confidence'] >= 10]
        print(f"🎯 高信頼度検出: {len(high_confidence)}件 (「最大値」文字列含む)")
    
    # 結果保存
    extractor.save_results()
    extractor.create_html_report()
    
    print("=" * 70)