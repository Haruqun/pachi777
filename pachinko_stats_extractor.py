#!/usr/bin/env python3
"""
パチンコ統計情報抽出ツール
- OCRを使って画面下部の重要な数値を抽出
- 累計スタート、スタート、大当たり回数、初当たり回数、大当たり確率、最高出玉
"""

import os
import re
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import pytesseract
from typing import Dict, Optional, Tuple
from datetime import datetime
import json

class PachinkoStatsExtractor:
    """パチンコ統計情報抽出システム"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        
        # OCR設定（日本語 + 数字）
        self.ocr_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789/回初当り確率最高出玉累計スタート：'
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            timestamp = datetime.now().strftime("%H:%M:%S")
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{timestamp}] {message}")
    
    def extract_stats_region(self, image_path: str) -> Image.Image:
        """
        統計情報表示領域を切り出し
        画面下部の統計情報部分を特定して抽出（最大値を含む領域を拡張）
        """
        self.log("統計情報領域の抽出を開始", "DEBUG")
        
        img = Image.open(image_path)
        width, height = img.size
        
        # 統計情報は画面下部の広い範囲（グラフ下部の「最大値」も含む）
        stats_top = int(height * 0.55)    # グラフ内下部から開始（最大値表示を含む）
        stats_bottom = int(height * 0.85)  # ボタンまで
        
        # 左右のマージンを除いた中央部分
        stats_left = int(width * 0.05)
        stats_right = int(width * 0.95)
        
        # 統計情報領域を切り出し
        stats_region = img.crop((stats_left, stats_top, stats_right, stats_bottom))
        
        self.log(f"統計情報領域: ({stats_left}, {stats_top}) - ({stats_right}, {stats_bottom})", "DEBUG")
        
        if self.debug_mode:
            # デバッグ用に切り出し領域を保存
            debug_path = "debug_stats_region.png"
            stats_region.save(debug_path)
            self.log(f"デバッグ用統計領域保存: {debug_path}", "DEBUG")
        
        return stats_region
    
    def preprocess_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        OCR精度向上のための前処理
        """
        self.log("OCR前処理を開始", "DEBUG")
        
        # PILからOpenCVに変換
        img_array = np.array(image)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # グレースケール変換
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # コントラスト強化
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # ノイズ除去
        denoised = cv2.medianBlur(enhanced, 3)
        
        # 二値化（適応的閾値）
        binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
        
        # モルフォロジー演算でテキストを強化
        kernel = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # OpenCVからPILに変換
        result = Image.fromarray(cleaned)
        
        # サイズを2倍に拡大（OCR精度向上）
        width, height = result.size
        result = result.resize((width*2, height*2), Image.Resampling.LANCZOS)
        
        if self.debug_mode:
            result.save("debug_preprocessed_stats.png")
            self.log("前処理済み画像保存: debug_preprocessed_stats.png", "DEBUG")
        
        return result
    
    def extract_text_with_ocr(self, image: Image.Image) -> str:
        """
        OCRでテキストを抽出
        """
        self.log("OCRテキスト抽出を開始", "DEBUG")
        
        try:
            # Tesseractで文字認識
            text = pytesseract.image_to_string(image, lang='jpn', config=self.ocr_config)
            
            self.log(f"OCR抽出テキスト:\n{text}", "DEBUG")
            return text
            
        except Exception as e:
            self.log(f"OCRエラー: {e}", "ERROR")
            return ""
    
    def parse_statistics(self, text: str) -> Dict[str, Optional[int]]:
        """
        抽出されたテキストから統計数値をパース
        """
        self.log("統計数値のパース開始", "DEBUG")
        
        stats = {
            "累計スタート": None,
            "スタート": None,
            "大当たり回数": None,
            "初当たり回数": None,
            "大当たり確率_分母": None,
            "最高出玉": None,
            "最終差玉": None
        }
        
        # テキストを行ごとに分割
        lines = text.strip().split('\n')
        combined_text = ' '.join(lines)
        
        self.log(f"パース対象テキスト: {combined_text}", "DEBUG")
        
        # 各項目のパターンマッチング（OCRで認識されたテキストに基づく）
        patterns = {
            "累計スタート": [
                r'累計スタート[：:\s]*(\d+)',
                r'累計[：:\s]*(\d+)',
            ],
            "スタート": [
                r'4318\s+スタート\s+(\d+)',                      # 4318スタート 350のパターン
                r'(?<!累計)スタート\s+(\d+)',                     # 累計でないスタート
                r'\s+スタート\s+(\d+)(?!\s*大当)',               # スタートの後の数字（大当りでない）
            ],
            "大当たり回数": [
                r'当り回[：:\s]*(\d+)回',     # OCRで"大当り回数"が"当り回"に認識される
                r'大当り回数[：:\s]*(\d+)回',
                r'大当り[：:\s]*(\d+)回',
                r'当り[：:\s]*(\d+)回',
            ],
            "初当たり回数": [
                r'初当り回[：:\s]*(\d+)回',    # OCRで"初当り回数"が"初当り回"に認識される
                r'初当り回数[：:\s]*(\d+)回',
                r'初当り[：:\s]*(\d+)回',
                r'初当[：:\s]*(\d+)回',
            ],
            "大当たり確率_分母": [
                r'当り確率[：:\s]*1/(\d+)',    # OCRで"大当り確率"が"当り確率"に認識される
                r'大当り確率[：:\s]*1/(\d+)',
                r'確率[：:\s]*1/(\d+)',
                r'1/(\d+)',
            ],
            "最高出玉": [
                r'最高出玉[：:\s]*(\d+)',
                r'最高[：:\s]*(\d+)',
                r'出玉[：:\s]*(\d+)',
            ],
            "最終差玉": [
                r'最大値[：:\s]*(\d+)',
                r'最大[：:\s]*(\d+)',
                r'差玉[：:\s]*(\d+)',
                r'^(\d{4})$',                    # 行頭の4桁数字（3520など）
                r'^\s*(\d{3,5})\s*$',           # 独立した3-5桁数字
            ]
        }
        
        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                # 結合されたテキストでマッチを試行
                match = re.search(pattern, combined_text)
                if match:
                    try:
                        stats[key] = int(match.group(1))
                        self.log(f"{key}: {stats[key]}", "SUCCESS")
                        break
                    except (ValueError, IndexError):
                        continue
                
                # 各行に対してもマッチを試行（特に独立した数字のため）
                if not match:
                    for line in lines:
                        match = re.search(pattern, line.strip())
                        if match:
                            try:
                                stats[key] = int(match.group(1))
                                self.log(f"{key}: {stats[key]} (from line: {line.strip()})", "SUCCESS")
                                break
                            except (ValueError, IndexError):
                                continue
                    if match:
                        break
        
        return stats
    
    def extract_pachinko_stats(self, image_path: str) -> Dict[str, Optional[int]]:
        """
        パチンコ統計情報の完全抽出
        """
        try:
            self.log(f"🎯 パチンコ統計情報抽出開始: {os.path.basename(image_path)}", "INFO")
            
            # 1. 統計情報領域を切り出し
            stats_region = self.extract_stats_region(image_path)
            
            # 2. OCR前処理
            preprocessed = self.preprocess_for_ocr(stats_region)
            
            # 3. OCRでテキスト抽出
            text = self.extract_text_with_ocr(preprocessed)
            
            # 4. 統計数値をパース
            stats = self.parse_statistics(text)
            
            # 5. 結果の検証と追加計算
            validated_stats = self.validate_and_enhance_stats(stats)
            
            self.log("✅ 統計情報抽出完了", "SUCCESS")
            return validated_stats
            
        except Exception as e:
            self.log(f"統計情報抽出エラー: {e}", "ERROR")
            return {}
    
    def validate_and_enhance_stats(self, stats: Dict[str, Optional[int]]) -> Dict[str, Optional[int]]:
        """
        統計情報の検証と追加計算
        """
        self.log("統計情報の検証と拡張", "DEBUG")
        
        # 基本的な妥当性チェック
        if stats.get("累計スタート") and stats.get("大当たり回数"):
            # 実際の大当たり確率を計算
            actual_prob = stats["累計スタート"] // stats["大当たり回数"]
            stats["実際の確率分母"] = actual_prob
            
        if stats.get("大当たり回数") and stats.get("初当たり回数"):
            # 連チャン率を計算
            if stats["初当たり回数"] > 0:
                chain_rate = (stats["大当たり回数"] - stats["初当たり回数"]) / stats["初当たり回数"]
                stats["連チャン率"] = round(chain_rate, 2)
        
        # 妥当性チェック結果をログ出力
        for key, value in stats.items():
            if value is not None:
                self.log(f"  {key}: {value}", "INFO")
        
        return stats
    
    def save_stats_to_file(self, stats: Dict, image_path: str, output_folder: str = "graphs/extracted_data"):
        """
        統計情報をJSONファイルに保存
        """
        os.makedirs(output_folder, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_path = os.path.join(output_folder, f"{base_name}_stats.json")
        
        # メタデータを追加
        output_data = {
            "source_image": image_path,
            "extraction_timestamp": datetime.now().isoformat(),
            "statistics": stats
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        self.log(f"統計情報保存: {output_path}", "SUCCESS")
        return output_path

def batch_process_graphs():
    """graphsフォルダ内の全PNG画像を一括処理"""
    import glob
    
    extractor = PachinkoStatsExtractor()
    
    # graphsフォルダ内の画像ファイルを取得（PNG, JPG両方）
    image_files = glob.glob("graphs/*.png") + glob.glob("graphs/*.jpg")
    
    if not image_files:
        print("📂 graphsフォルダに画像ファイルが見つかりません")
        return
    
    print(f"🔍 {len(image_files)}個の画像ファイルを発見")
    print("="*60)
    
    results = []
    
    for i, image_path in enumerate(image_files, 1):
        print(f"\n🔄 [{i}/{len(image_files)}] 処理中: {os.path.basename(image_path)}")
        
        try:
            stats = extractor.extract_pachinko_stats(image_path)
            extractor.save_stats_to_file(stats, image_path)
            
            # 結果を保存
            results.append({
                "file": os.path.basename(image_path),
                "stats": stats
            })
            
            print("✅ 処理完了")
            
        except Exception as e:
            print(f"❌ 処理エラー: {e}")
            results.append({
                "file": os.path.basename(image_path),
                "error": str(e)
            })
    
    # 一括結果表示
    print("\n" + "="*60)
    print("📊 一括処理結果サマリー")
    print("="*60)
    
    for result in results:
        print(f"\n📁 {result['file']}:")
        if 'error' in result:
            print(f"  ❌ エラー: {result['error']}")
        else:
            stats = result['stats']
            if stats:
                for key, value in stats.items():
                    if value is not None:
                        print(f"  {key}: {value}")
            else:
                print("  ⚠️ 統計情報なし")
    
    return results

def main():
    """メイン実行関数"""
    batch_process_graphs()

if __name__ == "__main__":
    main()