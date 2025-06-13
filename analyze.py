from PIL import Image
import numpy as np
import os

def hex_to_rgb(hex_color):
    """16進数カラーコードをRGBに変換"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def find_graph_by_smart_analysis(image_path, target_color="#f5ece7", show_analysis=False):
    """
    スマートな分析でグラフエリアを検出
    
    Args:
        image_path (str): 画像パス
        target_color (str): グラフ背景色
        show_analysis (bool): 分析過程を表示するか
    
    Returns:
        tuple: (left, top, right, bottom) 座標
    """
    
    img = Image.open(image_path)
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    
    print(f"スマート分析開始: {width} x {height}")
    
    # 1. 画面を水平方向にスキャンして、グラフエリアらしい行を見つける
    target_rgb = np.array(hex_to_rgb(target_color))
    graph_rows = []
    
    print("水平スキャンでグラフエリアを検出中...")
    
    # 各行について、ターゲット色の密度を計算
    for y in range(height):
        row = img_array[y, :, :3]
        # ターゲット色に近いピクセルの数をカウント
        distances = np.sqrt(np.sum((row - target_rgb) ** 2, axis=1))
        target_pixels = np.sum(distances <= 15)  # 厳しい許容範囲
        
        # その行の総ピクセル数に対する割合
        density = target_pixels / width
        
        # グラフエリアと思われる行を記録（密度が10%以上）
        if density > 0.1:
            graph_rows.append((y, density, target_pixels))
    
    if not graph_rows:
        print("グラフエリアが見つかりませんでした")
        return None
    
    if show_analysis:
        print(f"グラフ候補行数: {len(graph_rows)}")
        for y, density, pixels in graph_rows[:10]:  # 上位10行を表示
            print(f"  行 {y}: 密度 {density:.1%}, ピクセル数 {pixels}")
    
    # 2. 連続するグラフエリアを見つける
    # グラフ行をy座標でソート
    graph_rows.sort(key=lambda x: x[0])
    
    # 最大の連続領域を見つける
    best_region = None
    current_region = []
    max_region_size = 0
    
    for i, (y, density, pixels) in enumerate(graph_rows):
        if not current_region or y - current_region[-1][0] <= 5:  # 5ピクセル以内は連続とみなす
            current_region.append((y, density, pixels))
        else:
            # 現在の領域を評価
            if len(current_region) > max_region_size:
                max_region_size = len(current_region)
                best_region = current_region.copy()
            current_region = [(y, density, pixels)]
    
    # 最後の領域もチェック
    if len(current_region) > max_region_size:
        best_region = current_region
    
    if not best_region:
        print("連続するグラフ領域が見つかりませんでした")
        return None
    
    # 3. 上下境界を決定
    top = best_region[0][0]
    bottom = best_region[-1][0]
    
    # 境界を少し拡張
    padding = 20
    top = max(0, top - padding)
    bottom = min(height - 1, bottom + padding)
    
    print(f"検出された縦範囲: {top} - {bottom} (高さ: {bottom - top})")
    
    # 4. 左右境界を決定（より詳細な分析）
    # 検出された縦範囲内で、列ごとにターゲット色の密度を分析
    graph_cols = []
    
    print("垂直スキャンで左右境界を検出中...")
    
    for x in range(width):
        col = img_array[top:bottom, x, :3]
        distances = np.sqrt(np.sum((col - target_rgb) ** 2, axis=1))
        target_pixels = np.sum(distances <= 15)
        density = target_pixels / (bottom - top)
        
        if density > 0.05:  # 5%以上
            graph_cols.append((x, density, target_pixels))
    
    if not graph_cols:
        # フォールバック: 縦範囲内で左右の余白を推定
        print("列分析が失敗。余白推定にフォールバック...")
        left = int(width * 0.05)
        right = int(width * 0.95)
    else:
        # 左右境界を決定
        graph_cols.sort(key=lambda x: x[0])
        left = graph_cols[0][0]
        right = graph_cols[-1][0]
        
        # 境界を少し拡張
        left = max(0, left - 20)
        right = min(width - 1, right + 20)
    
    print(f"検出された横範囲: {left} - {right} (幅: {right - left})")
    print(f"最終領域サイズ: {right - left} x {bottom - top}")
    print(f"画面比率: {(right-left)/width:.1%} x {(bottom-top)/height:.1%}")
    
    return (left, top, right, bottom)

def find_graph_by_layout_analysis(image_path):
    """
    レイアウト分析でグラフエリアを推定（改良版）
    """
    
    img = Image.open(image_path)
    width, height = img.size
    
    print(f"レイアウト分析: {width} x {height}")
    
    # パチンコアプリの一般的なレイアウト分析
    # 上部: タイトル、ボタン等 (約35-40%)
    # 中部: グラフエリア (約25-35%) 
    # 下部: データ、ボタン等 (約25-35%)
    
    if height > 2000:  # 高解像度
        # より正確な範囲を設定
        left = int(width * 0.07)    # 7%マージン
        right = int(width * 0.93)   # 7%マージン
        top = int(height * 0.28)    # 28%位置から
        bottom = int(height * 0.59) # 59%位置まで（約31%の高さ）
    else:
        left = int(width * 0.08)
        right = int(width * 0.92)
        top = int(height * 0.30)
        bottom = int(height * 0.65)
    
    print(f"レイアウト推定領域: {left}, {top}, {right}, {bottom}")
    print(f"推定サイズ: {right-left} x {bottom-top}")
    print(f"画面比率: {(right-left)/width:.1%} x {(bottom-top)/height:.1%}")
    
    return (left, top, right, bottom)

def find_graph_by_color_boundary(image_path, target_color="#f5ece7"):
    """
    色境界を使ってグラフエリアを検出
    """
    
    img = Image.open(image_path)
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    
    target_rgb = np.array(hex_to_rgb(target_color))
    
    print("色境界検出を実行中...")
    
    # まず大まかな領域を特定
    layout_bounds = find_graph_by_layout_analysis(image_path)
    layout_left, layout_top, layout_right, layout_bottom = layout_bounds
    
    # レイアウト推定領域内で詳細な色分析
    region = img_array[layout_top:layout_bottom, layout_left:layout_right, :3]
    region_height, region_width = region.shape[:2]
    
    # 各ピクセルがターゲット色に近いかチェック
    distances = np.sqrt(np.sum((region - target_rgb) ** 2, axis=2))
    mask = distances <= 20  # 許容範囲
    
    if not np.any(mask):
        print("色境界検出失敗、レイアウト分析結果を使用")
        return layout_bounds
    
    # マスクから実際の境界を計算
    y_coords, x_coords = np.where(mask)
    
    if len(y_coords) == 0:
        return layout_bounds
    
    # 相対座標から絶対座標に変換
    abs_left = layout_left + np.min(x_coords)
    abs_right = layout_left + np.max(x_coords)
    abs_top = layout_top + np.min(y_coords)
    abs_bottom = layout_top + np.max(y_coords)
    
    # パディングを追加
    padding = 15
    abs_left = max(0, abs_left - padding)
    abs_right = min(width - 1, abs_right + padding)
    abs_top = max(0, abs_top - padding)
    abs_bottom = min(height - 1, abs_bottom + padding)
    
    print(f"色境界検出結果: {abs_left}, {abs_top}, {abs_right}, {abs_bottom}")
    print(f"サイズ: {abs_right - abs_left} x {abs_bottom - abs_top}")
    
    return (abs_left, abs_top, abs_right, abs_bottom)

def crop_graph_multi_method(image_path, output_path=None, target_color="#f5ece7"):
    """
    複数の手法を組み合わせてグラフを切り抜く
    """
    
    print(f"--- 複数手法でのグラフ切り抜き: {os.path.basename(image_path)} ---")
    
    img = Image.open(image_path)
    print(f"元画像サイズ: {img.size[0]} x {img.size[1]}")
    
    methods = [
        ("スマート分析", find_graph_by_smart_analysis),
        ("色境界検出", find_graph_by_color_boundary),
        ("レイアウト分析", find_graph_by_layout_analysis)
    ]
    
    results = []
    
    for method_name, method_func in methods:
        print(f"\n=== {method_name} ===")
        try:
            if method_name == "スマート分析":
                bounds = method_func(image_path, target_color, show_analysis=True)
            elif method_name == "色境界検出":
                bounds = method_func(image_path, target_color)
            else:
                bounds = method_func(image_path)
            
            if bounds:
                left, top, right, bottom = bounds
                area = (right - left) * (bottom - top)
                results.append((method_name, bounds, area))
                print(f"{method_name}結果: {bounds}, 面積: {area}")
            else:
                print(f"{method_name}: 検出失敗")
        except Exception as e:
            print(f"{method_name}: エラー - {e}")
    
    if not results:
        print("全ての手法で検出に失敗しました")
        return None
    
    # 最も適切な結果を選択（面積が中程度のもの）
    results.sort(key=lambda x: x[2])  # 面積でソート
    
    print(f"\n=== 結果比較 ===")
    for i, (name, bounds, area) in enumerate(results):
        print(f"{i+1}. {name}: 面積 {area}")
    
    # 中央値の結果を選択（極端すぎず、小さすぎない）
    if len(results) >= 2:
        chosen = results[len(results)//2]  # 中央値
    else:
        chosen = results[0]
    
    chosen_name, chosen_bounds, chosen_area = chosen
    print(f"\n選択された手法: {chosen_name}")
    print(f"最終的な切り抜き範囲: {chosen_bounds}")
    
    # 切り抜き実行
    left, top, right, bottom = chosen_bounds
    cropped_img = img.crop((left, top, right, bottom))
    
    if output_path:
        cropped_img.save(output_path)
        print(f"✓ 切り抜き完了: {output_path}")
    
    return cropped_img

# 使用例
if __name__ == "__main__":
    
    if os.path.exists("graphs"):
        print("=== graphsフォルダ内の画像一覧 ===")
        files = [f for f in os.listdir("graphs") 
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
        
        if files:
            for i, file in enumerate(files, 1):
                print(f"{i}. {file}")
            
            print("\n選択してください:")
            print("1. 🚀 全画像を自動処理（推奨）")
            print("2. 📷 番号で画像を選択")
            print("3. 📝 ファイル名で画像を指定")
            print("4. 🔧 手法を指定して処理")
            
            choice = input("番号を入力 (1-4): ").strip()
            
            if choice == "1":
                # 全画像を自動処理（最も簡単）
                print(f"\n🚀 {len(files)}個の画像を自動処理開始...")
                output_folder = "graphs/cropped_auto"
                os.makedirs(output_folder, exist_ok=True)
                
                successful = 0
                for i, file in enumerate(files, 1):
                    input_path = os.path.join("graphs", file)
                    filename_without_ext = os.path.splitext(file)[0]
                    output_path = os.path.join(output_folder, f"{filename_without_ext}_cropped.png")
                    
                    print(f"\n[{i}/{len(files)}] 処理中: {file}")
                    try:
                        crop_graph_multi_method(input_path, output_path)
                        successful += 1
                        print(f"✅ 完了")
                    except Exception as e:
                        print(f"❌ エラー: {e}")
                
                print(f"\n🎉 処理完了！ {successful}/{len(files)}個成功")
                print(f"📁 出力フォルダ: {output_folder}")
                
            elif choice == "2":
                # 番号で選択（簡単）
                try:
                    file_num = int(input("画像番号を入力: ").strip())
                    if 1 <= file_num <= len(files):
                        selected_file = files[file_num - 1]
                        print(f"\n📷 選択: {selected_file}")
                        
                        input_path = os.path.join("graphs", selected_file)
                        output_folder = "graphs/cropped_auto"
                        os.makedirs(output_folder, exist_ok=True)
                        filename_without_ext = os.path.splitext(selected_file)[0]
                        output_path = os.path.join(output_folder, f"{filename_without_ext}_cropped.png")
                        
                        crop_graph_multi_method(input_path, output_path)
                    else:
                        print("❌ 無効な番号です")
                except ValueError:
                    print("❌ 数字を入力してください")
                    
            elif choice == "3":
                # ファイル名で指定（従来の方法）
                filename = input("ファイル名を入力: ").strip()
                if filename in files:
                    print(f"\n📝 選択: {filename}")
                    input_path = os.path.join("graphs", filename)
                    output_folder = "graphs/cropped_auto"
                    os.makedirs(output_folder, exist_ok=True)
                    filename_without_ext = os.path.splitext(filename)[0]
                    output_path = os.path.join(output_folder, f"{filename_without_ext}_cropped.png")
                    
                    crop_graph_multi_method(input_path, output_path)
                else:
                    print("❌ ファイルが見つかりません")
                    print("利用可能なファイル:", ", ".join(files))
                    
            elif choice == "4":
                # 手法を指定（上級者向け）
                print("\n🔧 手法を選択:")
                print("1. 複数手法（自動選択）")
                print("2. スマート分析のみ")
                print("3. レイアウト分析のみ")
                print("4. 色境界検出のみ")
                
                method_choice = input("手法番号を入力 (1-4): ").strip()
                
                try:
                    file_num = int(input("画像番号を入力: ").strip())
                    if 1 <= file_num <= len(files):
                        selected_file = files[file_num - 1]
                        input_path = os.path.join("graphs", selected_file)
                        
                        if method_choice == "1":
                            output_folder = "graphs/cropped_multi"
                            os.makedirs(output_folder, exist_ok=True)
                            filename_without_ext = os.path.splitext(selected_file)[0]
                            output_path = os.path.join(output_folder, f"{filename_without_ext}_multi.png")
                            crop_graph_multi_method(input_path, output_path)
                            
                        elif method_choice == "2":
                            bounds = find_graph_by_smart_analysis(input_path, show_analysis=True)
                            if bounds:
                                img = Image.open(input_path)
                                cropped = img.crop(bounds)
                                output_folder = "graphs/cropped_smart"
                                os.makedirs(output_folder, exist_ok=True)
                                filename_without_ext = os.path.splitext(selected_file)[0]
                                output_path = os.path.join(output_folder, f"{filename_without_ext}_smart.png")
                                cropped.save(output_path)
                                print(f"✅ スマート分析完了: {output_path}")
                                
                        elif method_choice == "3":
                            bounds = find_graph_by_layout_analysis(input_path)
                            img = Image.open(input_path)
                            cropped = img.crop(bounds)
                            output_folder = "graphs/cropped_layout"
                            os.makedirs(output_folder, exist_ok=True)
                            filename_without_ext = os.path.splitext(selected_file)[0]
                            output_path = os.path.join(output_folder, f"{filename_without_ext}_layout.png")
                            cropped.save(output_path)
                            print(f"✅ レイアウト分析完了: {output_path}")
                            
                        elif method_choice == "4":
                            bounds = find_graph_by_color_boundary(input_path)
                            img = Image.open(input_path)
                            cropped = img.crop(bounds)
                            output_folder = "graphs/cropped_color"
                            os.makedirs(output_folder, exist_ok=True)
                            filename_without_ext = os.path.splitext(selected_file)[0]
                            output_path = os.path.join(output_folder, f"{filename_without_ext}_color.png")
                            cropped.save(output_path)
                            print(f"✅ 色境界検出完了: {output_path}")
                        else:
                            print("❌ 無効な手法番号です")
                    else:
                        print("❌ 無効な画像番号です")
                except ValueError:
                    print("❌ 数字を入力してください")
            else:
                print("❌ 無効な選択です")
        else:
            print("❌ 画像ファイルが見つかりません")
    else:
        print("❌ graphsフォルダが見つかりません")
        print("📁 フォルダを作成して画像を配置してください")
    
    print("\n✨ 処理完了！")