#!/usr/bin/env python3
"""
完璧グラフ切り抜きツール
- グラフサイズ基準: 911px × 797px
- オレンジバー検出 → グラフエリア特定
- 0ライン検出 → 正確な位置調整
- 完璧な精度を目指した決定版
"""

import os
import numpy as np
from PIL import Image
import cv2
from typing import Tuple, Optional, Dict
from datetime import datetime
import json


class PerfectGraphCropper:
    """完璧グラフ切り抜きシステム"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        # 標準グラフサイズ
        self.GRAPH_WIDTH = 911
        self.GRAPH_HEIGHT = 797
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            timestamp = datetime.now().strftime("%H:%M:%S")
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{timestamp}] {message}")
    
    def detect_orange_bar_precise(self, image_path: str) -> Optional[Tuple[int, int]]:
        """
        高精度オレンジバー検出
        Returns: (top_y, bottom_y) or None
        """
        self.log("オレンジバー検出を開始", "DEBUG")
        
        img = Image.open(image_path)
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        # HSV色空間での検出
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        
        # オレンジ色の範囲（HSV）- より広範囲で検出
        orange_ranges = [
            ([10, 100, 100], [30, 255, 255]),  # 標準オレンジ
            ([5, 120, 120], [35, 255, 255]),   # 幅広オレンジ
            ([15, 80, 80], [25, 255, 255])     # 明るいオレンジ
        ]
        
        orange_mask = np.zeros((height, width), dtype=np.uint8)
        
        for lower, upper in orange_ranges:
            lower = np.array(lower)
            upper = np.array(upper)
            mask = cv2.inRange(hsv, lower, upper)
            orange_mask = cv2.bitwise_or(orange_mask, mask)
        
        # 水平線強調
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (width//4, 1))
        orange_lines = cv2.morphologyEx(orange_mask, cv2.MORPH_OPEN, kernel)
        
        # オレンジバーの候補行を検出
        orange_rows = []
        for y in range(height):
            orange_pixel_count = np.sum(orange_lines[y, :])
            coverage = orange_pixel_count / width
            
            # 行の40%以上がオレンジならオレンジバー候補
            if coverage > 0.4:
                orange_rows.append((y, coverage, orange_pixel_count))
        
        if not orange_rows:
            self.log("オレンジバーが検出されませんでした", "WARNING")
            return None
        
        # 最も太いオレンジバー領域を特定
        orange_rows.sort(key=lambda x: x[0])  # Y座標順
        
        # 連続する行をグループ化
        groups = []
        current_group = [orange_rows[0]]
        
        for i in range(1, len(orange_rows)):
            prev_y = current_group[-1][0]
            curr_y = orange_rows[i][0]
            
            if curr_y - prev_y <= 3:  # 3px以内なら同じグループ
                current_group.append(orange_rows[i])
            else:
                groups.append(current_group)
                current_group = [orange_rows[i]]
        
        groups.append(current_group)
        
        # 最も密度の高いグループを選択
        best_group = max(groups, key=lambda g: sum(row[1] for row in g))
        
        orange_top = best_group[0][0]
        orange_bottom = best_group[-1][0]
        
        self.log(f"オレンジバー検出成功: Y={orange_top}-{orange_bottom}", "SUCCESS")
        return (orange_top, orange_bottom)
    
    def detect_zero_line_in_graph(self, image_path: str, graph_top: int, graph_bottom: int) -> Optional[int]:
        """
        グラフエリア内での0ライン検出
        """
        self.log("グラフエリア内0ライン検出を開始", "DEBUG")
        
        img = Image.open(image_path)
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        # グラフエリアのみを抽出
        graph_region = img_array[graph_top:graph_bottom, :, :]
        gray_graph = cv2.cvtColor(graph_region, cv2.COLOR_RGB2GRAY)
        
        region_height = graph_bottom - graph_top
        
        # グラフエリア内での水平線検出
        line_scores = []
        
        # 左右20%を除外して中央部分を分析
        left_margin = int(width * 0.2)
        right_margin = int(width * 0.8)
        
        for y in range(region_height):
            row = gray_graph[y, left_margin:right_margin]
            
            # 水平線の特徴分析
            mean_val = np.mean(row)
            min_val = np.min(row)
            std_val = np.std(row)
            
            # 暗い線スコア
            darkness_score = (255 - mean_val) / 255
            
            # 一様性スコア
            uniformity_score = 1 / (1 + std_val)
            
            # 最小値の暗さ
            min_darkness_score = (255 - min_val) / 255
            
            # 水平線らしさスコア
            total_score = darkness_score * 0.4 + uniformity_score * 0.3 + min_darkness_score * 0.3
            
            line_scores.append((y, total_score))
        
        # グラフ中央付近の最高スコア線を選択
        center_y = region_height // 2
        center_range = region_height // 4
        
        center_candidates = [(y, score) for y, score in line_scores 
                           if center_y - center_range <= y <= center_y + center_range]
        
        if center_candidates:
            best_line_relative = max(center_candidates, key=lambda x: x[1])[0]
            zero_line_absolute = graph_top + best_line_relative
            
            self.log(f"0ライン検出成功: Y={zero_line_absolute} (グラフ内相対: {best_line_relative})", "SUCCESS")
            return zero_line_absolute
        
        self.log("0ライン検出失敗", "WARNING")
        return None
    
    def calculate_perfect_bounds(self, image_path: str) -> Optional[Tuple[int, int, int, int]]:
        """
        完璧な切り抜き境界を計算
        
        Returns: (left, top, right, bottom) or None
        """
        self.log(f"完璧境界計算開始: {os.path.basename(image_path)}", "INFO")
        
        img = Image.open(image_path)
        width, height = img.size
        
        # Step 1: オレンジバー検出
        orange_result = self.detect_orange_bar_precise(image_path)
        if orange_result is None:
            self.log("オレンジバー検出失敗、レイアウト分析にフォールバック", "WARNING")
            return self._fallback_layout_analysis(width, height)
        
        orange_top, orange_bottom = orange_result
        
        # Step 2: グラフエリアの推定位置
        # オレンジバーの直下にグラフエリアがある
        estimated_graph_top = orange_bottom + 10  # 少し余裕
        estimated_graph_bottom = estimated_graph_top + self.GRAPH_HEIGHT
        
        # Step 3: グラフエリア内で0ライン検出
        zero_line_y = self.detect_zero_line_in_graph(image_path, estimated_graph_top, estimated_graph_bottom)
        
        if zero_line_y is None:
            self.log("0ライン検出失敗、推定位置を使用", "WARNING")
            zero_line_y = estimated_graph_top + (self.GRAPH_HEIGHT // 2)
        
        # Step 4: 0ラインを基準とした完璧な境界計算
        # グラフの標準サイズ 911×797 を基準に配置
        
        # 横方向: 画面中央に配置
        graph_left = (width - self.GRAPH_WIDTH) // 2
        graph_right = graph_left + self.GRAPH_WIDTH
        
        # 縦方向: 0ラインが適切な位置になるよう調整
        # 実測に基づく調整: 84px下にずらす（81-87pxの中央値）
        # 通常、0ラインはグラフの中央やや下（60%位置）にある
        zero_line_offset_from_top = int(self.GRAPH_HEIGHT * 0.6)
        
        graph_top = zero_line_y - zero_line_offset_from_top + 84  # 84px下に調整
        graph_bottom = graph_top + self.GRAPH_HEIGHT
        
        # 境界の妥当性チェック
        if graph_top < 0:
            graph_top = estimated_graph_top
            graph_bottom = graph_top + self.GRAPH_HEIGHT
        
        if graph_bottom > height:
            graph_bottom = height - 10
            graph_top = graph_bottom - self.GRAPH_HEIGHT
        
        # 左右の微調整（画面端からの適切な距離を確保）
        left_margin = max(20, (width - self.GRAPH_WIDTH) // 2)
        right_margin = max(20, (width - self.GRAPH_WIDTH) // 2)
        
        final_left = left_margin
        final_right = width - right_margin
        final_top = graph_top
        final_bottom = graph_bottom
        
        # 最終サイズ調整
        actual_width = final_right - final_left
        actual_height = final_bottom - final_top
        
        self.log(f"完璧境界計算完了:", "SUCCESS")
        self.log(f"  オレンジバー: Y={orange_top}-{orange_bottom}", "DEBUG")
        self.log(f"  0ライン: Y={zero_line_y}", "DEBUG")
        self.log(f"  最終境界: ({final_left}, {final_top}, {final_right}, {final_bottom})", "DEBUG")
        self.log(f"  最終サイズ: {actual_width} × {actual_height}", "DEBUG")
        self.log(f"  目標サイズ: {self.GRAPH_WIDTH} × {self.GRAPH_HEIGHT}", "DEBUG")
        
        return (final_left, final_top, final_right, final_bottom)
    
    def _fallback_layout_analysis(self, width: int, height: int) -> Tuple[int, int, int, int]:
        """フォールバック: レイアウト分析"""
        self.log("フォールバックレイアウト分析", "WARNING")
        
        # パチンコアプリの標準レイアウト
        if height > 2400:  # 高解像度
            top_ratio = 0.32
            left_ratio = 0.06
            right_ratio = 0.94
        else:  # 標準解像度
            top_ratio = 0.30
            left_ratio = 0.08
            right_ratio = 0.92
        
        left = int(width * left_ratio)
        right = int(width * right_ratio)
        top = int(height * top_ratio)
        bottom = top + self.GRAPH_HEIGHT
        
        return (left, top, right, bottom)
    
    def crop_perfect_graph(self, image_path: str, output_path: str = None) -> Tuple[bool, Optional[str], Dict]:
        """
        完璧なグラフ切り抜きを実行
        
        Returns: (成功フラグ, 出力パス, 詳細情報)
        """
        try:
            self.log(f"🎯 完璧グラフ切り抜き開始: {os.path.basename(image_path)}", "INFO")
            
            # 完璧な境界を計算
            bounds = self.calculate_perfect_bounds(image_path)
            if bounds is None:
                return False, None, {"error": "境界計算失敗"}
            
            left, top, right, bottom = bounds
            
            # 切り抜き実行
            img = Image.open(image_path)
            cropped_img = img.crop(bounds)
            
            # 出力パス設定
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_dir = "graphs/cropped_perfect"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{base_name}_perfect.png")
            
            # 保存
            cropped_img.save(output_path)
            
            # 詳細情報
            actual_width = right - left
            actual_height = bottom - top
            
            # 精度評価
            width_accuracy = min(actual_width / self.GRAPH_WIDTH, self.GRAPH_WIDTH / actual_width) * 100
            height_accuracy = min(actual_height / self.GRAPH_HEIGHT, self.GRAPH_HEIGHT / actual_height) * 100
            overall_accuracy = (width_accuracy + height_accuracy) / 2
            
            details = {
                "bounds": bounds,
                "actual_size": (actual_width, actual_height),
                "target_size": (self.GRAPH_WIDTH, self.GRAPH_HEIGHT),
                "width_accuracy": width_accuracy,
                "height_accuracy": height_accuracy,
                "overall_accuracy": overall_accuracy,
                "output_path": output_path
            }
            
            self.log(f"✅ 完璧切り抜き完了: {output_path}", "SUCCESS")
            self.log(f"   サイズ精度: 横{width_accuracy:.1f}% × 縦{height_accuracy:.1f}%", "SUCCESS")
            self.log(f"   総合精度: {overall_accuracy:.1f}%", "SUCCESS")
            
            return True, output_path, details
            
        except Exception as e:
            self.log(f"切り抜きエラー: {e}", "ERROR")
            return False, None, {"error": str(e)}
    
    def batch_process_perfect(self, input_folder: str = "graphs", 
                            output_folder: str = "graphs/cropped_perfect"):
        """完璧切り抜きバッチ処理"""
        self.log("🎯 完璧切り抜きバッチ処理開始", "INFO")
        
        if not os.path.exists(input_folder):
            self.log(f"入力フォルダが見つかりません: {input_folder}", "ERROR")
            return
        
        # 対象画像ファイル
        image_files = [f for f in os.listdir(input_folder)
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                      and not f.endswith('_perfect.png')]
        
        if not image_files:
            self.log("処理対象の画像ファイルが見つかりません", "ERROR")
            return
        
        os.makedirs(output_folder, exist_ok=True)
        
        self.log(f"📁 処理対象: {len(image_files)}個のファイル", "INFO")
        
        successful = 0
        failed = []
        all_details = []
        
        for i, filename in enumerate(image_files, 1):
            self.log(f"\n[{i}/{len(image_files)}] 処理中: {filename}", "INFO")
            
            input_path = os.path.join(input_folder, filename)
            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(output_folder, f"{base_name}_perfect.png")
            
            success, result_path, details = self.crop_perfect_graph(input_path, output_path)
            
            if success:
                successful += 1
                details["filename"] = filename
                all_details.append(details)
            else:
                failed.append(filename)
        
        # バッチ処理結果
        self.log(f"\n🎉 完璧切り抜きバッチ処理完了!", "SUCCESS")
        self.log(f"✅ 成功: {successful}/{len(image_files)}", "SUCCESS")
        
        if failed:
            self.log(f"❌ 失敗: {len(failed)}個", "ERROR")
            for f in failed:
                self.log(f"  - {f}", "ERROR")
        
        # 精度統計
        if all_details:
            accuracies = [d["overall_accuracy"] for d in all_details]
            avg_accuracy = np.mean(accuracies)
            min_accuracy = min(accuracies)
            max_accuracy = max(accuracies)
            
            self.log(f"📊 精度統計:", "INFO")
            self.log(f"   平均精度: {avg_accuracy:.1f}%", "INFO")
            self.log(f"   最高精度: {max_accuracy:.1f}%", "INFO")
            self.log(f"   最低精度: {min_accuracy:.1f}%", "INFO")
        
        # レポート保存
        report = {
            "timestamp": datetime.now().isoformat(),
            "input_folder": input_folder,
            "output_folder": output_folder,
            "total_files": len(image_files),
            "successful": successful,
            "failed": failed,
            "average_accuracy": avg_accuracy if all_details else 0,
            "details": all_details,
            "target_graph_size": {"width": self.GRAPH_WIDTH, "height": self.GRAPH_HEIGHT}
        }
        
        report_path = f"perfect_crop_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.log(f"📋 レポート保存: {report_path}", "INFO")
        self.log(f"📁 出力フォルダ: {output_folder}", "INFO")


def main():
    """メイン処理"""
    print("=" * 60)
    print("🎯 完璧グラフ切り抜きツール")
    print("=" * 60)
    print(f"📏 標準グラフサイズ: 911px × 797px")
    print("🔍 オレンジバー検出 + 0ライン基準")
    print("🎮 完璧な精度を目指した決定版")
    
    cropper = PerfectGraphCropper()
    
    # 入力フォルダチェック
    input_folder = "graphs"
    if not os.path.exists(input_folder):
        print(f"\n❌ 入力フォルダが見つかりません: {input_folder}")
        return
    
    # 画像ファイル検索
    image_files = [f for f in os.listdir(input_folder)
                  if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                  and not f.endswith('_perfect.png')]
    
    if not image_files:
        print(f"\n❌ 処理対象の画像ファイルが見つかりません")
        return
    
    print(f"\n📁 見つかった画像ファイル ({len(image_files)}個):")
    for i, file in enumerate(image_files, 1):
        print(f"   {i}. {file}")
    
    # 処理モード選択
    print(f"\n🎯 処理モードを選択:")
    print("1. 🚀 完璧切り抜きバッチ処理（推奨）")
    print("2. 📷 単一画像の完璧処理")
    print("3. 🔍 境界計算テスト（切り抜きなし）")
    
    try:
        choice = input("\n選択 (1-3): ").strip()
        
        if choice == "1":
            # バッチ処理
            cropper.batch_process_perfect()
            
        elif choice == "2":
            # 単一画像処理
            print(f"\n📁 画像を選択:")
            for i, file in enumerate(image_files, 1):
                print(f"{i}. {file}")
            
            try:
                file_num = int(input("画像番号を選択: "))
                if 1 <= file_num <= len(image_files):
                    selected_file = image_files[file_num - 1]
                    image_path = os.path.join(input_folder, selected_file)
                    
                    success, output_path, details = cropper.crop_perfect_graph(image_path)
                    
                    if success:
                        print(f"\n🎉 完璧切り抜き成功!")
                        print(f"📁 出力: {output_path}")
                        print(f"📊 精度: {details['overall_accuracy']:.1f}%")
                        print(f"📏 サイズ: {details['actual_size'][0]}×{details['actual_size'][1]}")
                    else:
                        print(f"\n❌ 切り抜き失敗")
                else:
                    print("❌ 無効な番号です")
            except ValueError:
                print("❌ 数字を入力してください")
                
        elif choice == "3":
            # 境界計算テスト
            print(f"\n📁 画像を選択:")
            for i, file in enumerate(image_files, 1):
                print(f"{i}. {file}")
            
            try:
                file_num = int(input("画像番号を選択: "))
                if 1 <= file_num <= len(image_files):
                    selected_file = image_files[file_num - 1]
                    image_path = os.path.join(input_folder, selected_file)
                    
                    bounds = cropper.calculate_perfect_bounds(image_path)
                    
                    if bounds:
                        left, top, right, bottom = bounds
                        width = right - left
                        height = bottom - top
                        
                        print(f"\n🔍 境界計算結果:")
                        print(f"   境界: ({left}, {top}, {right}, {bottom})")
                        print(f"   サイズ: {width} × {height}")
                        print(f"   目標: {cropper.GRAPH_WIDTH} × {cropper.GRAPH_HEIGHT}")
                        print(f"   精度: 横{width/cropper.GRAPH_WIDTH*100:.1f}% × 縦{height/cropper.GRAPH_HEIGHT*100:.1f}%")
                    else:
                        print(f"\n❌ 境界計算失敗")
                else:
                    print("❌ 無効な番号です")
            except ValueError:
                print("❌ 数字を入力してください")
        else:
            print("❌ 無効な選択です")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 処理が中断されました")
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
    
    print(f"\n✨ 処理完了")


if __name__ == "__main__":
    main()