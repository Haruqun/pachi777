#!/usr/bin/env python3
"""
スマートグラフデータ抽出ツール（日本語対応版）
- OCRによる最大値自動検出
- ピクセル比率による正確な抽出
- ハードコーディングなし、完全自動化
- 日本語フォント対応
"""

from PIL import Image
import numpy as np
import pandas as pd
import os
from scipy import ndimage
import re
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️ pytesseract がインストールされていません")
    print("インストール方法: pip install pytesseract")


def setup_japanese_font():
    """
    日本語フォントの設定
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        
        # macOS用日本語フォント設定
        japanese_fonts = [
            'Hiragino Sans',           # macOS標準
            'Hiragino Kaku Gothic Pro', # macOS
            'Yu Gothic',               # Windows/macOS
            'Meiryo',                  # Windows
            'Takao PGothic',           # Linux
            'IPAexGothic',             # Linux
            'IPAPGothic',              # Linux
            'VL PGothic',              # Linux
            'Noto Sans CJK JP',        # Google Fonts
            'DejaVu Sans'              # フォールバック
        ]
        
        # 利用可能なフォントを検索
        available_fonts = [f.name for f in matplotlib.font_manager.fontManager.ttflist]
        
        for font in japanese_fonts:
            if font in available_fonts:
                plt.rcParams['font.family'] = font
                plt.rcParams['axes.unicode_minus'] = False
                print(f"✅ 日本語フォント設定: {font}")
                return True
        
        # フォールバック: システムのデフォルトフォント
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['axes.unicode_minus'] = False
        print("⚠️ 日本語フォントが見つかりません。デフォルトフォントを使用します。")
        return False
        
    except ImportError:
        print("⚠️ matplotlib がインストールされていません")
        return False


def hex_to_rgb(hex_color):
    """16進数カラーコードをRGBに変換"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def extract_max_value_from_graph(image_path):
    """
    OCRでグラフから最大値を抽出
    """
    if not OCR_AVAILABLE:
        print("⚠️ OCR機能が利用できません。手動で最大値を入力してください。")
        try:
            max_val = float(input("グラフの最大値を入力してください: "))
            return max_val
        except ValueError:
            return None
    
    print("OCRでグラフから最大値を読み取り中...")
    
    try:
        img = Image.open(image_path)
        
        # 画像の下部分に注目（最大値表示エリア）
        width, height = img.size
        bottom_area = img.crop((0, height * 0.7, width, height))  # 下30%
        
        # OCRでテキストを抽出
        text = pytesseract.image_to_string(bottom_area, lang='jpn+eng', config='--psm 6')
        print(f"OCRで抽出されたテキスト:\n{text}")
        
        # 「最大値：XXXX」「最高値：XXXX」パターンを検索
        max_patterns = [
            r'最大値[：:]\s*(\d{1,6})',
            r'最高値[：:]\s*(\d{1,6})',
            r'max[：:]\s*(\d{1,6})',
            r'MAX[：:]\s*(\d{1,6})',
            r'最大[：:]\s*(\d{1,6})'
        ]
        
        for pattern in max_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                max_val = float(matches[0])
                print(f"✅ 最大値を検出: {max_val}")
                return max_val
        
        # パターンが見つからない場合、数値のみを検索
        numbers = re.findall(r'\d{3,6}', text)  # 3-6桁の数値
        valid_numbers = []
        for num_str in numbers:
            num = float(num_str)
            if 100 <= num <= 100000:  # 現実的な範囲
                valid_numbers.append(num)
        
        if valid_numbers:
            # 最も可能性の高い値を選択
            max_val = max(valid_numbers)
            print(f"✅ 推定最大値: {max_val}")
            return max_val
        
        print("⚠️ OCRで最大値を自動検出できませんでした")
        return None
        
    except Exception as e:
        print(f"OCRエラー: {e}")
        return None


def detect_pink_line_accurate(image_path, tolerance=40):
    """
    高精度ピンク線検出
    """
    print(f"ピンク線を検出中: {os.path.basename(image_path)}")
    
    img = Image.open(image_path)
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    
    # メインのピンク色（画像から確認済み）
    target_color = "#fe17ce"
    target_rgb = np.array(hex_to_rgb(target_color))
    
    # 色距離計算
    reshaped = img_array[:, :, :3].reshape(-1, 3).astype(np.float64)
    distances = np.sqrt(np.sum((reshaped - target_rgb) ** 2, axis=1))
    mask = distances <= tolerance
    mask_2d = mask.reshape(height, width)
    
    # 追加のピンク系も検出
    additional_pinks = ["#ff1493", "#ff69b4", "#e91e63"]
    for color in additional_pinks:
        additional_rgb = np.array(hex_to_rgb(color))
        distances = np.sqrt(np.sum((reshaped - additional_rgb) ** 2, axis=1))
        additional_mask = distances <= tolerance
        additional_mask_2d = additional_mask.reshape(height, width)
        mask_2d = mask_2d | additional_mask_2d
    
    # ノイズ除去とクリーニング
    cleaned_mask = ndimage.binary_opening(mask_2d, structure=np.ones((2,2)))
    cleaned_mask = ndimage.binary_closing(cleaned_mask, structure=np.ones((3,3)))
    
    pixel_count = np.sum(cleaned_mask)
    print(f"検出されたピンクピクセル数: {pixel_count}")
    
    return cleaned_mask if pixel_count >= 50 else None


def extract_data_points_precise(mask):
    """
    高精度データポイント抽出
    """
    height, width = mask.shape
    data_points = []
    
    for x in range(width):
        column = mask[:, x]
        y_coords = np.where(column)[0]
        
        if len(y_coords) > 0:
            if len(y_coords) == 1:
                y = y_coords[0]
            else:
                # 複数の点がある場合は中央値を使用（ノイズに強い）
                y = int(np.median(y_coords))
            
            data_points.append((x, y))
    
    print(f"抽出されたデータポイント数: {len(data_points)}")
    return data_points


def detect_zero_line_smart(image_path):
    """
    スマートゼロライン検出
    """
    print("ゼロライン（基準線）を検出中...")
    
    img = Image.open(image_path)
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    
    # グレースケール変換
    gray = np.mean(img_array[:, :, :3], axis=2)
    
    # 水平線のスコアを計算
    line_scores = []
    
    for y in range(height):
        row = gray[y, :]
        
        # 水平線の特徴を評価
        mean_val = np.mean(row)
        min_val = np.min(row)
        std_val = np.std(row)
        
        # 暗い線ほど高スコア
        darkness_score = (255 - mean_val) / 255
        
        # 一様性スコア（標準偏差が小さいほど高スコア）
        uniformity_score = 1 / (1 + std_val)
        
        # 最小値の暗さ
        min_darkness_score = (255 - min_val) / 255
        
        # 総合スコア
        total_score = darkness_score * 0.4 + uniformity_score * 0.3 + min_darkness_score * 0.3
        
        line_scores.append((y, total_score, mean_val))
    
    # 最高スコアの線を選択（ただし画像の中央付近を優先）
    center_y = height // 2
    best_lines = sorted(line_scores, key=lambda x: x[1], reverse=True)[:5]
    
    # 中央付近の線を優先選択
    center_lines = [line for line in best_lines if abs(line[0] - center_y) < height * 0.3]
    
    if center_lines:
        zero_line = center_lines[0]
    else:
        zero_line = best_lines[0]
    
    zero_y, score, mean_color = zero_line
    print(f"✅ ゼロライン検出: y={zero_y} (スコア={score:.3f}, 平均色={mean_color:.1f})")
    
    return zero_y


def convert_with_pixel_ratio(points, zero_line_y, max_value):
    """
    ピクセル比率による正確な座標変換
    """
    if not points or max_value is None:
        return []
    
    print(f"ピクセル比率で座標変換中...")
    print(f"基準最大値: {max_value}")
    print(f"ゼロライン位置: y={zero_line_y}")
    
    # データポイントの範囲を分析
    y_coords = [p[1] for p in points]
    graph_top = min(y_coords)      # グラフの最高点
    graph_bottom = max(y_coords)   # グラフの最低点
    
    print(f"グラフの実際の範囲: y={graph_top} 〜 {graph_bottom}")
    
    # ゼロラインからの距離を計算
    up_distance = zero_line_y - graph_top      # 上方向の最大距離
    down_distance = graph_bottom - zero_line_y  # 下方向の最大距離
    
    print(f"上方向距離: {up_distance}px")
    print(f"下方向距離: {down_distance}px")
    print(f"上下比率: 1:{down_distance/up_distance:.2f}")
    
    # 比率から下限値を推定
    if up_distance > 0:
        estimated_min = -max_value * (down_distance / up_distance)
    else:
        estimated_min = -max_value  # フォールバック
    
    print(f"推定最小値: {estimated_min:.0f}")
    
    # 座標変換
    converted_points = []
    
    for x_pixel, y_pixel in points:
        distance_from_zero = y_pixel - zero_line_y
        
        if distance_from_zero <= 0:  # ゼロラインより上（プラス値）
            if up_distance > 0:
                ratio = abs(distance_from_zero) / up_distance
                value = ratio * max_value
            else:
                value = 0
        else:  # ゼロラインより下（マイナス値）
            if down_distance > 0:
                ratio = distance_from_zero / down_distance
                value = ratio * estimated_min
            else:
                value = 0
        
        converted_points.append((x_pixel, int(value)))
    
    return converted_points


def plot_comparison(image_path, points, converted_points, zero_line_y, max_value):
    """
    元画像と抽出結果の比較可視化（日本語対応）
    """
    try:
        import matplotlib.pyplot as plt
        
        # 日本語フォント設定
        font_success = setup_japanese_font()
        
        print("📊 比較グラフを作成中...")
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # タイトル設定（フォントによって切り替え）
        if font_success:
            fig.suptitle('スマートグラフ抽出結果 - 形状比較', fontsize=16, fontweight='bold')
            titles = [
                '1. 元のグラフ画像',
                '2. 検出結果（画像座標）',
                '3. 抽出データ（実際の値）',
                '4. 正規化された形状（0-1）'
            ]
            labels = {
                'detected_line': '検出されたライン',
                'zero_line': 'ゼロライン',
                'extracted_data': '抽出データ',
                'max_value': f'最大値: {max_value}',
                'normalized_shape': '正規化された形状',
                'x_coord': 'X座標（ピクセル）',
                'y_value': 'Y値',
                'x_pos_norm': 'X位置（正規化）',
                'y_pos_norm': 'Y位置（正規化）'
            }
        else:
            fig.suptitle('Smart Graph Extraction Results - Shape Comparison', fontsize=16, fontweight='bold')
            titles = [
                '1. Original Graph Image',
                '2. Detection Results (Image Coordinates)',
                '3. Extracted Data (Real Values)',
                '4. Normalized Shape (0-1)'
            ]
            labels = {
                'detected_line': 'Detected Line',
                'zero_line': 'Zero Line',
                'extracted_data': 'Extracted Data',
                'max_value': f'Max Value: {max_value}',
                'normalized_shape': 'Normalized Shape',
                'x_coord': 'X Coordinate (pixels)',
                'y_value': 'Y Value',
                'x_pos_norm': 'X Position (normalized)',
                'y_pos_norm': 'Y Position (normalized)'
            }
        
        # 1. 元画像
        img = Image.open(image_path)
        axes[0, 0].imshow(img)
        axes[0, 0].set_title(titles[0], fontsize=12, fontweight='bold')
        axes[0, 0].axis('off')
        
        # 2. 検出結果オーバーレイ
        axes[0, 1].imshow(img)
        if points:
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            axes[0, 1].plot(x_coords, y_coords, 'red', linewidth=3, alpha=0.8, label=labels['detected_line'])
            axes[0, 1].axhline(y=zero_line_y, color='green', linestyle='--', linewidth=2, alpha=0.8, label=labels['zero_line'])
        axes[0, 1].set_title(titles[1], fontsize=12, fontweight='bold')
        axes[0, 1].legend()
        axes[0, 1].axis('off')
        
        # 3. 抽出されたデータ（実値）
        if converted_points:
            x_values = [p[0] for p in converted_points]
            y_values = [p[1] for p in converted_points]
            axes[1, 0].plot(x_values, y_values, 'blue', linewidth=2, label=labels['extracted_data'])
            axes[1, 0].axhline(y=0, color='green', linestyle='--', linewidth=1, alpha=0.7, label=labels['zero_line'])
            axes[1, 0].axhline(y=max_value, color='red', linestyle='--', linewidth=1, alpha=0.7, label=labels['max_value'])
            axes[1, 0].set_title(titles[2], fontsize=12, fontweight='bold')
            axes[1, 0].set_xlabel(labels['x_coord'])
            axes[1, 0].set_ylabel(labels['y_value'])
            axes[1, 0].grid(True, alpha=0.3)
            axes[1, 0].legend()
        
        # 4. 正規化された形状比較
        if converted_points:
            # X軸を0-1に正規化
            x_normalized = [(x - min(x_values)) / (max(x_values) - min(x_values)) for x in x_values]
            # Y軸も見やすいように正規化
            y_min, y_max = min(y_values), max(y_values)
            y_normalized = [(y - y_min) / (y_max - y_min) for y in y_values]
            
            axes[1, 1].plot(x_normalized, y_normalized, 'purple', linewidth=2, label=labels['normalized_shape'])
            axes[1, 1].set_title(titles[3], fontsize=12, fontweight='bold')
            axes[1, 1].set_xlabel(labels['x_pos_norm'])
            axes[1, 1].set_ylabel(labels['y_pos_norm'])
            axes[1, 1].grid(True, alpha=0.3)
            axes[1, 1].legend()
        
        plt.tight_layout()
        
        # 保存
        output_path = os.path.splitext(image_path)[0] + '_comparison.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"📊 比較グラフを保存: {output_path}")
        
        # 表示
        plt.show()
        
    except ImportError:
        print("⚠️ matplotlib がインストールされていません")
        print("インストール方法: pip install matplotlib")
    except Exception as e:
        print(f"可視化エラー: {e}")


def analyze_graph_smart(image_path, save_csv=True, show_plot=True):
    """
    スマートグラフ分析（OCR + ピクセル比率）+ 可視化
    """
    print(f"=== スマートグラフ分析開始: {os.path.basename(image_path)} ===")
    
    try:
        # 1. OCRで最大値を抽出
        max_value = extract_max_value_from_graph(image_path)
        if max_value is None:
            print("❌ 最大値の取得に失敗しました")
            return None
        
        # 2. ピンク線検出
        mask = detect_pink_line_accurate(image_path)
        if mask is None:
            print("❌ ピンク線の検出に失敗しました")
            return None
        
        # 3. データポイント抽出
        points = extract_data_points_precise(mask)
        if not points:
            print("❌ データポイントの抽出に失敗しました")
            return None
        
        # 4. ゼロライン検出
        zero_line_y = detect_zero_line_smart(image_path)
        
        # 5. ピクセル比率による座標変換
        converted_points = convert_with_pixel_ratio(points, zero_line_y, max_value)
        
        if not converted_points:
            print("❌ 座標変換に失敗しました")
            return None
        
        # 6. DataFrame作成
        df = pd.DataFrame(converted_points, columns=['x_pixel', 'y_value'])
        
        # X座標を正規化
        if df['x_pixel'].max() > df['x_pixel'].min():
            df['x_normalized'] = (df['x_pixel'] - df['x_pixel'].min()) / (df['x_pixel'].max() - df['x_pixel'].min())
        else:
            df['x_normalized'] = 0
        
        # 統計情報表示
        print(f"\n✅ データ抽出完了:")
        print(f"   ポイント数: {len(df)}")
        print(f"   Y値範囲: {df['y_value'].min()} 〜 {df['y_value'].max()}")
        print(f"   平均値: {df['y_value'].mean():.0f}")
        print(f"   基準最大値: {max_value}")
        print(f"   抽出最大値: {df['y_value'].max()}")
        print(f"   精度: {(df['y_value'].max() / max_value * 100):.1f}%")
        
        # 7. 可視化
        if show_plot:
            plot_comparison(image_path, points, converted_points, zero_line_y, max_value)
        
        # 8. CSV保存
        if save_csv:
            csv_path = os.path.splitext(image_path)[0] + '_smart.csv'
            df.to_csv(csv_path, index=False)
            print(f"\n💾 CSV保存: {csv_path}")
        
        return df
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None


if __name__ == "__main__":
    print("=== スマートグラフデータ抽出ツール（日本語対応版） ===")
    print("OCR + ピクセル比率による正確な抽出 + 形状比較可視化")
    
    # 画像ファイルを探す
    folder = "graphs/cropped_auto"
    if os.path.exists(folder):
        files = [f for f in os.listdir(folder) 
                if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if files:
            print(f"\n📁 {folder} 内の画像:")
            for i, file in enumerate(files, 1):
                print(f"{i}. {file}")
            
            try:
                file_num = int(input("画像番号を選択: "))
                if 1 <= file_num <= len(files):
                    selected_file = files[file_num - 1]
                    image_path = os.path.join(folder, selected_file)
                    
                    # 可視化オプション
                    show_plot = input("比較グラフを表示しますか？ (y/n, デフォルト: y): ").strip().lower()
                    show_plot = show_plot != 'n'
                    
                    analyze_graph_smart(image_path, show_plot=show_plot)
                else:
                    print("❌ 無効な番号です")
            except ValueError:
                print("❌ 数字を入力してください")
        else:
            print(f"❌ {folder} に画像がありません")
    else:
        print("❌ フォルダが見つかりません")
    
    print("\n✨ 完了！")