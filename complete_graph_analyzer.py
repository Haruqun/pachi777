#!/usr/bin/env python3
"""
完全グラフ解析ツール
- 全ての画像を自動切り抜き
- グラフから最終差玉を抽出
- 統計情報と組み合わせて完全な解析
"""

import os
import sys
import numpy as np
from PIL import Image
import cv2
import pandas as pd
from typing import Tuple, List, Optional, Dict
from datetime import datetime
import json
import glob

# 既存のスクリプトをインポート
try:
    from perfect_graph_cropper import PerfectGraphCropper
    from perfect_data_extractor import PerfectDataExtractor
    from pachinko_stats_extractor import PachinkoStatsExtractor
except ImportError:
    print("❌ 必要なモジュールがインポートできません")
    sys.exit(1)

class CompleteGraphAnalyzer:
    """完全グラフ解析システム"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        
        # 各モジュールを初期化
        self.cropper = PerfectGraphCropper(debug_mode=debug_mode)
        self.extractor = PerfectDataExtractor(debug_mode=debug_mode)
        self.stats_extractor = PachinkoStatsExtractor(debug_mode=debug_mode)
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            timestamp = datetime.now().strftime("%H:%M:%S")
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{timestamp}] {message}")
    
    def extract_final_difference(self, graph_data: pd.DataFrame, image_path: str = None) -> Optional[float]:
        """
        グラフデータから最終差玉を抽出
        """
        if graph_data is None or graph_data.empty:
            return None
            
        try:
            # 最後の10%のデータポイントから最終値を取得
            end_section = graph_data.tail(int(len(graph_data) * 0.1))
            
            if end_section.empty:
                # データが少ない場合は最後の値
                final_value = graph_data['y_value'].iloc[-1]
            else:
                # 最後の10%の平均値（ノイズ対策）
                final_value = end_section['y_value'].mean()
            
            # 最も確度の高い最終値を選択
            last_value = graph_data['y_value'].iloc[-1]
            
            # 最後の値と平均値の差が1000円以内なら最後の値を使用
            if abs(last_value - final_value) <= 1000:
                result = last_value
            else:
                result = final_value
                
            # 画像タイプを判別
            image_type = "S_画像" if (image_path and ("S__" in os.path.basename(image_path) or "S_" in os.path.basename(image_path))) else "IMG画像"
            self.log(f"最終差玉抽出 ({image_type}): {result:.0f}円", "SUCCESS")
            return round(result)
            
        except Exception as e:
            self.log(f"最終差玉抽出エラー: {e}", "ERROR")
            return None
    
    def analyze_single_image(self, image_path: str) -> Dict:
        """
        単一画像の完全解析
        """
        self.log(f"🎯 完全解析開始: {os.path.basename(image_path)}", "INFO")
        
        result = {
            "source_image": image_path,
            "timestamp": datetime.now().isoformat(),
            "cropping_success": False,
            "graph_extraction_success": False,
            "stats_extraction_success": False,
            "cropped_image": None,
            "graph_data": None,
            "final_difference_from_graph": None,
            "statistics": {},
            "errors": []
        }
        
        try:
            # Step 1: 画像切り抜き
            self.log("Step 1: 画像切り抜き", "INFO")
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            cropped_path = f"graphs/cropped_auto/{base_name}_cropped.png"
            
            success, _, _ = self.cropper.crop_perfect_graph(image_path, cropped_path)
            
            if success and os.path.exists(cropped_path):
                result["cropping_success"] = True
                result["cropped_image"] = cropped_path
                self.log("✅ 画像切り抜き成功", "SUCCESS")
                
                # Step 2: グラフデータ抽出
                self.log("Step 2: グラフデータ抽出", "INFO")
                try:
                    graph_df = self.extractor.extract_perfect_data(cropped_path)
                    
                    if graph_df is not None and not graph_df.empty:
                        result["graph_extraction_success"] = True
                        result["graph_data"] = len(graph_df)  # データ点数
                        
                        # 最終差玉をグラフから抽出
                        final_diff = self.extract_final_difference(graph_df, image_path)
                        if final_diff is not None:
                            result["final_difference_from_graph"] = final_diff
                            
                        self.log("✅ グラフデータ抽出成功", "SUCCESS")
                    else:
                        result["errors"].append("グラフデータ抽出失敗")
                        
                except Exception as e:
                    result["errors"].append(f"グラフデータ抽出エラー: {e}")
                    self.log(f"グラフデータ抽出エラー: {e}", "ERROR")
            else:
                result["errors"].append("画像切り抜き失敗")
                self.log("❌ 画像切り抜き失敗", "ERROR")
            
            # Step 3: 統計情報抽出（元画像から）
            self.log("Step 3: 統計情報抽出", "INFO")
            try:
                stats = self.stats_extractor.extract_pachinko_stats(image_path)
                
                if stats and any(v is not None for v in stats.values()):
                    result["stats_extraction_success"] = True
                    result["statistics"] = stats
                    self.log("✅ 統計情報抽出成功", "SUCCESS")
                else:
                    result["errors"].append("統計情報抽出失敗")
                    
            except Exception as e:
                result["errors"].append(f"統計情報抽出エラー: {e}")
                self.log(f"統計情報抽出エラー: {e}", "ERROR")
            
            # Step 4: 結果の統合と検証
            self.log("Step 4: 結果統合", "INFO")
            self.validate_and_merge_results(result)
            
        except Exception as e:
            result["errors"].append(f"全体処理エラー: {e}")
            self.log(f"全体処理エラー: {e}", "ERROR")
        
        return result
    
    def validate_and_merge_results(self, result: Dict):
        """
        結果の検証と統合
        """
        # グラフから抽出した最終差玉とOCRの最終差玉を比較
        graph_final = result.get("final_difference_from_graph")
        ocr_final = result.get("statistics", {}).get("最終差玉")
        
        if graph_final is not None and ocr_final is not None:
            # 両方の値が取得できた場合
            diff = abs(graph_final - ocr_final)
            
            if diff <= 500:  # 500円以内の差なら一致とみなす
                result["final_difference_verified"] = True
                result["final_difference_best"] = graph_final  # グラフの方を優先
                self.log(f"最終差玉検証: グラフ={graph_final}, OCR={ocr_final} → 一致", "SUCCESS")
            else:
                result["final_difference_verified"] = False
                result["final_difference_best"] = graph_final  # グラフの方を優先
                self.log(f"最終差玉検証: グラフ={graph_final}, OCR={ocr_final} → 不一致(差{diff}円)", "WARNING")
        elif graph_final is not None:
            # グラフのみ
            result["final_difference_best"] = graph_final
            result["final_difference_verified"] = False
            self.log(f"最終差玉: グラフのみ={graph_final}", "INFO")
        elif ocr_final is not None:
            # OCRのみ
            result["final_difference_best"] = ocr_final
            result["final_difference_verified"] = False
            self.log(f"最終差玉: OCRのみ={ocr_final}", "INFO")
        else:
            # 両方とも取得できなかった
            result["final_difference_best"] = None
            result["final_difference_verified"] = False
            self.log("最終差玉: 取得できませんでした", "WARNING")
    
    def batch_analyze_all(self, input_folder: str = "graphs") -> Dict:
        """
        フォルダ内の全画像を一括解析
        """
        self.log("🚀 全画像一括解析開始", "INFO")
        
        # 画像ファイルを検索
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg']:
            image_files.extend(glob.glob(os.path.join(input_folder, ext)))
        
        if not image_files:
            self.log(f"画像ファイルが見つかりません: {input_folder}", "ERROR")
            return {}
        
        self.log(f"📁 発見した画像: {len(image_files)}個", "INFO")
        
        # 出力フォルダ作成
        os.makedirs("graphs/cropped_auto", exist_ok=True)
        os.makedirs("graphs/extracted_data", exist_ok=True)
        
        # 結果収集用
        all_results = {}
        successful_extractions = 0
        failed_extractions = []
        
        # 各画像を処理
        for i, image_path in enumerate(image_files, 1):
            self.log(f"\n[{i}/{len(image_files)}] 処理中: {os.path.basename(image_path)}", "INFO")
            
            try:
                result = self.analyze_single_image(image_path)
                
                # 結果を保存
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                all_results[base_name] = result
                
                # 成功判定
                if (result["cropping_success"] or 
                    result["graph_extraction_success"] or 
                    result["stats_extraction_success"]):
                    successful_extractions += 1
                    self.log("✅ 解析成功", "SUCCESS")
                else:
                    failed_extractions.append(base_name)
                    self.log("❌ 解析失敗", "ERROR")
                
                # 個別結果を保存
                result_path = f"graphs/extracted_data/{base_name}_complete_analysis.json"
                with open(result_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
            except Exception as e:
                failed_extractions.append(os.path.basename(image_path))
                self.log(f"処理エラー: {e}", "ERROR")
        
        # 全体結果をまとめる
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(image_files),
            "successful": successful_extractions,
            "failed": len(failed_extractions),
            "failed_files": failed_extractions,
            "success_rate": successful_extractions / len(image_files) * 100,
            "results": all_results
        }
        
        # サマリーファイル保存
        summary_path = f"complete_analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        self.log(f"\n🎉 全画像解析完了!", "SUCCESS")
        self.log(f"✅ 成功: {successful_extractions}/{len(image_files)} ({summary['success_rate']:.1f}%)", "SUCCESS")
        self.log(f"📋 サマリー: {summary_path}", "INFO")
        
        # 統計表示
        self.display_analysis_summary(all_results)
        
        return summary
    
    def display_analysis_summary(self, results: Dict):
        """
        解析結果サマリーを表示
        """
        self.log("\n📊 解析結果サマリー", "INFO")
        self.log("=" * 60, "INFO")
        
        # 最終差玉が取得できた画像
        final_diffs = []
        graph_extractions = 0
        stat_extractions = 0
        
        for name, result in results.items():
            if result.get("final_difference_best") is not None:
                final_diffs.append(result["final_difference_best"])
            
            if result.get("graph_extraction_success"):
                graph_extractions += 1
                
            if result.get("stats_extraction_success"):
                stat_extractions += 1
        
        self.log(f"🔢 グラフデータ抽出成功: {graph_extractions}/{len(results)}", "INFO")
        self.log(f"📋 統計情報抽出成功: {stat_extractions}/{len(results)}", "INFO")
        self.log(f"💰 最終差玉取得成功: {len(final_diffs)}/{len(results)}", "INFO")
        
        if final_diffs:
            self.log(f"\n💰 最終差玉統計:", "INFO")
            self.log(f"   平均: {np.mean(final_diffs):,.0f}円", "INFO")
            self.log(f"   最大: {max(final_diffs):,.0f}円", "INFO")
            self.log(f"   最小: {min(final_diffs):,.0f}円", "INFO")
            self.log(f"   標準偏差: {np.std(final_diffs):,.0f}円", "INFO")
        
        # 各画像の結果概要
        self.log(f"\n📁 各画像の結果:", "INFO")
        for name, result in results.items():
            status_icons = []
            if result.get("cropping_success"):
                status_icons.append("✂️")
            if result.get("graph_extraction_success"):
                status_icons.append("📈")
            if result.get("stats_extraction_success"):
                status_icons.append("📋")
            
            # 最終差玉の優先順位: graph > OCR
            final_diff = result.get("final_difference_best")
            if final_diff is None:
                # グラフからの抽出
                final_diff = result.get("final_difference_from_graph")
            if final_diff is None:
                # OCRからの抽出
                stats = result.get("statistics", {})
                final_diff = stats.get("最終差玉") if stats else None
                
            final_str = f"{final_diff:,.0f}円" if final_diff is not None else "N/A"
            
            self.log(f"   {name}: {''.join(status_icons)} 最終差玉={final_str}", "INFO")

def main():
    """メイン処理"""
    print("=" * 60)
    print("🎯 完全グラフ解析ツール")
    print("=" * 60)
    print("機能:")
    print("  1. 📷 全画像の自動切り抜き")
    print("  2. 📈 グラフからの最終差玉抽出")
    print("  3. 📋 OCRによる統計情報抽出")
    print("  4. 🔍 結果の検証と統合")
    
    analyzer = CompleteGraphAnalyzer()
    
    # 入力フォルダ確認
    input_folder = "graphs"
    if not os.path.exists(input_folder):
        print(f"\n❌ 入力フォルダが見つかりません: {input_folder}")
        return
    
    # 画像ファイル検索
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg']:
        image_files.extend(glob.glob(os.path.join(input_folder, ext)))
    
    if not image_files:
        print(f"\n❌ 処理対象の画像ファイルが見つかりません")
        return
    
    print(f"\n📁 発見した画像: {len(image_files)}個")
    
    # 自動実行
    try:
        print("\n🚀 全画像の完全解析を開始します...")
        
        # 一括解析実行
        summary = analyzer.batch_analyze_all(input_folder)
        
        print(f"\n🎉 完全解析完了!")
        summary_files = [f for f in os.listdir('.') if f.startswith('complete_analysis_summary_')]
        if summary_files:
            print(f"📋 詳細結果: {summary_files[-1]}")
        print(f"📁 個別結果: graphs/extracted_data/")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 処理が中断されました")
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
    
    print(f"\n✨ 処理完了")

if __name__ == "__main__":
    main()