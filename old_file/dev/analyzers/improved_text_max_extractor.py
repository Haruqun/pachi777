#!/usr/bin/env python3
"""
改良版テキスト最大値抽出ツール
グラフ内とテキスト領域の両方から「最大値」と「最高出玉」を抽出
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

class ImprovedTextMaxExtractor:
    def __init__(self):
        self.results = []
    
    def preprocess_for_ocr(self, img, enhance_factor=2.5):
        """OCR用の画像前処理（強化版）"""
        if isinstance(img, np.ndarray):
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        else:
            img_pil = img
        
        # より強いコントラスト強化
        enhancer = ImageEnhance.Contrast(img_pil)
        img_pil = enhancer.enhance(enhance_factor)
        
        # 鮮明度向上
        enhancer = ImageEnhance.Sharpness(img_pil)
        img_pil = enhancer.enhance(2.0)
        
        # リサイズ（より大きく）
        width, height = img_pil.size
        img_pil = img_pil.resize((width * 3, height * 3), Image.LANCZOS)
        
        return img_pil
    
    def extract_from_graph_area(self, img):
        """グラフエリア内の最大値を抽出"""
        height, width = img.shape[:2]
        
        # グラフエリアを特定（おおよそ中央部分）
        graph_top = int(height * 0.35)
        graph_bottom = int(height * 0.75)
        graph_left = int(width * 0.1)
        graph_right = int(width * 0.9)
        
        graph_region = img[graph_top:graph_bottom, graph_left:graph_right]
        
        # OCR前処理
        graph_img_pil = self.preprocess_for_ocr(graph_region, enhance_factor=3.0)
        
        try:
            # より高精度設定でOCR
            ocr_config = '--oem 3 --psm 6 -l jpn+eng -c tessedit_char_whitelist=0123456789：:最大値'
            text = pytesseract.image_to_string(graph_img_pil, config=ocr_config)
            
            # グラフ内の最大値パターン
            patterns = [
                r'最大値[：:\s]*([0-9,]+)',
                r'最大[：:\s]*([0-9,]+)',
                r'MAX[：:\s]*([0-9,]+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    value = int(matches[0].replace(',', ''))
                    return value, text
            
            return None, text
            
        except Exception as e:
            return None, f"グラフOCRエラー: {str(e)}"
    
    def extract_from_stats_area(self, img):
        """統計エリアから最高出玉を抽出"""
        height, width = img.shape[:2]
        
        # 下部統計エリア
        stats_top = int(height * 0.75)
        stats_region = img[stats_top:, :]
        
        # OCR前処理
        stats_img_pil = self.preprocess_for_ocr(stats_region)
        
        try:
            ocr_config = '--oem 3 --psm 6 -l jpn+eng'
            text = pytesseract.image_to_string(stats_img_pil, config=ocr_config)
            
            # 統計情報抽出
            stats = {}
            
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
            
            # スタート回数（累計とラウンド別）
            start_patterns = [
                r'累計スタート[：:\s]*([0-9,]+)',
                r'スタート[：:\s]*([0-9,]+)'
            ]
            for pattern in start_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    if '累計' in pattern:
                        stats['total_start'] = int(matches[0].replace(',', ''))
                    else:
                        stats['round_start'] = int(matches[0].replace(',', ''))
            
            # 大当り回数
            jackpot_patterns = [
                r'大当り回数[：:\s]*([0-9,]+)回',
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
            
            return stats, text
            
        except Exception as e:
            return {}, f"統計OCRエラー: {str(e)}"
    
    def extract_all_values(self, img_path):
        """画像から全ての値を抽出"""
        img = cv2.imread(img_path)
        if img is None:
            return None, {}, "画像読み込み失敗", ""
        
        # グラフエリアから最大値を抽出
        graph_max_value, graph_text = self.extract_from_graph_area(img)
        
        # 統計エリアから情報を抽出
        stats, stats_text = self.extract_from_stats_area(img)
        
        # 最大値の優先順位：グラフ内最大値 > 最高出玉
        final_max_value = graph_max_value
        source = "グラフ内"
        
        if final_max_value is None and stats.get('max_payout'):
            final_max_value = stats['max_payout']
            source = "最高出玉"
        
        combined_text = f"【グラフエリア】\\n{graph_text}\\n\\n【統計エリア】\\n{stats_text}"
        
        return final_max_value, stats, source, combined_text
    
    def process_all_images(self):
        """全画像を処理"""
        original_files = glob.glob("graphs/original/*.jpg")
        
        print(f"🔍 改良版テキスト最大値抽出開始: {len(original_files)}枚")
        print("=" * 70)
        
        for img_file in original_files:
            file_name = Path(img_file).stem
            print(f"処理中: {file_name}")
            
            max_value, stats, source, raw_text = self.extract_all_values(img_file)
            
            result = {
                'file_name': file_name,
                'max_value': max_value,
                'source': source,
                'statistics': stats,
                'raw_ocr_text': raw_text,
                'image_path': img_file
            }
            
            self.results.append(result)
            
            if max_value is not None:
                print(f"  ✅ 最大値: {max_value:,} (出典: {source})")
                if stats:
                    key_stats = []
                    if stats.get('total_start'):
                        key_stats.append(f"累計スタート: {stats['total_start']:,}")
                    if stats.get('jackpot_count'):
                        key_stats.append(f"大当り: {stats['jackpot_count']}回")
                    if stats.get('probability'):
                        key_stats.append(f"確率: {stats['probability']}")
                    if key_stats:
                        print(f"     {' | '.join(key_stats)}")
            else:
                print(f"  ❌ 最大値検出失敗")
        
        return self.results
    
    def save_results(self):
        """結果保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"improved_text_max_{timestamp}.json"
        
        successful = [r for r in self.results if r['max_value'] is not None]
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_images': len(self.results),
            'successful_extractions': len(successful),
            'success_rate': len(successful) / len(self.results) * 100,
            'extraction_sources': {},
            'results': self.results
        }
        
        # 抽出元の統計
        for result in successful:
            source = result['source']
            report_data['extraction_sources'][source] = report_data['extraction_sources'].get(source, 0) + 1
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\\n📄 結果保存: {output_file}")
        return output_file
    
    def create_html_report(self):
        """HTMLレポート生成"""
        successful_results = [r for r in self.results if r['max_value'] is not None]
        
        # 抽出元別統計
        source_stats = {}
        for result in successful_results:
            source = result['source']
            source_stats[source] = source_stats.get(source, 0) + 1
        
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📋 改良版テキスト最大値抽出レポート</title>
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
        .source-stats {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
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
            font-size: 1.8em;
            font-weight: bold;
            color: #4ecdc4;
            margin: 10px 0;
        }}
        .source-badge {{
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 4px 8px;
            border-radius: 10px;
            font-size: 0.8em;
            margin-left: 10px;
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
            max-height: 150px;
            overflow-y: auto;
            white-space: pre-line;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 改良版パチンコテキスト最大値抽出レポート</h1>
            <p>グラフ内最大値 + 統計エリア最高出玉の複合解析</p>
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
        
        <div class="source-stats">
            <h3>📈 抽出元別統計</h3>
            <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-top: 15px;">
"""
        
        for source, count in source_stats.items():
            html_content += f"""
                <div style="background: rgba(255,255,255,0.1); padding: 10px 15px; border-radius: 10px;">
                    <strong>{source}</strong>: {count}件
                </div>
"""
        
        html_content += """
            </div>
        </div>
        
        <h2>📋 画像別抽出結果</h2>
        <div class="results-grid">
"""
        
        for result in self.results:
            file_name = result['file_name']
            max_value = result['max_value']
            source = result.get('source', '')
            stats = result['statistics']
            ocr_text = result['raw_ocr_text']
            
            card_class = "success" if max_value is not None else "failure"
            
            html_content += f"""
            <div class="result-card {card_class}">
                <h3>📷 {file_name}</h3>
"""
            
            if max_value is not None:
                html_content += f"""
                <div class="max-value">
                    最大値: {max_value:,}
                    <span class="source-badge">{source}</span>
                </div>
                <div class="stats-detail">
                    <h4>📈 統計情報:</h4>
"""
                if stats:
                    stat_items = []
                    if stats.get('total_start'):
                        stat_items.append(f"累計スタート: {stats['total_start']:,}")
                    if stats.get('round_start'):
                        stat_items.append(f"ラウンドスタート: {stats['round_start']:,}")
                    if stats.get('jackpot_count'):
                        stat_items.append(f"大当り回数: {stats['jackpot_count']}回")
                    if stats.get('probability'):
                        stat_items.append(f"大当り確率: {stats['probability']}")
                    if stats.get('max_payout'):
                        stat_items.append(f"最高出玉: {stats['max_payout']:,}")
                    
                    for item in stat_items:
                        html_content += f"<div>• {item}</div>"
                else:
                    html_content += "<div>統計情報なし</div>"
                
                html_content += "</div>"
            else:
                html_content += """
                <div style="color: #ff6b6b; font-weight: bold;">❌ 最大値の検出に失敗</div>
"""
            
            if ocr_text:
                html_content += f"""
                <div class="ocr-text">
                    <strong>OCR解析テキスト:</strong><br>
                    {ocr_text[:400]}{'...' if len(ocr_text) > 400 else ''}
                </div>
"""
            
            html_content += "</div>"
        
        html_content += """
        </div>
    </div>
</body>
</html>"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"improved_text_max_{timestamp}.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 HTMLレポート保存: {output_file}")
        return output_file

if __name__ == "__main__":
    extractor = ImprovedTextMaxExtractor()
    
    # 全画像処理
    results = extractor.process_all_images()
    
    # 結果サマリー
    successful = [r for r in results if r['max_value'] is not None]
    print("\\n" + "=" * 70)
    print(f"✅ 改良版OCR抽出完了")
    print(f"📊 総画像数: {len(results)}")
    print(f"🎯 成功数: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
    
    if successful:
        max_values = [r['max_value'] for r in successful]
        print(f"📈 最高値: {max(max_values):,}")
        print(f"📊 平均値: {int(np.mean(max_values)):,}")
        
        # 抽出元別統計
        source_stats = {}
        for result in successful:
            source = result['source']
            source_stats[source] = source_stats.get(source, 0) + 1
        
        print("📈 抽出元別:")
        for source, count in source_stats.items():
            print(f"   {source}: {count}件")
    
    # 結果保存
    extractor.save_results()
    extractor.create_html_report()
    
    print("=" * 70)