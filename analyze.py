from PIL import Image
import numpy as np
import os
from typing import Optional, Tuple, List

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """16進数カラーコードをRGBに変換"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def analyze_color_distribution(image_array: np.ndarray, target_color: str = "#f5ece7") -> dict:
    """画像の色分布を分析してターゲット色の最適な検出パラメータを決定"""
    target_rgb = np.array(hex_to_rgb(target_color))
    height, width = image_array.shape[:2]
    
    # 全ピクセルとターゲット色の距離を計算
    distances = np.sqrt(np.sum((image_array.reshape(-1, 3) - target_rgb) ** 2, axis=1))
    
    # 距離のヒストグラムを作成して最適な閾値を決定
    hist, bins = np.histogram(distances, bins=50, range=(0, 100))
    
    # ターゲット色に近いピクセルの割合を分析
    thresholds = [10, 15, 20, 25, 30]
    threshold_analysis = {}
    
    for threshold in thresholds:
        matching_pixels = np.sum(distances <= threshold)
        percentage = (matching_pixels / len(distances)) * 100
        threshold_analysis[threshold] = {
            'pixel_count': matching_pixels,
            'percentage': percentage
        }
    
    # 最適な閾値を選択（1-15%の範囲でマッチするものを優先）
    optimal_threshold = 20
    for threshold in thresholds:
        if 1 <= threshold_analysis[threshold]['percentage'] <= 15:
            optimal_threshold = threshold
            break
    
    return {
        'optimal_threshold': optimal_threshold,
        'analysis': threshold_analysis,
        'mean_distance': np.mean(distances),
        'std_distance': np.std(distances)
    }

def find_graph_by_adaptive_analysis(image_path: str, target_color: str = "#f5ece7", show_analysis: bool = False) -> Optional[Tuple[int, int, int, int]]:
    """
    適応的分析でグラフエリアを検出（改良版）
    """
    
    img = Image.open(image_path)
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    
    print(f"適応的分析開始: {width} x {height}")
    
    # 色分布を分析して最適なパラメータを決定
    color_analysis = analyze_color_distribution(img_array, target_color)
    optimal_threshold = color_analysis['optimal_threshold']
    
    if show_analysis:
        print(f"色分析結果:")
        print(f"  最適閾値: {optimal_threshold}")
        print(f"  平均距離: {color_analysis['mean_distance']:.1f}")
        for threshold, data in color_analysis['analysis'].items():
            print(f"  閾値{threshold}: {data['percentage']:.1f}% ({data['pixel_count']}ピクセル)")
    
    target_rgb = np.array(hex_to_rgb(target_color))
    
    # 1. 粗い検索：大まかなグラフエリアを特定
    # 画像を16x16のブロックに分割して分析
    block_size = min(width // 16, height // 16, 32)
    graph_blocks = []
    
    for y in range(0, height - block_size, block_size):
        for x in range(0, width - block_size, block_size):
            block = img_array[y:y+block_size, x:x+block_size, :3]
            distances = np.sqrt(np.sum((block.reshape(-1, 3) - target_rgb) ** 2, axis=1))
            matching_pixels = np.sum(distances <= optimal_threshold)
            density = matching_pixels / (block_size * block_size)
            
            if density > 0.05:  # 5%以上
                graph_blocks.append((x, y, x + block_size, y + block_size, density))
    
    if not graph_blocks:
        print("粗い検索でグラフエリアが見つかりませんでした")
        return None
    
    # 2. ブロックから連続領域を構築
    graph_blocks.sort(key=lambda x: x[4], reverse=True)  # 密度の高い順にソート
    
    if show_analysis:
        print(f"グラフブロック数: {len(graph_blocks)}")
        print("上位ブロック:")
        for i, (x, y, x2, y2, density) in enumerate(graph_blocks[:5]):
            print(f"  {i+1}. ({x},{y}) 密度: {density:.1%}")
    
    # 最も密度の高いブロック群から境界を推定
    min_x = min(block[0] for block in graph_blocks[:len(graph_blocks)//2])
    max_x = max(block[2] for block in graph_blocks[:len(graph_blocks)//2])
    min_y = min(block[1] for block in graph_blocks[:len(graph_blocks)//2])
    max_y = max(block[3] for block in graph_blocks[:len(graph_blocks)//2])
    
    # 3. 精密検索：境界を詳細に調整
    search_margin = 50
    search_left = max(0, min_x - search_margin)
    search_right = min(width, max_x + search_margin)
    search_top = max(0, min_y - search_margin)
    search_bottom = min(height, max_y + search_margin)
    
    # 行ごとの分析で上下境界を精密化
    row_densities = []
    for y in range(search_top, search_bottom):
        row = img_array[y, search_left:search_right, :3]
        distances = np.sqrt(np.sum((row - target_rgb) ** 2, axis=1))
        matching_pixels = np.sum(distances <= optimal_threshold)
        density = matching_pixels / (search_right - search_left)
        row_densities.append((y, density))
    
    # 密度が閾値以上の行を抽出
    dense_rows = [(y, density) for y, density in row_densities if density > 0.03]
    
    if dense_rows:
        top = min(row[0] for row in dense_rows)
        bottom = max(row[0] for row in dense_rows)
    else:
        top, bottom = search_top, search_bottom
    
    # 列ごとの分析で左右境界を精密化
    col_densities = []
    for x in range(search_left, search_right):
        col = img_array[top:bottom, x, :3]
        distances = np.sqrt(np.sum((col - target_rgb) ** 2, axis=1))
        matching_pixels = np.sum(distances <= optimal_threshold)
        density = matching_pixels / (bottom - top)
        col_densities.append((x, density))
    
    # 密度が閾値以上の列を抽出
    dense_cols = [(x, density) for x, density in col_densities if density > 0.02]
    
    if dense_cols:
        left = min(col[0] for col in dense_cols)
        right = max(col[0] for col in dense_cols)
    else:
        left, right = search_left, search_right
    
    # 4. 最終調整とパディング
    padding = 10
    left = max(0, left - padding)
    right = min(width - 1, right + padding)
    top = max(0, top - padding)
    bottom = min(height - 1, bottom + padding)
    
    # 結果の妥当性チェック（パチンコアプリ専用）
    area = (right - left) * (bottom - top)
    image_area = width * height
    area_ratio = area / image_area
    width_ratio = (right - left) / width
    
    # パチンコアプリのグラフエリア特性
    # - 横幅: 90%以上使用することが多い
    # - 高さ: 20-40%程度
    # - 面積: 15-40%程度
    
    if area_ratio < 0.05:
        print(f"警告: 検出エリアが小さすぎます ({area_ratio:.1%})")
        print("レイアウト分析にフォールバック")
        return find_graph_by_smart_layout_analysis(image_path)
    elif area_ratio > 0.7:
        print(f"警告: 検出エリアが大きすぎます ({area_ratio:.1%})")
        print("レイアウト分析にフォールバック") 
        return find_graph_by_smart_layout_analysis(image_path)
    elif width_ratio < 0.5:
        print(f"警告: 検出幅が狭すぎます ({width_ratio:.1%})")
        print("レイアウト分析にフォールバック")
        return find_graph_by_smart_layout_analysis(image_path)
    
    print(f"適応的分析結果: {left}, {top}, {right}, {bottom}")
    print(f"サイズ: {right - left} x {bottom - top}")
    print(f"画面比率: {(right-left)/width:.1%} x {(bottom-top)/height:.1%}")
    
    return (left, top, right, bottom)

def find_graph_by_smart_layout_analysis(image_path: str) -> Tuple[int, int, int, int]:
    """
    スマートなレイアウト分析（パチンコアプリ専用最適化）
    """
    
    img = Image.open(image_path)
    width, height = img.size
    
    print(f"スマートレイアウト分析: {width} x {height}")
    
    # パチンコアプリの実際のレイアウトパターンに基づく調整
    # 上部: 日付タブ、機種名、ボタン (約35%)
    # 中部: オレンジバー + グラフエリア (約35%)  
    # 下部: データ、ボタン (約30%)
    
    # 左右のマージンは狭め（グラフが横幅をほぼフルに使用）
    left_margin = 0.06   # 6%
    right_margin = 0.01  # 1%
    
    # 縦方向はオレンジバーの下からグラフが始まる
    if height > 2400:  # 高解像度（2556など）
        top_margin = 0.35    # 35% - オレンジバーの下
        bottom_margin = 0.42  # 42% - データ表示の上
    else:  # 標準解像度
        top_margin = 0.32
        bottom_margin = 0.40
    
    left = int(width * left_margin)
    right = int(width * (1 - right_margin))
    top = int(height * top_margin)
    bottom = int(height * (1 - bottom_margin))
    
    print(f"パチンコアプリ最適化レイアウト")
    print(f"推定領域: {left}, {top}, {right}, {bottom}")
    print(f"推定サイズ: {right-left} x {bottom-top}")
    print(f"画面比率: {(right-left)/width:.1%} x {(bottom-top)/height:.1%}")
    
    return (left, top, right, bottom)

def find_graph_by_orange_bar_detection(image_path: str) -> Optional[Tuple[int, int, int, int]]:
    """
    オレンジバーを検出してグラフエリアを特定（パチンコアプリ専用）
    """
    
    img = Image.open(image_path)
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    
    print(f"オレンジバー検出分析: {width} x {height}")
    
    # オレンジ色の範囲を定義（RGB値で直接検出）
    # パチンコアプリのオレンジバー: 濃いオレンジ系
    orange_ranges = [
        # 標準的なオレンジ
        ([200, 80, 0], [255, 150, 80]),
        # 明るいオレンジ
        ([220, 100, 20], [255, 180, 100]),
        # 濃いオレンジ
        ([180, 60, 0], [240, 120, 60])
    ]
    
    best_orange_rows = []
    best_score = 0
    
    # 各オレンジ範囲で検出を試行
    for lower_rgb, upper_rgb in orange_ranges:
        lower = np.array(lower_rgb)
        upper = np.array(upper_rgb)
        
        # 各行でオレンジ色のピクセルをカウント
        orange_rows = []
        for y in range(height):
            row = img_array[y, :, :3]
            # 各ピクセルがオレンジ範囲内かチェック
            in_range = np.all((row >= lower) & (row <= upper), axis=1)
            orange_pixel_count = np.sum(in_range)
            
            # 行の30%以上がオレンジ色ならオレンジバー候補
            if orange_pixel_count > width * 0.3:
                orange_rows.append((y, orange_pixel_count))
        
        # この範囲での検出スコアを計算
        if orange_rows:
            total_score = sum(count for _, count in orange_rows)
            if total_score > best_score:
                best_score = total_score
                best_orange_rows = orange_rows
    
    if not best_orange_rows:
        print("オレンジバーが検出されませんでした")
        return None
    
    # オレンジバーの位置を特定
    orange_y_positions = [y for y, _ in best_orange_rows]
    orange_top = min(orange_y_positions)
    orange_bottom = max(orange_y_positions)
    orange_height = orange_bottom - orange_top
    
    print(f"オレンジバー検出: Y={orange_top}-{orange_bottom} (高さ: {orange_height})")
    print(f"検出された行数: {len(best_orange_rows)}")
    
    # グラフエリアはオレンジバーの直下に位置
    graph_top = orange_bottom + 10  # 少し余裕を持たせる
    
    # グラフの高さを推定（画面の20-30%程度）
    estimated_graph_height = int(height * 0.28)
    graph_bottom = min(height - 100, graph_top + estimated_graph_height)  # 下部に余裕
    
    # 左右は画面幅の大部分を使用
    graph_left = int(width * 0.04)   # 4%マージン
    graph_right = int(width * 0.98)  # 2%マージン
    
    # 検出結果の妥当性チェック
    if graph_bottom <= graph_top:
        print("グラフエリアの高さが無効です")
        return None
    
    print(f"オレンジバー基準グラフエリア: {graph_left}, {graph_top}, {graph_right}, {graph_bottom}")
    print(f"グラフサイズ: {graph_right - graph_left} x {graph_bottom - graph_top}")
    
    return (graph_left, graph_top, graph_right, graph_bottom)

def find_graph_by_edge_detection(image_path: str) -> Optional[Tuple[int, int, int, int]]:
    """
    シンプルなエッジ検出（cv2不使用版）
    """
    
    img = Image.open(image_path)
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    
    print("シンプルエッジ検出を実行中...")
    
    # グレースケール変換（手動）
    gray = np.dot(img_array[...,:3], [0.2989, 0.5870, 0.1140])
    
    # 簡単なエッジ検出（Sobelフィルタの近似）
    # 垂直エッジ
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
    # 水平エッジ  
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
    
    # パディングして畳み込み演算
    padded = np.pad(gray, 1, mode='edge')
    edges_x = np.zeros_like(gray)
    edges_y = np.zeros_like(gray)
    
    for i in range(height):
        for j in range(width):
            region = padded[i:i+3, j:j+3]
            edges_x[i, j] = np.sum(region * sobel_x)
            edges_y[i, j] = np.sum(region * sobel_y)
    
    # エッジ強度を計算
    edge_magnitude = np.sqrt(edges_x**2 + edges_y**2)
    
    # 閾値処理
    threshold = np.percentile(edge_magnitude, 90)  # 上位10%をエッジとする
    edges = edge_magnitude > threshold
    
    # エッジが集中している領域を探す
    # ブロック単位で分析
    block_size = 32
    max_edge_density = 0
    best_region = None
    
    for y in range(0, height - block_size, block_size // 2):
        for x in range(0, width - block_size, block_size // 2):
            block = edges[y:y+block_size, x:x+block_size]
            edge_density = np.sum(block) / (block_size * block_size)
            
            if edge_density > max_edge_density:
                max_edge_density = edge_density
                best_region = (x, y, x + block_size, y + block_size)
    
    if best_region is None or max_edge_density < 0.1:
        print("エッジ検出: 有効な領域が見つかりませんでした")
        return None
    
    # 検出された領域を拡張
    left, top, right, bottom = best_region
    padding = 50
    left = max(0, left - padding)
    right = min(width, right + padding)
    top = max(0, top - padding)  
    bottom = min(height, bottom + padding)
    
    print(f"エッジ検出結果: {left}, {top}, {right}, {bottom}")
    return (left, top, right, bottom)
    """
    エッジ検出を使用してグラフ境界を特定
    """
    
    img = Image.open(image_path)
    img_array = np.array(img)
    
    # グレースケール変換
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # ガウシアンブラーを適用
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Cannyエッジ検出
    edges = cv2.Canny(blurred, 30, 100)
    
    # 輪郭を検出
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None
    
    # 最大の輪郭を選択
    largest_contour = max(contours, key=cv2.contourArea)
    
    # バウンディングボックスを取得
    x, y, w, h = cv2.boundingRect(largest_contour)
    
    # 結果の妥当性チェック
    area = w * h
    image_area = img.size[0] * img.size[1]
    
    if area / image_area < 0.1:  # 10%未満の場合は無効
        return None
    
    return (x, y, x + w, y + h)

def crop_graph_enhanced(image_path: str, output_path: Optional[str] = None, target_color: str = "#f5ece7") -> Optional[Image.Image]:
    """
    拡張されたグラフ切り抜き機能
    """
    
    print(f"--- 拡張グラフ切り抜き: {os.path.basename(image_path)} ---")
    
    img = Image.open(image_path)
    print(f"元画像サイズ: {img.size[0]} x {img.size[1]}")
    
    methods = [
        ("オレンジバー検出", find_graph_by_orange_bar_detection),
        ("適応的分析", lambda path: find_graph_by_adaptive_analysis(path, target_color, show_analysis=True)),
        ("スマートレイアウト", find_graph_by_smart_layout_analysis),
        ("エッジ検出", find_graph_by_edge_detection)
    ]
    
    results = []
    
    for method_name, method_func in methods:
        print(f"\n=== {method_name} ===")
        try:
            bounds = method_func(image_path)
            
            if bounds:
                left, top, right, bottom = bounds
                area = (right - left) * (bottom - top)
                
                # 結果の品質評価（パチンコアプリ専用）
                width_ratio = (right - left) / img.size[0]
                height_ratio = (bottom - top) / img.size[1]
                area_ratio = area / (img.size[0] * img.size[1])
                quality_score = 0
                
                # パチンコアプリのグラフに最適化した評価基準
                # 横幅: 85-95%が理想的（グラフは横幅をほぼフルに使用）
                if 0.85 <= width_ratio <= 0.98:
                    quality_score += 40
                elif 0.75 <= width_ratio <= 0.85:
                    quality_score += 30
                elif 0.60 <= width_ratio <= 0.75:
                    quality_score += 20
                
                # 高さ: 20-35%が理想的（グラフエリアは画面の約1/4-1/3）
                if 0.20 <= height_ratio <= 0.35:
                    quality_score += 40
                elif 0.15 <= height_ratio <= 0.45:
                    quality_score += 30
                elif 0.10 <= height_ratio <= 0.55:
                    quality_score += 20
                
                # 面積比率: 15-35%が理想的
                if 0.15 <= area_ratio <= 0.35:
                    quality_score += 20
                elif 0.10 <= area_ratio <= 0.45:
                    quality_score += 15
                
                # 特別ボーナス: 適応的分析で色検出が成功した場合
                if method_name == "適応的分析" and area_ratio >= 0.15:
                    quality_score += 25  # 色検出成功ボーナス
                
                results.append((method_name, bounds, area, quality_score))
                print(f"{method_name}結果: {bounds}")
                print(f"  面積: {area}, 品質スコア: {quality_score}")
            else:
                print(f"{method_name}: 検出失敗")
        except Exception as e:
            print(f"{method_name}: エラー - {e}")
    
    if not results:
        print("全ての手法で検出に失敗しました")
        return None
    
    # 品質スコアが最も高い結果を選択
    results.sort(key=lambda x: x[3], reverse=True)
    
    print(f"\n=== 結果比較 ===")
    for i, (name, bounds, area, score) in enumerate(results):
        print(f"{i+1}. {name}: 品質スコア {score}, 面積 {area}")
    
    chosen_name, chosen_bounds, chosen_area, chosen_score = results[0]
    print(f"\n選択された手法: {chosen_name} (スコア: {chosen_score})")
    print(f"最終的な切り抜き範囲: {chosen_bounds}")
    
    # 切り抜き実行
    left, top, right, bottom = chosen_bounds
    cropped_img = img.crop((left, top, right, bottom))
    
    if output_path:
        cropped_img.save(output_path)
        print(f"✓ 切り抜き完了: {output_path}")
    
    return cropped_img

def batch_process_images(input_folder: str = "graphs", output_folder: str = "graphs/cropped_enhanced"):
    """
    フォルダ内の全画像を一括処理
    """
    
    if not os.path.exists(input_folder):
        print(f"❌ フォルダが見つかりません: {input_folder}")
        return
    
    # 対応画像形式
    supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
    files = [f for f in os.listdir(input_folder) 
             if f.lower().endswith(supported_formats)]
    
    if not files:
        print(f"❌ {input_folder}に画像ファイルが見つかりません")
        return
    
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"🚀 {len(files)}個の画像を処理開始...")
    print(f"📁 出力フォルダ: {output_folder}")
    
    successful = 0
    failed = []
    
    for i, file in enumerate(files, 1):
        input_path = os.path.join(input_folder, file)
        filename_without_ext = os.path.splitext(file)[0]
        output_path = os.path.join(output_folder, f"{filename_without_ext}_cropped.png")
        
        print(f"\n[{i}/{len(files)}] 処理中: {file}")
        print("-" * 50)
        
        try:
            result = crop_graph_enhanced(input_path, output_path)
            if result:
                successful += 1
                print(f"✅ 完了: {file}")
            else:
                failed.append(file)
                print(f"❌ 失敗: {file}")
        except Exception as e:
            failed.append(file)
            print(f"❌ エラー: {file} - {e}")
    
    print(f"\n🎉 処理完了！")
    print(f"✅ 成功: {successful}/{len(files)}個")
    if failed:
        print(f"❌ 失敗: {len(failed)}個")
        for f in failed:
            print(f"  - {f}")
    
    print(f"📁 結果フォルダ: {output_folder}")

# 使用例とメインプログラム
if __name__ == "__main__":
    
    print("🎯 改良版グラフ切り抜きツール")
    print("=" * 50)
    
    if os.path.exists("graphs"):
        files = [f for f in os.listdir("graphs") 
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'))]
        
        if files:
            print(f"📁 {len(files)}個の画像ファイルを発見")
            print("\n選択してください:")
            print("1. 🚀 全画像を自動処理（推奨）")
            print("2. 📷 単一画像を処理")
            print("3. 🔧 詳細設定で処理")
            
            choice = input("\n番号を入力 (1-3): ").strip()
            
            if choice == "1":
                # 全画像を自動処理
                batch_process_images()
                
            elif choice == "2":
                # 単一画像を処理
                print("\n利用可能な画像:")
                for i, file in enumerate(files, 1):
                    print(f"{i}. {file}")
                
                try:
                    file_num = int(input("\n画像番号を入力: ").strip())
                    if 1 <= file_num <= len(files):
                        selected_file = files[file_num - 1]
                        input_path = os.path.join("graphs", selected_file)
                        
                        output_folder = "graphs/cropped_single"
                        os.makedirs(output_folder, exist_ok=True)
                        filename_without_ext = os.path.splitext(selected_file)[0]
                        output_path = os.path.join(output_folder, f"{filename_without_ext}_cropped.png")
                        
                        crop_graph_enhanced(input_path, output_path)
                    else:
                        print("❌ 無効な番号です")
                except ValueError:
                    print("❌ 数字を入力してください")
                    
            elif choice == "3":
                # 詳細設定
                print("\n🔧 詳細設定")
                
                # ターゲット色の設定
                print("グラフ背景色を指定してください:")
                print("1. デフォルト (#f5ece7)")
                print("2. カスタム色を指定")
                
                color_choice = input("選択 (1-2): ").strip()
                target_color = "#f5ece7"
                
                if color_choice == "2":
                    custom_color = input("16進数カラーコード (例: #ffffff): ").strip()
                    if custom_color.startswith('#') and len(custom_color) == 7:
                        target_color = custom_color
                    else:
                        print("無効な色コードです。デフォルトを使用します。")
                
                # 出力フォルダの設定
                output_folder = input("出力フォルダ名 (デフォルト: graphs/cropped_custom): ").strip()
                if not output_folder:
                    output_folder = "graphs/cropped_custom"
                
                print(f"設定:")
                print(f"  ターゲット色: {target_color}")
                print(f"  出力フォルダ: {output_folder}")
                
                # 処理実行
                batch_process_images("graphs", output_folder)
            else:
                print("❌ 無効な選択です")
        else:
            print("❌ 画像ファイルが見つかりません")
    else:
        print("❌ graphsフォルダが見つかりません")
        print("📁 フォルダを作成して画像を配置してください")
    
    print("\n✨ プログラム終了")