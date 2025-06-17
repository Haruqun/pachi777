#!/usr/bin/env python3
"""
グラフ最終値の読み取り精度を分析
"""

import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import pandas as pd

def analyze_graph_end_region(image_path, boundaries):
    """グラフ終端領域の詳細分析"""
    # 画像読み込み
    img = Image.open(image_path)
    img_array = np.array(img)
    
    # 終端領域を拡大表示
    end_region_start = boundaries["end_x"] - 100
    end_region = img_array[:, end_region_start:boundaries["end_x"]+20]
    
    # BGR変換とHSV変換
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    # グラフ領域内でのライン検出
    graph_region = img_hsv[boundaries["top_y"]:boundaries["bottom_y"], 
                          end_region_start:boundaries["end_x"]+20]
    
    return img_array, end_region, graph_region

def detect_line_in_final_region(img_hsv, color_ranges):
    """最終領域でのライン検出"""
    results = {}
    
    for color_name, (lower, upper) in color_ranges.items():
        lower = np.array(lower)
        upper = np.array(upper)
        mask = cv2.inRange(img_hsv, lower, upper)
        
        # 各列でのライン検出
        column_detections = []
        for x in range(mask.shape[1]):
            column = mask[:, x]
            y_indices = np.where(column > 0)[0]
            if len(y_indices) > 0:
                column_detections.append({
                    'x': x,
                    'y_indices': y_indices,
                    'y_mean': np.mean(y_indices),
                    'y_count': len(y_indices)
                })
        
        results[color_name] = column_detections
    
    return results

def visualize_end_region_analysis(image_path, boundaries):
    """終端領域の詳細な可視化"""
    # 設定
    end_margin = 50  # 終端から内側への余白
    
    # 画像読み込み
    img = Image.open(image_path)
    img_array = np.array(img)
    
    # BGR/HSV変換
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    # 色範囲定義
    color_ranges = {
        "pink": [(140, 30, 30), (170, 255, 255)],
        "blue": [(90, 30, 30), (120, 255, 255)],
    }
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle(f'Final Value Region Analysis: {os.path.basename(image_path)}', fontsize=16)
    
    # 1. 元画像の終端領域
    ax = axes[0, 0]
    end_start = boundaries["end_x"] - end_margin
    end_region = img_array[:, end_start:]
    ax.imshow(end_region)
    ax.axvline(x=boundaries["end_x"] - end_start, color='red', linestyle='--', label='Graph End')
    ax.set_title('Original End Region')
    ax.legend()
    
    # 2. HSV色相チャンネル
    ax = axes[0, 1]
    hsv_end = img_hsv[:, end_start:]
    ax.imshow(hsv_end[:, :, 0], cmap='hsv')
    ax.set_title('HSV Hue Channel')
    ax.axvline(x=boundaries["end_x"] - end_start, color='white', linestyle='--')
    
    # 3. エッジ検出結果
    ax = axes[0, 2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray[:, end_start:], 30, 100)
    ax.imshow(edges, cmap='gray')
    ax.set_title('Edge Detection')
    ax.axvline(x=boundaries["end_x"] - end_start, color='red', linestyle='--')
    
    # 4. 色マスク（ピンク）
    ax = axes[1, 0]
    lower_pink = np.array([140, 30, 30])
    upper_pink = np.array([170, 255, 255])
    mask_pink = cv2.inRange(img_hsv[:, end_start:], lower_pink, upper_pink)
    ax.imshow(mask_pink, cmap='gray')
    ax.set_title('Pink Mask')
    ax.axvline(x=boundaries["end_x"] - end_start, color='red', linestyle='--')
    
    # 5. 色マスク（青）
    ax = axes[1, 1]
    lower_blue = np.array([90, 30, 30])
    upper_blue = np.array([120, 255, 255])
    mask_blue = cv2.inRange(img_hsv[:, end_start:], lower_blue, upper_blue)
    ax.imshow(mask_blue, cmap='gray')
    ax.set_title('Blue Mask')
    ax.axvline(x=boundaries["end_x"] - end_start, color='red', linestyle='--')
    
    # 6. ライン検出プロファイル
    ax = axes[1, 2]
    
    # グラフ領域内でのライン検出
    graph_region = img_hsv[boundaries["top_y"]:boundaries["bottom_y"], end_start:]
    
    # 各X座標でのライン検出強度
    detection_profiles = []
    x_positions = []
    
    for x in range(graph_region.shape[1]):
        # ピンクマスク
        column_pink = mask_pink[boundaries["top_y"]:boundaries["bottom_y"], x]
        # 青マスク
        column_blue = mask_blue[boundaries["top_y"]:boundaries["bottom_y"], x]
        
        # 検出強度（検出ピクセル数）
        pink_strength = np.sum(column_pink > 0)
        blue_strength = np.sum(column_blue > 0)
        
        detection_profiles.append(max(pink_strength, blue_strength))
        x_positions.append(x + end_start)
    
    ax.plot(x_positions, detection_profiles, 'b-', linewidth=2)
    ax.axvline(x=boundaries["end_x"], color='red', linestyle='--', label='Graph End')
    ax.set_xlabel('X Position')
    ax.set_ylabel('Detection Strength')
    ax.set_title('Line Detection Profile')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    return fig

def analyze_final_values_accuracy():
    """すべての画像の最終値精度を分析"""
    # 境界値設定
    boundaries = {
        "start_x": 36,
        "end_x": 620,
        "top_y": 29,
        "bottom_y": 520,
        "zero_y": 274
    }
    
    # 入力フォルダ
    input_folder = "graphs/cropped"
    data_folder = "graphs/advanced_extracted_data"
    
    # 分析結果
    results = []
    
    # 画像ファイルを処理
    image_files = [f for f in os.listdir(input_folder) if f.endswith('.png')]
    
    for image_file in sorted(image_files):
        image_path = os.path.join(input_folder, image_file)
        base_name = os.path.splitext(image_file)[0]
        
        # CSVファイルの読み込み
        csv_path = os.path.join(data_folder, f"{base_name}_data.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if len(df) > 0:
                # 最終値のX座標とY座標
                last_x = df.iloc[-1]['x']  # x座標
                last_y = df.iloc[-1]['y']  # y座標
                last_value = df.iloc[-1]['value']  # 値
                
                # 理論的な最終X座標との差
                x_diff = boundaries["end_x"] - last_x
                
                results.append({
                    'image': image_file,
                    'last_x': last_x,
                    'last_y': last_y,
                    'last_value': last_value,
                    'x_diff_from_end': x_diff,
                    'data_points': len(df)
                })
    
    # 結果をDataFrameに変換
    results_df = pd.DataFrame(results)
    
    # 統計情報
    print("=== 最終値読み取り精度分析 ===")
    print(f"\n分析画像数: {len(results_df)}")
    print(f"\n最終X座標の統計:")
    print(f"  平均: {results_df['last_x'].mean():.2f}")
    print(f"  標準偏差: {results_df['last_x'].std():.2f}")
    print(f"  最小: {results_df['last_x'].min():.2f}")
    print(f"  最大: {results_df['last_x'].max():.2f}")
    print(f"\n終端からの距離:")
    print(f"  平均: {results_df['x_diff_from_end'].mean():.2f} ピクセル")
    print(f"  標準偏差: {results_df['x_diff_from_end'].std():.2f}")
    print(f"  最大: {results_df['x_diff_from_end'].max():.2f}")
    
    # 最も終端から離れている画像
    worst_cases = results_df.nlargest(3, 'x_diff_from_end')
    print(f"\n終端から最も離れている画像:")
    for _, row in worst_cases.iterrows():
        print(f"  {row['image']}: {row['x_diff_from_end']:.0f}ピクセル離れている")
    
    return results_df

def main():
    """メイン処理"""
    # 境界値設定
    boundaries = {
        "start_x": 36,
        "end_x": 620,
        "top_y": 29,
        "bottom_y": 520,
        "zero_y": 274
    }
    
    # 1. 全体的な精度分析
    results_df = analyze_final_values_accuracy()
    
    # 2. 問題のある画像の詳細分析
    worst_cases = results_df.nlargest(3, 'x_diff_from_end')
    
    print("\n=== 詳細分析 ===")
    for _, row in worst_cases.iterrows():
        image_path = os.path.join("graphs/cropped", row['image'])
        print(f"\n分析中: {row['image']}")
        
        # 終端領域の可視化
        fig = visualize_end_region_analysis(image_path, boundaries)
        output_path = f"final_value_analysis_{os.path.splitext(row['image'])[0]}.png"
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  分析画像を保存: {output_path}")
        plt.close(fig)
    
    # 3. 改善案の提示
    print("\n=== 改善案 ===")
    print("1. エッジ領域の特別処理:")
    print("   - 最後の20-30ピクセルで検出感度を上げる")
    print("   - エッジ検出と色検出の組み合わせを強化")
    print("\n2. 外挿法の活用:")
    print("   - 最後の有効データポイントから線形/多項式外挿")
    print("   - グラフの傾向を考慮した予測")
    print("\n3. 後処理の改善:")
    print("   - 終端付近のデータ点を重点的に保護")
    print("   - スムージング時の終端保護を強化")

if __name__ == "__main__":
    main()