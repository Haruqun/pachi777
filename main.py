import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from glob import glob
import base64
import requests
import json
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# Claude API設定
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

# === 日本語フォント設定（macOS対応） ===
import matplotlib
matplotlib.rcParams['font.family'] = ['Hiragino Sans', 'Arial Unicode MS', 'DejaVu Sans']
# フォント警告を抑制
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.font_manager')

def detect_graph_area_adaptive(img):
    """適応的なグラフ領域検出"""
    h, w, _ = img.shape
    print(f"画像サイズ: {w} x {h}")
    
    # 複数の候補領域を試す
    roi_candidates = [
        # 標準的なパチンコ台レイアウト
        {'x1': int(w * 0.1), 'y1': int(h * 0.35), 'x2': int(w * 0.9), 'y2': int(h * 0.85)},
        # より広い範囲
        {'x1': int(w * 0.05), 'y1': int(h * 0.3), 'x2': int(w * 0.95), 'y2': int(h * 0.9)},
        # 中央寄り
        {'x1': int(w * 0.15), 'y1': int(h * 0.4), 'x2': int(w * 0.85), 'y2': int(h * 0.8)},
    ]
    
    best_roi = None
    max_line_points = 0
    
    for i, roi in enumerate(roi_candidates):
        print(f"ROI候補 {i+1}: ({roi['x1']}, {roi['y1']}) - ({roi['x2']}, {roi['y2']})")
        test_roi = img[roi['y1']:roi['y2'], roi['x1']:roi['x2']]
        
        # ピンク線検出テスト
        points = detect_pink_line_multi_method(test_roi)
        if points is not None:
            point_count = len(points)
            print(f"  検出ポイント数: {point_count}")
            
            if point_count > max_line_points and point_count > 100:
                max_line_points = point_count
                best_roi = roi
                print(f"  ✅ 最適ROI更新: {point_count}ポイント")
        else:
            print(f"  ❌ ピンク線未検出")
    
    if best_roi:
        print(f"✅ 最適ROI選択: {max_line_points}ポイント")
        return best_roi
    else:
        # フォールバック: 標準ROI
        print("⚠️ フォールバック: 標準ROI使用")
        return roi_candidates[0]

def detect_pink_line_multi_method(roi):
    """複数手法でピンク線を検出"""
    if roi is None or roi.size == 0:
        return None
    
    # 方法1: HSV色空間での厳密な色検出
    points_hsv = detect_pink_hsv(roi)
    
    # 方法2: RGB色空間での検出
    points_rgb = detect_pink_rgb(roi)
    
    # 方法3: LAB色空間での検出
    points_lab = detect_pink_lab(roi)
    
    # 最も多くポイントを検出した方法を採用
    candidates = [
        (points_hsv, "HSV"),
        (points_rgb, "RGB"), 
        (points_lab, "LAB")
    ]
    
    best_points = None
    max_count = 0
    best_method = ""
    
    for points, method in candidates:
        if points is not None:
            count = len(points)
            print(f"  {method}方式: {count}ポイント")
            if count > max_count and count > 50:
                max_count = count
                best_points = points
                best_method = method
    
    if best_points is not None:
        print(f"  ✅ {best_method}方式採用: {max_count}ポイント")
        return best_points
    
    print(f"  ❌ 全方式でピンク線検出失敗")
    return None

def detect_pink_hsv(roi):
    """HSV色空間でピンク線検出"""
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    
    # #fb59d6 のHSV値: H=314°→157, S=65%→166, V=98%→250
    target_h, target_s, target_v = 157, 166, 250
    
    # 複数の検出範囲
    ranges = [
        (np.array([target_h-8, target_s-30, target_v-40]), 
         np.array([target_h+8, target_s+30, target_v+5])),
        (np.array([target_h-15, target_s-50, target_v-60]), 
         np.array([target_h+15, target_s+50, target_v+5])),
    ]
    
    for lower, upper in ranges:
        mask = cv2.inRange(hsv, lower, upper)
        
        # ノイズ除去
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        points = cv2.findNonZero(mask)
        if points is not None and len(points) > 100:
            return points.squeeze()
    
    return None

def detect_pink_rgb(roi):
    """RGB色空間でピンク線検出"""
    # #fb59d6 = RGB(251, 89, 214)
    target_rgb = np.array([214, 89, 251])  # BGR順序
    
    # 色距離による検出
    color_diff = np.linalg.norm(roi - target_rgb, axis=2)
    
    # 閾値を段階的に緩める
    thresholds = [30, 50, 80]
    
    for threshold in thresholds:
        mask = (color_diff < threshold).astype(np.uint8) * 255
        
        # ノイズ除去
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        points = cv2.findNonZero(mask)
        if points is not None and len(points) > 100:
            return points.squeeze()
    
    return None

def detect_pink_lab(roi):
    """LAB色空間でピンク線検出"""
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    
    # #fb59d6のLAB値を基準に範囲設定
    # 概算: L=70, A=50, B=-20
    lower_lab = np.array([40, 30, -40])
    upper_lab = np.array([90, 80, 10])
    
    mask = cv2.inRange(lab, lower_lab, upper_lab)
    
    # ノイズ除去
    kernel = np.ones((2, 2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    points = cv2.findNonZero(mask)
    if points is not None and len(points) > 100:
        return points.squeeze()
    
    return None

def detect_zero_line_enhanced(roi):
    """強化されたゼロライン検出"""
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    
    print("🎯 強化ゼロライン検出開始...")
    
    # 方法1: 改良版エッジ検出
    candidates_edge = detect_zero_line_by_edges(gray, w, h)
    
    # 方法2: 色分析による検出
    candidates_color = detect_zero_line_by_color(roi, w, h)
    
    # 方法3: テンプレートマッチング（水平線）
    candidates_template = detect_zero_line_by_template(gray, w, h)
    
    # 全候補を統合
    all_candidates = candidates_edge + candidates_color + candidates_template
    
    if all_candidates:
        # 中央付近（h//3 から 2*h//3）の候補を優先
        center_candidates = [
            cand for cand in all_candidates 
            if h//3 <= cand[0] <= 2*h//3
        ]
        
        if center_candidates:
            # 最も信頼性の高い候補を選択（長さ×中央度）
            best = max(center_candidates, key=lambda x: x[1] * (1 - abs(x[0] - h//2) / (h//2)))
            zero_y = best[0]
            print(f"✅ 中央領域ゼロライン: Y={zero_y}, 信頼度={best[1]}")
        else:
            # 最も長い線を選択
            best = max(all_candidates, key=lambda x: x[1])
            zero_y = best[0]
            print(f"✅ 最長ゼロライン: Y={zero_y}, 長さ={best[1]}")
    else:
        # フォールバック
        zero_y = h // 2
        print(f"❌ ゼロライン検出失敗、中央使用: Y={zero_y}")
    
    return zero_y

def detect_zero_line_by_edges(gray, w, h):
    """エッジ検出によるゼロライン候補"""
    candidates = []
    
    # 複数のエッジ検出パラメータ
    edge_params = [
        (30, 100, 80),  # (low, high, threshold)
        (50, 150, 60),
        (20, 80, 100)
    ]
    
    for low, high, threshold in edge_params:
        edges = cv2.Canny(gray, low, high, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=threshold,
                               minLineLength=w//3, maxLineGap=30)
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if abs(y2 - y1) <= 3 and abs(x2 - x1) > w//3:  # 水平線判定
                    avg_y = (y1 + y2) // 2
                    line_length = abs(x2 - x1)
                    candidates.append((avg_y, line_length))
    
    return candidates

def detect_zero_line_by_color(roi, w, h):
    """色分析によるゼロライン候補"""
    candidates = []
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    
    # 黒〜グレー系の色検出
    color_ranges = [
        (np.array([0, 0, 0]), np.array([180, 30, 80])),      # 黒
        (np.array([0, 0, 80]), np.array([180, 30, 160])),    # ダークグレー
        (np.array([0, 0, 160]), np.array([180, 30, 220])),   # ライトグレー
    ]
    
    for lower, upper in color_ranges:
        mask = cv2.inRange(hsv, lower, upper)
        
        # 水平線強調
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w//4, 1))
        horizontal_lines = cv2.morphologyEx(mask, cv2.MORPH_OPEN, horizontal_kernel)
        
        contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w_cont, h_cont = cv2.boundingRect(contour)
            if w_cont > w//4 and h_cont < 8:  # 十分長く、薄い
                center_y = y + h_cont // 2
                candidates.append((center_y, w_cont))
    
    return candidates

def detect_zero_line_by_template(gray, w, h):
    """テンプレートマッチングによるゼロライン検出"""
    candidates = []
    
    # 水平線テンプレート作成
    template_widths = [w//6, w//4, w//3]
    
    for template_w in template_widths:
        template = np.zeros((3, template_w), dtype=np.uint8)
        template[1, :] = 255  # 中央に白線
        
        # テンプレートマッチング
        result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        
        # 閾値以上の場所を検出
        locations = np.where(result >= 0.3)
        
        for y, x in zip(locations[0], locations[1]):
            candidates.append((y + 1, template_w))  # テンプレート中央のY座標
    
    return candidates

def extract_graph_data_enhanced(image_path, claude_data):
    """強化されたグラフデータ抽出（参考値による二点校正版）"""
    img = cv2.imread(image_path)
    h, w, _ = img.shape
    filename = os.path.basename(image_path)
    
    print(f"\n--- {filename} の強化解析 ---")
    print(f"画像サイズ: {w} x {h}")
    
    # 1. 適応的ROI検出
    roi_coords = detect_graph_area_adaptive(img)
    roi = img[roi_coords['y1']:roi_coords['y2'], roi_coords['x1']:roi_coords['x2']]
    roi_h, roi_w = roi.shape[:2]
    
    print(f"✅ 選択されたROI: ({roi_coords['x1']}, {roi_coords['y1']}) - ({roi_coords['x2']}, {roi_coords['y2']})")
    print(f"ROIサイズ: {roi_w} x {roi_h}")
    
    # 2. 多方式ピンク線検出
    print("🔍 多方式ピンク線検出開始...")
    points = detect_pink_line_multi_method(roi)
    
    if points is None:
        print("❌ ピンク線検出失敗")
        return None, None, None
    
    # 点群の整理
    if len(points.shape) == 1:
        points = points.reshape(1, -1)
    
    # X座標でソート
    points = sorted(points, key=lambda p: p[0])
    
    # サンプリング（パフォーマンス向上）
    if len(points) > 3000:
        step = len(points) // 3000
        points = points[::step]
    
    x_vals = [p[0] for p in points]
    y_vals = [p[1] for p in points]
    
    print(f"✅ 最終検出ポイント数: {len(points)}")
    print(f"Y値範囲: {min(y_vals)} - {max(y_vals)} (ROI内)")
    
    # 3. 二点校正による正確なスケーリング
    claude_max = claude_data.get('max_value') if claude_data else None
    reference_final = -17964  # 参考最終値
    
    # ピクセル座標の特定
    highest_y = min(y_vals)  # 最大値位置（Y座標が最小）
    final_y = y_vals[-1]     # 最終値位置
    
    print(f"\n🎯 二点校正スケーリング:")
    print(f"   Claude最大値: {claude_max}発")
    print(f"   参考最終値: {reference_final}発")
    print(f"   ピンク線最高点Y: {highest_y}")
    print(f"   ピンク線最終点Y: {final_y}")
    
    if claude_max and claude_max > 0:
        # 二点から線形変換パラメータを計算
        # highest_y → claude_max
        # final_y → reference_final
        
        pixel_diff = final_y - highest_y  # ピクセル差
        value_diff = reference_final - claude_max  # 値差
        
        if pixel_diff != 0:
            # ピクセル/玉の比率
            px_per_ball = pixel_diff / value_diff
            
            # ゼロライン位置（最高点からの逆算）
            zero_line_y = highest_y + claude_max * px_per_ball
            
            print(f"   ピクセル差: {pixel_diff}px")
            print(f"   値差: {value_diff}発")
            print(f"   ピクセル/玉: {px_per_ball:.6f}")
            print(f"   計算ゼロライン: Y={zero_line_y:.1f}")
            
            # 座標変換（ゼロライン基準）
            y_normalized = [-(y - zero_line_y) / px_per_ball for y in y_vals]
            x_normalized = [(x - min(x_vals)) / (max(x_vals) - min(x_vals)) * 100 for x in x_vals]
            
            # 開始点を0に調整
            start_offset = y_normalized[0]
            y_normalized = [val - start_offset for val in y_normalized]
            
            print(f"   変換後最大値: {max(y_normalized):.0f}発")
            print(f"   変換後最終値: {y_normalized[-1]:.0f}発")
            
        else:
            print("❌ ピクセル差が0のため、フォールバック処理")
            # フォールバック: 従来の方法
            GRAPH_RANGE = 60000
            px_per_ball = roi_h / GRAPH_RANGE
            zero_line_y = detect_zero_line_enhanced(roi)
            
            y_normalized = [-(y - zero_line_y) / px_per_ball for y in y_vals]
            x_normalized = [(x - min(x_vals)) / (max(x_vals) - min(x_vals)) * 100 for x in x_vals]
            
            start_offset = y_normalized[0]
            y_normalized = [val - start_offset for val in y_normalized]
            
            # 最大値スケーリング
            current_max = max(y_normalized)
            if current_max > 0:
                scale_factor = claude_max / current_max
                y_normalized = [val * scale_factor for val in y_normalized]
    
    else:
        print("❌ Claude最大値が無効、フォールバック処理")
        # フォールバック処理
        GRAPH_RANGE = 60000
        px_per_ball = roi_h / GRAPH_RANGE
        zero_line_y = detect_zero_line_enhanced(roi)
        
        y_normalized = [-(y - zero_line_y) / px_per_ball for y in y_vals]
        x_normalized = [(x - min(x_vals)) / (max(x_vals) - min(x_vals)) * 100 for x in x_vals]
        
        start_offset = y_normalized[0]
        y_normalized = [val - start_offset for val in y_normalized]
    
    # 結果統計
    calc_max = max(y_normalized)
    calc_min = min(y_normalized)
    calc_final = y_normalized[-1]
    
    print(f"\n📊 最終結果:")
    print(f"   開始値: {y_normalized[0]:.0f}発")
    print(f"   最大値: {calc_max:.0f}発")
    print(f"   最小値: {calc_min:.0f}発") 
    print(f"   最終値: {calc_final:.0f}発")
    
    # 精度計算
    max_accuracy = None
    final_accuracy = None
    
    if claude_max and claude_max > 0:
        max_diff = abs(calc_max - claude_max)
        max_accuracy = (1 - max_diff / claude_max) * 100 if claude_max > 0 else 0
        print(f"   最大値精度: {max_accuracy:.1f}%")
    
    final_diff = abs(calc_final - reference_final)
    final_accuracy = (1 - final_diff / abs(reference_final)) * 100
    print(f"   最終値精度: {final_accuracy:.1f}%")
    
    debug_info = {
        'claude_data': claude_data,
        'calculated_max': calc_max,
        'calculated_final': calc_final,
        'reference_final': reference_final,
        'max_accuracy': max_accuracy,
        'final_accuracy': final_accuracy,
        'px_per_ball': px_per_ball if 'px_per_ball' in locals() else None,
        'zero_line_y': zero_line_y if 'zero_line_y' in locals() else None,
        'roi_coords': roi_coords
    }
    
    return x_normalized, y_normalized, debug_info

def analyze_single_image_enhanced(image_path):
    """単一画像の強化解析"""
    filename = os.path.basename(image_path)
    print(f"\n{'='*60}")
    print(f"🔍 {filename} を強化解析中...")
    print(f"{'='*60}")
    
    # Claude APIでテキスト抽出（既存関数使用）
    claude_data = extract_values_with_claude(image_path)
    
    # 強化版グラフ解析
    x, y, debug_info = extract_graph_data_enhanced(image_path, claude_data)
    
    if x is None or y is None:
        print(f"❌ {filename} でグラフ線が検出できませんでした")
        return None
    
    # 結果表示とグラフ保存
    max_ball = int(max(y))
    min_ball = int(min(y))
    final_ball = int(y[-1])
    
    claude_max = claude_data.get('max_value') if claude_data else None
    max_accuracy = debug_info.get('max_accuracy')
    
    print(f"\n📊 解析結果:")
    print(f"   Claude最大値: {claude_max}")
    print(f"   計算最大値: {max_ball:,}発")
    print(f"   計算最終差玉: {final_ball:,}発")
    print(f"   参考最終値: -17,964発")
    if max_accuracy:
        print(f"   最大値精度: {max_accuracy:.1f}%")
    
    final_accuracy = debug_info.get('final_accuracy')
    if final_accuracy:
        print(f"   最終値精度: {final_accuracy:.1f}%")
    
    # グラフ保存
    plt.figure(figsize=(12, 8))
    plt.plot(x, y, linewidth=2, color='magenta', alpha=0.8, label='抽出されたグラフ')
    plt.title(f"{filename} - 強化版解析結果", fontsize=16)
    plt.xlabel("経過時間 (%)", fontsize=12)
    plt.ylabel("差玉", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.axhline(y=0, color='black', linestyle='--', alpha=0.5, label='ゼロライン')
    plt.legend()
    
    # 縦軸範囲を±30,000に設定
    plt.ylim(-30000, 30000)
    plt.yticks(range(-30000, 35000, 5000))
    
    # 統計情報
    stats_text = f'Claude最大値: {claude_max or "N/A"}\n計算最大値: {max_ball:,}発\n'
    stats_text += f'計算最終差玉: {final_ball:,}発\n参考最終値: -17,964発'
    
    final_accuracy = debug_info.get('final_accuracy')
    if max_accuracy:
        stats_text += f'\n最大値精度: {max_accuracy:.1f}%'
    if final_accuracy:
        stats_text += f'\n最終値精度: {final_accuracy:.1f}%'
    if claude_data:
        stats_text += f'\nスタート: {claude_data.get("start_count", "N/A")}\n大当り: {claude_data.get("jackpot_count", "N/A")}回'
    
    plt.text(0.02, 0.98, stats_text,
            transform=plt.gca().transAxes, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
            fontsize=9)
    
    plt.tight_layout()
    output_filename = f"enhanced_{filename}"
    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   💾 グラフ保存: {output_filename}")
    
    return {
        'filename': filename,
        'claude_max': claude_max,
        'calculated_max': max_ball,
        'calculated_final': final_ball,
        'max_accuracy': max_accuracy,
        'final_accuracy': debug_info.get('final_accuracy'),
        'claude_data': claude_data
    }

# 既存のextract_values_with_claude関数をそのまま使用
def extract_values_with_claude(image_path):
    """Claude APIを使って画像から数値を抽出"""
    try:
        # 画像をbase64エンコード
        base64_image = encode_image_to_base64(image_path)
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """この画像はパチンコの台データです。以下の数値を正確に読み取って、JSON形式で回答してください：

{
  "max_value": 最大値（「最大値: XXXX」の数字部分）,
  "final_value": 最終出玉（「最高出玉」の数字）,
  "final_diff": 最終差玉（グラフ右端に表示されている「ここまで (-XXXXX玉)」の数値、マイナス記号も含む）,
  "start_count": スタート回数（「スタート」の数字）,
  "jackpot_count": 大当り回数（「大当り回数」の数字）
}

数値のみを抽出し、カンマや「発」などの単位は除いてください。最終差玉は必ずマイナス記号も含めて正確に読み取ってください。見つからない場合はnullにしてください。"""
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_image
                            }
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(CLAUDE_API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            content = result['content'][0]['text']
            
            # JSONの抽出
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                json_str = content[json_start:json_end].strip()
            elif '{' in content and '}' in content:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                json_str = content[json_start:json_end]
            else:
                json_str = content
            
            try:
                data = json.loads(json_str)
                print(f"Claude API結果: {data}")
                return data
            except json.JSONDecodeError:
                print(f"JSON解析エラー: {json_str}")
                return None
                
        else:
            print(f"Claude API エラー: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"Claude API呼び出しエラー: {e}")
        return None

def encode_image_to_base64(image_path):
    """画像をbase64エンコード"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

if __name__ == "__main__":
    # 使用例
    # API キーの確認
    if not CLAUDE_API_KEY:
        print("❌ .envファイルにCLAUDE_API_KEYが設定されていません")
        exit(1)
    
    # 単一画像テスト用
    image_path = "./graphs/IMG_4403.png"  # テスト画像パス
    
    if os.path.exists(image_path):
        print("🚀 強化版パチンコグラフ解析を開始...")
        result = analyze_single_image_enhanced(image_path)
        
        if result:
            print("\n" + "="*60)
            print("🎯 強化版解析完了")
            print("="*60)
            print(f"ファイル: {result['filename']}")
            print(f"Claude最大値: {result['claude_max']}")
            print(f"計算最大値: {result['calculated_max']:,}発")
            print(f"計算最終差玉: {result['calculated_final']:,}発")
            if result['max_accuracy']:
                print(f"最大値精度: {result['max_accuracy']:.1f}%")
        else:
            print("❌ 解析に失敗しました")
    else:
        print(f"❌ 画像ファイルが見つかりません: {image_path}")
        print("フォルダ内の全画像を処理する場合:")
        print("folder = './graphs'")
        print("for path in glob(os.path.join(folder, '*.png')):")
        print("    analyze_single_image_enhanced(path)")