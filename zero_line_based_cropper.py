#!/usr/bin/env python3
"""
0ライン基準グラフ切り抜きツール
- 0ライン（ゼロライン）を検出
- ゼロラインから上下指定ピクセル範囲を切り抜き
- シンプルで高精度なアプローチ
"""

import os
import numpy as np
from PIL import Image
import cv2
from typing import Tuple, Optional
from datetime import datetime


class ZeroLineBasedCropper:
    """0ライン基準の切り抜きシステム"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
    
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            timestamp = datetime.now().strftime("%H:%M:%S")
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{timestamp}] {message}")
    
    def detect_zero_line_enhanced(self, image_path: str) -> Optional[int]:
        """
        強化された0ライン検出
        - 複数手法の統合
        - より高精度な検出
        """
        self.log("0ライン検出を開始", "DEBUG")
        
        img = Image.open(image_path)
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        # 手法1: グレースケール分析
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        zero_line_1 = self._detect_by_grayscale_analysis(gray, width, height)
        
        # 手法2: エッジ検出
        zero_line_2 = self._detect_by_edge_analysis(gray, width, height)
        
        # 手法3: 水平線検出
        zero_line_3 = self._detect_by_horizontal_line(gray, width, height)
        
        # 手法4: 色分析（黒線検出）
        zero_line_4 = self._detect_by_color_analysis(img_array, width, height)
        
        # 結果統合
        candidates = [line for line in [zero_line_1, zero_line_2, zero_line_3, zero_line_4] if line is not None]
        
        if not candidates:
            self.log("0ラインが検出できませんでした", "WARNING")
            # フォールバック: 画面中央付近
            return height // 2
        
        # 中央値を採用（外れ値に強い）
        final_zero_line = int(np.median(candidates))
        
        self.log(f"0ライン検出結果:", "SUCCESS")
        self.log(f"  手法1(グレー): {zero_line_1}", "DEBUG")
        self.log(f"  手法2(エッジ): {zero_line_2}", "DEBUG")
        self.log(f"  手法3(水平線): {zero_line_3}", "DEBUG")
        self.log(f"  手法4(色分析): {zero_line_4}", "DEBUG")
        self.log(f"  最終結果: Y={final_zero_line}", "SUCCESS")
        
        return final_zero_line
    
    def _detect_by_grayscale_analysis(self, gray: np.ndarray, width: int, height: int) -> Optional[int]:
        """グレースケール分析による0ライン検出"""
        line_scores = []
        
        # 画像の中央部分のみを分析（左右20%ずつ除外）
        left_margin = int(width * 0.2)
        right_margin = int(width * 0.8)
        
        for y in range(height):
            row = gray[y, left_margin:right_margin]
            
            # 水平線の特徴
            mean_val = np.mean(row)
            min_val = np.min(row)
            std_val = np.std(row)
            
            # スコア計算（暗くて一様な線ほど高スコア）
            darkness_score = (255 - mean_val) / 255
            uniformity_score = 1 / (1 + std_val)
            min_darkness_score = (255 - min_val) / 255
            
            total_score = darkness_score * 0.4 + uniformity_score * 0.4 + min_darkness_score * 0.2
            line_scores.append((y, total_score))
        
        # 画像中央付近の最高スコア線を選択
        center_y = height // 2
        center_range = height // 4
        
        center_candidates = [(y, score) for y, score in line_scores 
                           if center_y - center_range <= y <= center_y + center_range]
        
        if center_candidates:
            best_line = max(center_candidates, key=lambda x: x[1])
            return best_line[0]
        
        return None
    
    def _detect_by_edge_analysis(self, gray: np.ndarray, width: int, height: int) -> Optional[int]:
        """エッジ検出による0ライン検出"""
        # Cannyエッジ検出
        edges = cv2.Canny(gray, 30, 100)
        
        # 水平線強調フィルタ
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (width//4, 1))
        horizontal_edges = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
        
        # 各行のエッジ密度を計算
        edge_densities = []
        for y in range(height):
            edge_count = np.sum(horizontal_edges[y, :])
            edge_densities.append((y, edge_count))
        
        # 画像中央付近で最も密度が高い行を選択
        center_y = height // 2
        center_range = height // 3
        
        center_candidates = [(y, density) for y, density in edge_densities 
                           if center_y - center_range <= y <= center_y + center_range
                           and density > 0]
        
        if center_candidates:
            best_line = max(center_candidates, key=lambda x: x[1])
            return best_line[0]
        
        return None
    
    def _detect_by_horizontal_line(self, gray: np.ndarray, width: int, height: int) -> Optional[int]:
        """形態学的演算による水平線検出"""
        # 水平線検出カーネル
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (width//3, 1))
        
        # 白いピクセルの水平線を検出
        white_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
        
        # 黒いピクセルの水平線を検出（反転してから処理）
        inverted_gray = 255 - gray
        black_lines = cv2.morphologyEx(inverted_gray, cv2.MORPH_OPEN, horizontal_kernel)
        
        # 両方の結果を統合
        combined_lines = cv2.add(white_lines, black_lines)
        
        # 各行での線の強度を測定
        line_strengths = []
        for y in range(height):
            strength = np.sum(combined_lines[y, :])
            line_strengths.append((y, strength))
        
        # 画像中央付近で最強の線を選択
        center_y = height // 2
        center_range = height // 3
        
        center_candidates = [(y, strength) for y, strength in line_strengths 
                           if center_y - center_range <= y <= center_y + center_range
                           and strength > np.mean([s for _, s in line_strengths])]
        
        if center_candidates:
            best_line = max(center_candidates, key=lambda x: x[1])
            return best_line[0]
        
        return None
    
    def _detect_by_color_analysis(self, img_array: np.ndarray, width: int, height: int) -> Optional[int]:
        """色分析による黒線検出"""
        line_blackness = []
        
        # 左右20%を除外した中央部分を分析
        left_margin = int(width * 0.2)
        right_margin = int(width * 0.8)
        
        for y in range(height):
            row = img_array[y, left_margin:right_margin, :]
            
            # RGB各チャンネルの平均
            r_mean = np.mean(row[:, 0])
            g_mean = np.mean(row[:, 1])
            b_mean = np.mean(row[:, 2])
            
            # 黒さの指標（値が小さいほど黒い）
            blackness = (r_mean + g_mean + b_mean) / 3
            
            # 色の一様性（RGB値の差が小さいほど一様）
            color_variance = np.var([r_mean, g_mean, b_mean])
            uniformity = 1 / (1 + color_variance)
            
            # 黒くて一様な線ほど高スコア
            black_line_score = (255 - blackness) / 255 * uniformity
            
            line_blackness.append((y, black_line_score))
        
        # 画像中央付近で最も黒い線を選択
        center_y = height // 2
        center_range = height // 3
        
        center_candidates = [(y, blackness) for y, blackness in line_blackness 
                           if center_y - center_range <= y <= center_y + center_range]
        
        if center_candidates:
            best_line = max(center_candidates, key=lambda x: x[1])
            return best_line[0]
        
        return None
    
    def crop_around_zero_line(self, image_path: str, 
                            above_pixels: int = 150, 
                            below_pixels: int = 150,
                            left_margin: int = 20,
                            right_margin: int = 20,
                            output_path: str = None) -> Tuple[bool, Optional[str]]:
        """
        0ラインを基準とした固定ピクセル範囲での切り抜き
        
        Args:
            image_path: 入力画像パス
            above_pixels: 0ラインより上のピクセル数
            below_pixels: 0ラインより下のピクセル数
            left_margin: 左余白
            right_margin: 右余白
            output_path: 出力パス（Noneの場合は自動生成）
        
        Returns:
            (成功フラグ, 出力パス)
        """
        try:
            self.log(f"0ライン基準切り抜き開始: {os.path.basename(image_path)}", "INFO")
            
            # 0ライン検出
            zero_line_y = self.detect_zero_line_enhanced(image_path)
            if zero_line_y is None:
                self.log("0ライン検出に失敗", "ERROR")
                return False, None
            
            # 画像読み込み
            img = Image.open(image_path)
            width, height = img.size
            
            # 切り抜き範囲計算
            top = max(0, zero_line_y - above_pixels)
            bottom = min(height, zero_line_y + below_pixels)
            left = max(0, left_margin)
            right = min(width, width - right_margin)
            
            # 切り抜き実行
            cropped_img = img.crop((left, top, right, bottom))
            
            # 出力パス設定
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_dir = "graphs/cropped_zero_line"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{base_name}_zero_line.png")
            
            # 保存
            cropped_img.save(output_path)
            
            # 結果情報
            cropped_width = right - left
            cropped_height = bottom - top
            
            self.log(f"切り抜き完了:", "SUCCESS")
            self.log(f"  0ライン位置: Y={zero_line_y}", "INFO")
            self.log(f"  切り抜き範囲: ({left}, {top}, {right}, {bottom})", "INFO")
            self.log(f"  切り抜きサイズ: {cropped_width} x {cropped_height}", "INFO")
            self.log(f"  出力ファイル: {output_path}", "INFO")
            
            # 0ラインの相対位置を計算
            zero_line_relative = above_pixels
            self.log(f"  切り抜き画像内0ライン: Y={zero_line_relative}", "INFO")
            
            return True, output_path
            
        except Exception as e:
            self.log(f"切り抜きエラー: {e}", "ERROR")
            return False, None
    
    def analyze_optimal_range(self, image_path: str) -> dict:
        """
        最適な切り抜き範囲を分析
        
        Returns:
            分析結果辞書
        """
        self.log("最適範囲分析を開始", "INFO")
        
        try:
            # 0ライン検出
            zero_line_y = self.detect_zero_line_enhanced(image_path)
            if zero_line_y is None:
                return {"error": "0ライン検出失敗"}
            
            img = Image.open(image_path)
            img_array = np.array(img)
            width, height = img_array.shape[:2]
            
            # グラフデータの上下範囲を分析
            # ピンク線またはブルー線を検出
            graph_pixels = self._detect_graph_data_range(img_array, zero_line_y)
            
            if graph_pixels:
                max_above = zero_line_y - min(graph_pixels)
                max_below = max(graph_pixels) - zero_line_y
                
                # 推奨範囲（データ範囲 + 余裕）
                recommended_above = max_above + 30
                recommended_below = max_below + 30
            else:
                # デフォルト推奨値
                recommended_above = 150
                recommended_below = 150
            
            analysis = {
                "zero_line_y": zero_line_y,
                "image_size": (width, height),
                "data_range_above": max_above if graph_pixels else None,
                "data_range_below": max_below if graph_pixels else None,
                "recommended_above": recommended_above,
                "recommended_below": recommended_below,
                "graph_data_detected": bool(graph_pixels)
            }
            
            self.log(f"最適範囲分析結果:", "SUCCESS")
            self.log(f"  推奨上: {recommended_above}px", "INFO")
            self.log(f"  推奨下: {recommended_below}px", "INFO")
            
            return analysis
            
        except Exception as e:
            self.log(f"分析エラー: {e}", "ERROR")
            return {"error": str(e)}
    
    def _detect_graph_data_range(self, img_array: np.ndarray, zero_line_y: int) -> list:
        """グラフデータ（ピンク線・ブルー線）の範囲を検出"""
        height, width = img_array.shape[:2]
        
        # ピンク線検出
        pink_pixels = self._detect_pink_pixels(img_array)
        
        # ブルー線検出
        blue_pixels = self._detect_blue_pixels(img_array)
        
        # 両方を統合
        all_graph_pixels = pink_pixels + blue_pixels
        
        if all_graph_pixels:
            y_coords = [y for x, y in all_graph_pixels]
            return y_coords
        
        return []
    
    def _detect_pink_pixels(self, img_array: np.ndarray) -> list:
        """ピンク線ピクセルを検出"""
        height, width = img_array.shape[:2]
        pink_colors = [(254, 23, 206), (255, 20, 147), (255, 105, 180)]  # #fe17ce, #ff1493, #ff69b4
        
        pink_pixels = []
        for color in pink_colors:
            target_rgb = np.array(color)
            reshaped = img_array.reshape(-1, 3)
            distances = np.sqrt(np.sum((reshaped - target_rgb) ** 2, axis=1))
            mask = distances <= 40
            
            y_coords, x_coords = np.divmod(np.where(mask)[0], width)
            pink_pixels.extend(list(zip(x_coords, y_coords)))
        
        return pink_pixels
    
    def _detect_blue_pixels(self, img_array: np.ndarray) -> list:
        """ブルー線ピクセルを検出"""
        height, width = img_array.shape[:2]
        blue_colors = [(0, 150, 255), (30, 144, 255), (135, 206, 250)]  # 各種ブルー
        
        blue_pixels = []
        for color in blue_colors:
            target_rgb = np.array(color)
            reshaped = img_array.reshape(-1, 3)
            distances = np.sqrt(np.sum((reshaped - target_rgb) ** 2, axis=1))
            mask = distances <= 40
            
            y_coords, x_coords = np.divmod(np.where(mask)[0], width)
            blue_pixels.extend(list(zip(x_coords, y_coords)))
        
        return blue_pixels
    
    def batch_process(self, input_folder: str = "graphs", 
                     above_pixels: int = 150, 
                     below_pixels: int = 150):
        """バッチ処理"""
        self.log("0ライン基準バッチ処理開始", "INFO")
        
        if not os.path.exists(input_folder):
            self.log(f"入力フォルダが見つかりません: {input_folder}", "ERROR")
            return
        
        # 対象画像ファイル
        image_files = [f for f in os.listdir(input_folder)
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                      and not f.endswith('_zero_line.png')]
        
        if not image_files:
            self.log("処理対象の画像ファイルが見つかりません", "ERROR")
            return
        
        self.log(f"処理対象: {len(image_files)}個のファイル", "INFO")
        
        successful = 0
        failed = []
        
        for i, filename in enumerate(image_files, 1):
            self.log(f"\n[{i}/{len(image_files)}] 処理中: {filename}", "INFO")
            
            input_path = os.path.join(input_folder, filename)
            success, output_path = self.crop_around_zero_line(input_path, above_pixels, below_pixels)
            
            if success:
                successful += 1
            else:
                failed.append(filename)
        
        # バッチ処理結果
        self.log(f"\n🎉 バッチ処理完了!", "SUCCESS")
        self.log(f"✅ 成功: {successful}/{len(image_files)}", "SUCCESS")
        
        if failed:
            self.log(f"❌ 失敗: {len(failed)}個", "ERROR")
            for f in failed:
                self.log(f"  - {f}", "ERROR")


def main():
    """メイン処理"""
    print("=" * 60)
    print("🎯 0ライン基準グラフ切り抜きツール")
    print("=" * 60)
    print("🎮 シンプルで高精度なアプローチ")
    print("📏 0ラインから固定ピクセル範囲で切り抜き")
    
    cropper = ZeroLineBasedCropper()
    
    # 入力フォルダチェック
    input_folder = "graphs"
    if not os.path.exists(input_folder):
        print(f"\n❌ 入力フォルダが見つかりません: {input_folder}")
        return
    
    # 画像ファイル検索
    image_files = [f for f in os.listdir(input_folder)
                  if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                  and not f.endswith('_zero_line.png')]
    
    if not image_files:
        print(f"\n❌ 処理対象の画像ファイルが見つかりません")
        return
    
    print(f"\n📁 見つかった画像ファイル ({len(image_files)}個):")
    for i, file in enumerate(image_files, 1):
        print(f"   {i}. {file}")
    
    # 処理モード選択
    print(f"\n🎯 処理モードを選択:")
    print("1. 🚀 デフォルト設定でバッチ処理（上下150px）")
    print("2. 📏 最適範囲を分析してからバッチ処理")
    print("3. 📷 単一画像で設定テスト")
    print("4. ⚙️ カスタム設定でバッチ処理")
    
    try:
        choice = input("\n選択 (1-4): ").strip()
        
        if choice == "1":
            # デフォルトバッチ処理
            cropper.batch_process(input_folder, 150, 150)
            
        elif choice == "2":
            # 最適範囲分析
            print("\n🔍 最適範囲を分析中...")
            
            # 最初の画像で分析
            sample_image = os.path.join(input_folder, image_files[0])
            analysis = cropper.analyze_optimal_range(sample_image)
            
            if "error" not in analysis:
                above = analysis["recommended_above"]
                below = analysis["recommended_below"]
                
                print(f"📊 分析結果（{image_files[0]}）:")
                print(f"   推奨上側: {above}px")
                print(f"   推奨下側: {below}px")
                
                proceed = input(f"\nこの設定でバッチ処理しますか？ (y/n): ").strip().lower()
                if proceed != 'n':
                    cropper.batch_process(input_folder, above, below)
            else:
                print(f"❌ 分析エラー: {analysis['error']}")
                
        elif choice == "3":
            # 単一画像テスト
            print(f"\n📁 画像を選択:")
            for i, file in enumerate(image_files, 1):
                print(f"{i}. {file}")
            
            try:
                file_num = int(input("画像番号を選択: "))
                if 1 <= file_num <= len(image_files):
                    selected_file = image_files[file_num - 1]
                    image_path = os.path.join(input_folder, selected_file)
                    
                    # 最適範囲分析
                    analysis = cropper.analyze_optimal_range(image_path)
                    
                    if "error" not in analysis:
                        print(f"\n📊 分析結果:")
                        print(f"   0ライン位置: Y={analysis['zero_line_y']}")
                        print(f"   推奨上側: {analysis['recommended_above']}px")
                        print(f"   推奨下側: {analysis['recommended_below']}px")
                        
                        # カスタム設定
                        above_input = input(f"上側ピクセル数 (推奨: {analysis['recommended_above']}): ").strip()
                        below_input = input(f"下側ピクセル数 (推奨: {analysis['recommended_below']}): ").strip()
                        
                        above = int(above_input) if above_input else analysis['recommended_above']
                        below = int(below_input) if below_input else analysis['recommended_below']
                        
                        # 切り抜き実行
                        success, output_path = cropper.crop_around_zero_line(image_path, above, below)
                        
                        if success:
                            print(f"\n✅ テスト完了: {output_path}")
                        else:
                            print(f"\n❌ テスト失敗")
                    else:
                        print(f"❌ 分析エラー: {analysis['error']}")
                else:
                    print("❌ 無効な番号です")
            except ValueError:
                print("❌ 数字を入力してください")
                
        elif choice == "4":
            # カスタム設定
            print(f"\n⚙️ カスタム設定:")
            
            above_input = input("0ラインより上のピクセル数 (デフォルト: 150): ").strip()
            below_input = input("0ラインより下のピクセル数 (デフォルト: 150): ").strip()
            
            above = int(above_input) if above_input else 150
            below = int(below_input) if below_input else 150
            
            print(f"\n📋 設定確認:")
            print(f"   上側: {above}px")
            print(f"   下側: {below}px")
            
            # バッチ処理実行
            cropper.batch_process(input_folder, above, below)
            
        else:
            print("❌ 無効な選択です")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 処理が中断されました")
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
    
    print(f"\n✨ 処理完了")


if __name__ == "__main__":
    main()