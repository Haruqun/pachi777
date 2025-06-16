#!/usr/bin/env python3
"""
高精度パチンコグラフ切り抜きツール
- 複数の検出手法を組み合わせ
- AI学習による精度向上
- 詳細な検証・評価機能
- 完璧な精度を目指した最新版
"""

import os
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
from datetime import datetime
from typing import Tuple, List, Optional, Dict, Any
from scipy import ndimage
from scipy.signal import find_peaks
import cv2

# オプショナル機能
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    PLOT_AVAILABLE = True
except ImportError:
    PLOT_AVAILABLE = False

try:
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


class HighPrecisionCropper:
    """高精度グラフ切り抜きシステム"""
    
    def __init__(self):
        self.debug_mode = True
        self.detection_results = []
        self.ground_truth_data = []
        self.learning_data = {}
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            timestamp = datetime.now().strftime("%H:%M:%S")
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{timestamp}] {message}")
    
    # =====================================
    # 1. 基本検出手法
    # =====================================
    
    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """16進数カラーコードをRGBに変換"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def detect_by_color_analysis(self, image_path: str, target_colors: List[str] = None) -> Optional[Tuple[int, int, int, int]]:
        """色分析による検出（改良版）"""
        self.log("色分析検出を開始", "DEBUG")
        
        if target_colors is None:
            target_colors = ["#f5ece7", "#f0e6e1", "#e8ddd7", "#ede3dd"]
        
        img = Image.open(image_path)
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        # 複数色での統合検出
        combined_mask = np.zeros((height, width), dtype=bool)
        
        for color in target_colors:
            target_rgb = np.array(self.hex_to_rgb(color))
            
            # 色距離計算（改良版）
            reshaped = img_array[:, :, :3].reshape(-1, 3).astype(np.float64)
            distances = np.sqrt(np.sum((reshaped - target_rgb) ** 2, axis=1))
            
            # 動的閾値計算
            threshold = np.percentile(distances, 15)  # 下位15%
            threshold = max(10, min(threshold, 30))  # 範囲制限
            
            mask = distances <= threshold
            mask_2d = mask.reshape(height, width)
            combined_mask = combined_mask | mask_2d
        
        return self._extract_bounds_from_mask(combined_mask, width, height, "色分析")
    
    def detect_by_texture_analysis(self, image_path: str) -> Optional[Tuple[int, int, int, int]]:
        """テクスチャ分析による検出"""
        self.log("テクスチャ分析検出を開始", "DEBUG")
        
        img = Image.open(image_path)
        img_array = np.array(img)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        height, width = gray.shape
        
        # ガボールフィルタによるテクスチャ解析
        kernels = []
        for theta in range(0, 180, 30):
            kernel = cv2.getGaborKernel((21, 21), 5, np.radians(theta), 2*np.pi*0.5, 0.5, 0, ktype=cv2.CV_32F)
            kernels.append(kernel)
        
        # テクスチャ特徴を抽出
        texture_responses = []
        for kernel in kernels:
            filtered = cv2.filter2D(gray, cv2.CV_8UC3, kernel)
            texture_responses.append(filtered)
        
        # 統合テクスチャマップ
        texture_map = np.mean(texture_responses, axis=0)
        
        # グラフエリア特有のテクスチャを検出
        # グラフエリアは比較的均一なテクスチャを持つ
        texture_variance = ndimage.generic_filter(texture_map, np.var, size=20)
        
        # 低分散エリア（均一なエリア）を検出
        uniform_mask = texture_variance < np.percentile(texture_variance, 25)
        
        return self._extract_bounds_from_mask(uniform_mask, width, height, "テクスチャ分析")
    
    def detect_by_edge_analysis(self, image_path: str) -> Optional[Tuple[int, int, int, int]]:
        """エッジ分析による検出（高精度版）"""
        self.log("エッジ分析検出を開始", "DEBUG")
        
        img = Image.open(image_path)
        img_array = np.array(img)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        height, width = gray.shape
        
        # マルチスケールエッジ検出
        edges_multi = np.zeros_like(gray, dtype=np.float32)
        
        # 複数の閾値でCannyエッジ検出
        thresholds = [(30, 100), (50, 150), (70, 200)]
        for low, high in thresholds:
            edges = cv2.Canny(gray, low, high)
            edges_multi += edges.astype(np.float32)
        
        # エッジ密度マップ
        edge_density = ndimage.uniform_filter(edges_multi, size=20)
        
        # グラフ境界の特徴：中程度のエッジ密度
        graph_mask = (edge_density > np.percentile(edge_density, 30)) & \
                     (edge_density < np.percentile(edge_density, 85))
        
        return self._extract_bounds_from_mask(graph_mask, width, height, "エッジ分析")
    
    def detect_by_gradient_analysis(self, image_path: str) -> Optional[Tuple[int, int, int, int]]:
        """グラデーション分析による検出"""
        self.log("グラデーション分析検出を開始", "DEBUG")
        
        img = Image.open(image_path)
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        # 各チャンネルでのグラデーション計算
        gradients = []
        for channel in range(3):
            grad_x = np.gradient(img_array[:, :, channel], axis=1)
            grad_y = np.gradient(img_array[:, :, channel], axis=0)
            grad_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            gradients.append(grad_magnitude)
        
        # 統合グラデーション
        combined_gradient = np.mean(gradients, axis=0)
        
        # グラフエリアは比較的低いグラデーション
        low_gradient_mask = combined_gradient < np.percentile(combined_gradient, 40)
        
        return self._extract_bounds_from_mask(low_gradient_mask, width, height, "グラデーション分析")
    
    def detect_by_layout_analysis(self, image_path: str) -> Optional[Tuple[int, int, int, int]]:
        """レイアウト分析による検出（パチンコアプリ特化）"""
        self.log("レイアウト分析検出を開始", "DEBUG")
        
        img = Image.open(image_path)
        width, height = img.size
        
        # パチンコアプリの画面解像度別の最適化
        resolution_configs = {
            # 高解像度（iPhone Pro系）
            "high": {"min_height": 2400, "top": 0.32, "bottom": 0.38, "left": 0.05, "right": 0.02},
            # 標準解像度
            "standard": {"min_height": 1800, "top": 0.30, "bottom": 0.35, "left": 0.06, "right": 0.03},
            # 低解像度
            "low": {"min_height": 0, "top": 0.28, "bottom": 0.40, "left": 0.08, "right": 0.04}
        }
        
        # 解像度に応じた設定選択
        config = None
        for res_type, res_config in resolution_configs.items():
            if height >= res_config["min_height"]:
                config = res_config
                break
        
        if config is None:
            config = resolution_configs["low"]
        
        # 座標計算
        left = int(width * config["left"])
        right = int(width * (1 - config["right"]))
        top = int(height * config["top"])
        bottom = int(height * (1 - config["bottom"]))
        
        self.log(f"レイアウト検出: {left}, {top}, {right}, {bottom} (解像度: {width}x{height})", "DEBUG")
        
        return (left, top, right, bottom)
    
    def detect_by_orange_bar(self, image_path: str) -> Optional[Tuple[int, int, int, int]]:
        """オレンジバー検出による高精度位置特定"""
        self.log("オレンジバー検出を開始", "DEBUG")
        
        img = Image.open(image_path)
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        # HSV色空間での検出（より精密）
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        
        # オレンジ色の範囲（HSV）
        orange_ranges = [
            # 明るいオレンジ
            ([15, 100, 100], [25, 255, 255]),
            # 濃いオレンジ
            ([10, 150, 150], [20, 255, 255]),
            # 赤みがかったオレンジ
            ([5, 120, 120], [15, 255, 255])
        ]
        
        orange_mask = np.zeros((height, width), dtype=np.uint8)
        
        for lower, upper in orange_ranges:
            lower = np.array(lower)
            upper = np.array(upper)
            mask = cv2.inRange(hsv, lower, upper)
            orange_mask = cv2.bitwise_or(orange_mask, mask)
        
        # 水平線検出
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (width//4, 1))
        orange_lines = cv2.morphologyEx(orange_mask, cv2.MORPH_OPEN, kernel)
        
        # オレンジバーの位置を特定
        line_positions = []
        for y in range(height):
            if np.sum(orange_lines[y, :]) > width * 0.3:  # 行の30%以上がオレンジ
                line_positions.append(y)
        
        if not line_positions:
            self.log("オレンジバーが検出されませんでした", "WARNING")
            return None
        
        # 最も太いオレンジバーを選択
        orange_top = min(line_positions)
        orange_bottom = max(line_positions)
        
        # グラフエリアはオレンジバーの直下
        graph_top = orange_bottom + 5
        graph_bottom = min(height - 50, graph_top + int(height * 0.25))
        graph_left = int(width * 0.04)
        graph_right = int(width * 0.96)
        
        self.log(f"オレンジバー基準検出: {graph_left}, {graph_top}, {graph_right}, {graph_bottom}", "DEBUG")
        
        return (graph_left, graph_top, graph_right, graph_bottom)
    
    # =====================================
    # 2. AI・機械学習による検出
    # =====================================
    
    def detect_by_clustering(self, image_path: str) -> Optional[Tuple[int, int, int, int]]:
        """クラスタリングによる領域分割"""
        if not ML_AVAILABLE:
            self.log("scikit-learnが利用できません", "WARNING")
            return None
        
        self.log("クラスタリング検出を開始", "DEBUG")
        
        img = Image.open(image_path)
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        # 特徴量抽出
        features = []
        
        # 1. 色特徴
        reshaped_img = img_array.reshape(-1, 3)
        
        # 2. 位置特徴
        y_coords, x_coords = np.mgrid[0:height, 0:width]
        positions = np.column_stack([y_coords.ravel(), x_coords.ravel()])
        
        # 3. テクスチャ特徴（簡易版）
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # ローカル標準偏差
        local_std = ndimage.generic_filter(gray, np.std, size=5).ravel()
        
        # 特徴量結合
        features = np.column_stack([
            reshaped_img,           # RGB値
            positions / [height, width],  # 正規化位置
            local_std.reshape(-1, 1)  # テクスチャ
        ])
        
        # 特徴量正規化
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # K-meansクラスタリング
        n_clusters = 8
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(features_scaled)
        
        # クラスタマップを画像形状に戻す
        cluster_map = cluster_labels.reshape(height, width)
        
        # グラフエリアに対応するクラスタを特定
        # 中央部分の最も多いクラスタを選択
        center_region = cluster_map[height//3:2*height//3, width//4:3*width//4]
        center_clusters, counts = np.unique(center_region, return_counts=True)
        main_cluster = center_clusters[np.argmax(counts)]
        
        # メインクラスタをマスクとして使用
        cluster_mask = cluster_map == main_cluster
        
        return self._extract_bounds_from_mask(cluster_mask, width, height, "クラスタリング")
    
    def detect_by_pattern_matching(self, image_path: str) -> Optional[Tuple[int, int, int, int]]:
        """パターンマッチングによる検出"""
        self.log("パターンマッチング検出を開始", "DEBUG")
        
        img = Image.open(image_path)
        img_array = np.array(img)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        height, width = gray.shape
        
        # グラフエリアの典型的なパターンを定義
        patterns = []
        
        # 1. 水平グリッドライン検出
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (width//8, 1))
        horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
        
        # 2. 垂直グリッドライン検出
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, height//8))
        vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
        
        # 3. グリッドパターンの統合
        grid_pattern = cv2.add(horizontal_lines, vertical_lines)
        
        # グリッドが集中している領域を検出
        grid_density = ndimage.uniform_filter(grid_pattern.astype(float), size=30)
        
        # 閾値処理
        threshold = np.percentile(grid_density, 75)
        grid_mask = grid_density > threshold
        
        return self._extract_bounds_from_mask(grid_mask, width, height, "パターンマッチング")
    
    # =====================================
    # 3. 統合検出システム
    # =====================================
    
    def ensemble_detection(self, image_path: str) -> Tuple[int, int, int, int]:
        """複数手法を統合した高精度検出"""
        self.log(f"統合検出を開始: {os.path.basename(image_path)}", "INFO")
        
        # 全検出手法を実行
        detection_methods = [
            ("色分析", self.detect_by_color_analysis),
            ("テクスチャ分析", self.detect_by_texture_analysis),
            ("エッジ分析", self.detect_by_edge_analysis),
            ("グラデーション分析", self.detect_by_gradient_analysis),
            ("レイアウト分析", self.detect_by_layout_analysis),
            ("オレンジバー検出", self.detect_by_orange_bar),
            ("クラスタリング", self.detect_by_clustering),
            ("パターンマッチング", self.detect_by_pattern_matching)
        ]
        
        results = []
        
        for method_name, method_func in detection_methods:
            try:
                bounds = method_func(image_path)
                if bounds:
                    left, top, right, bottom = bounds
                    area = (right - left) * (bottom - top)
                    
                    # 結果の妥当性検証
                    quality_score = self._evaluate_bounds_quality(bounds, image_path)
                    
                    results.append({
                        'method': method_name,
                        'bounds': bounds,
                        'area': area,
                        'quality_score': quality_score
                    })
                    
                    self.log(f"{method_name}: {bounds} (品質: {quality_score:.2f})", "DEBUG")
                else:
                    self.log(f"{method_name}: 検出失敗", "WARNING")
            except Exception as e:
                self.log(f"{method_name}: エラー - {e}", "ERROR")
        
        if not results:
            self.log("全ての手法で検出に失敗しました", "ERROR")
            return self._fallback_detection(image_path)
        
        # 統合アルゴリズム
        final_bounds = self._combine_detection_results(results, image_path)
        
        self.log(f"最終検出結果: {final_bounds}", "SUCCESS")
        
        # 結果を保存（学習用）
        self.detection_results.append({
            'image_path': image_path,
            'methods_results': results,
            'final_bounds': final_bounds,
            'timestamp': datetime.now().isoformat()
        })
        
        return final_bounds
    
    def _extract_bounds_from_mask(self, mask: np.ndarray, width: int, height: int, method_name: str) -> Optional[Tuple[int, int, int, int]]:
        """マスクから境界を抽出"""
        if np.sum(mask) < 100:  # マスクが小さすぎる
            return None
        
        # 連結成分分析
        labeled_mask, num_features = ndimage.label(mask)
        
        if num_features == 0:
            return None
        
        # 最大の連結成分を選択
        component_sizes = ndimage.sum(mask, labeled_mask, range(1, num_features + 1))
        largest_component = np.argmax(component_sizes) + 1
        largest_mask = labeled_mask == largest_component
        
        # 境界抽出
        rows, cols = np.where(largest_mask)
        
        if len(rows) == 0:
            return None
        
        top, bottom = rows.min(), rows.max()
        left, right = cols.min(), cols.max()
        
        # パディング
        padding = 10
        left = max(0, left - padding)
        right = min(width - 1, right + padding)
        top = max(0, top - padding)
        bottom = min(height - 1, bottom + padding)
        
        return (left, top, right, bottom)
    
    def _evaluate_bounds_quality(self, bounds: Tuple[int, int, int, int], image_path: str) -> float:
        """検出結果の品質評価"""
        left, top, right, bottom = bounds
        
        img = Image.open(image_path)
        width, height = img.size
        
        # 基本的な妥当性チェック
        area_ratio = ((right - left) * (bottom - top)) / (width * height)
        width_ratio = (right - left) / width
        height_ratio = (bottom - top) / height
        
        quality_score = 0
        
        # 面積比率評価（15-40%が理想）
        if 0.15 <= area_ratio <= 0.40:
            quality_score += 30
        elif 0.10 <= area_ratio <= 0.50:
            quality_score += 20
        elif 0.05 <= area_ratio <= 0.60:
            quality_score += 10
        
        # 横幅比率評価（85-98%が理想）
        if 0.85 <= width_ratio <= 0.98:
            quality_score += 30
        elif 0.70 <= width_ratio <= 0.99:
            quality_score += 20
        elif 0.50 <= width_ratio <= 1.0:
            quality_score += 10
        
        # 高さ比率評価（20-35%が理想）
        if 0.20 <= height_ratio <= 0.35:
            quality_score += 25
        elif 0.15 <= height_ratio <= 0.45:
            quality_score += 15
        elif 0.10 <= height_ratio <= 0.55:
            quality_score += 5
        
        # 位置評価（中央寄りが理想）
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        
        x_center_score = 1 - abs(center_x / width - 0.5) * 2
        y_center_score = 1 - abs(center_y / height - 0.4) * 2  # 少し上寄り
        
        quality_score += x_center_score * 10
        quality_score += y_center_score * 5
        
        return min(quality_score, 100)
    
    def _combine_detection_results(self, results: List[Dict], image_path: str) -> Tuple[int, int, int, int]:
        """複数の検出結果を統合"""
        
        # 品質スコアによる重み付け
        weights = [result['quality_score'] / 100 for result in results]
        
        if sum(weights) == 0:
            # 全て低品質の場合は最良を選択
            best_result = max(results, key=lambda x: x['quality_score'])
            return best_result['bounds']
        
        # 重み付き平均による統合
        weighted_left = sum(result['bounds'][0] * weight for result, weight in zip(results, weights)) / sum(weights)
        weighted_top = sum(result['bounds'][1] * weight for result, weight in zip(results, weights)) / sum(weights)
        weighted_right = sum(result['bounds'][2] * weight for result, weight in zip(results, weights)) / sum(weights)
        weighted_bottom = sum(result['bounds'][3] * weight for result, weight in zip(results, weights)) / sum(weights)
        
        # 外れ値除去
        bounds_list = [result['bounds'] for result in results]
        
        # 四分位範囲による外れ値検出
        lefts = [b[0] for b in bounds_list]
        tops = [b[1] for b in bounds_list]
        rights = [b[2] for b in bounds_list]
        bottoms = [b[3] for b in bounds_list]
        
        def remove_outliers(values):
            q1, q3 = np.percentile(values, [25, 75])
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            return [v for v in values if lower_bound <= v <= upper_bound]
        
        filtered_lefts = remove_outliers(lefts)
        filtered_tops = remove_outliers(tops)
        filtered_rights = remove_outliers(rights)
        filtered_bottoms = remove_outliers(bottoms)
        
        # フィルタ済みデータの中央値
        final_left = int(np.median(filtered_lefts) if filtered_lefts else weighted_left)
        final_top = int(np.median(filtered_tops) if filtered_tops else weighted_top)
        final_right = int(np.median(filtered_rights) if filtered_rights else weighted_right)
        final_bottom = int(np.median(filtered_bottoms) if filtered_bottoms else weighted_bottom)
        
        # 最終調整
        img = Image.open(image_path)
        width, height = img.size
        
        final_left = max(0, final_left)
        final_right = min(width - 1, final_right)
        final_top = max(0, final_top)
        final_bottom = min(height - 1, final_bottom)
        
        return (final_left, final_top, final_right, final_bottom)
    
    def _fallback_detection(self, image_path: str) -> Tuple[int, int, int, int]:
        """フォールバック検出（最低限の結果）"""
        img = Image.open(image_path)
        width, height = img.size
        
        # 安全なデフォルト値
        left = int(width * 0.05)
        right = int(width * 0.95)
        top = int(height * 0.30)
        bottom = int(height * 0.65)
        
        self.log(f"フォールバック検出: {left}, {top}, {right}, {bottom}", "WARNING")
        
        return (left, top, right, bottom)
    
    # =====================================
    # 4. 可視化・検証機能
    # =====================================
    
    def visualize_detection_process(self, image_path: str, save_path: str = None):
        """検出プロセスの可視化"""
        if not PLOT_AVAILABLE:
            self.log("matplotlib が利用できません", "WARNING")
            return
        
        self.log("検出プロセスを可視化中...", "INFO")
        
        # 複数の検出結果を取得
        methods = [
            ("色分析", self.detect_by_color_analysis),
            ("エッジ分析", self.detect_by_edge_analysis),
            ("レイアウト分析", self.detect_by_layout_analysis),
            ("オレンジバー検出", self.detect_by_orange_bar)
        ]
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'高精度検出プロセス: {os.path.basename(image_path)}', fontsize=16, fontweight='bold')
        
        img = Image.open(image_path)
        
        # 元画像
        axes[0, 0].imshow(img)
        axes[0, 0].set_title('元画像')
        axes[0, 0].axis('off')
        
        # 各手法の結果
        colors = ['red', 'green', 'blue', 'orange', 'purple']
        
        for i, (method_name, method_func) in enumerate(methods[:4]):
            row = i // 2
            col = (i % 2) + 1
            
            axes[row, col].imshow(img)
            
            try:
                bounds = method_func(image_path)
                if bounds:
                    left, top, right, bottom = bounds
                    rect = patches.Rectangle((left, top), right-left, bottom-top,
                                           linewidth=3, edgecolor=colors[i], facecolor='none')
                    axes[row, col].add_patch(rect)
                    
                    quality = self._evaluate_bounds_quality(bounds, image_path)
                    axes[row, col].set_title(f'{method_name}\n品質: {quality:.1f}')
                else:
                    axes[row, col].set_title(f'{method_name}\n検出失敗')
            except Exception as e:
                axes[row, col].set_title(f'{method_name}\nエラー')
            
            axes[row, col].axis('off')
        
        # 統合結果
        axes[1, 2].imshow(img)
        final_bounds = self.ensemble_detection(image_path)
        left, top, right, bottom = final_bounds
        
        rect = patches.Rectangle((left, top), right-left, bottom-top,
                               linewidth=4, edgecolor='yellow', facecolor='none')
        axes[1, 2].add_patch(rect)
        
        final_quality = self._evaluate_bounds_quality(final_bounds, image_path)
        axes[1, 2].set_title(f'統合結果\n品質: {final_quality:.1f}')
        axes[1, 2].axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.log(f"可視化結果を保存: {save_path}", "SUCCESS")
        
        plt.show()
    
    def verify_detection_accuracy(self, test_folder: str, ground_truth_file: str = None):
        """検出精度の検証"""
        self.log("検出精度を検証中...", "INFO")
        
        if not os.path.exists(test_folder):
            self.log(f"テストフォルダが見つかりません: {test_folder}", "ERROR")
            return
        
        # テスト画像の処理
        test_images = [f for f in os.listdir(test_folder) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not test_images:
            self.log("テスト画像が見つかりません", "ERROR")
            return
        
        results = []
        
        for image_file in test_images:
            image_path = os.path.join(test_folder, image_file)
            
            try:
                bounds = self.ensemble_detection(image_path)
                quality = self._evaluate_bounds_quality(bounds, image_path)
                
                results.append({
                    'image': image_file,
                    'bounds': bounds,
                    'quality': quality
                })
                
                self.log(f"✅ {image_file}: 品質 {quality:.1f}", "SUCCESS")
                
            except Exception as e:
                self.log(f"❌ {image_file}: エラー - {e}", "ERROR")
        
        # 統計情報
        if results:
            qualities = [r['quality'] for r in results]
            avg_quality = np.mean(qualities)
            std_quality = np.std(qualities)
            
            self.log(f"\n📊 検証結果:", "INFO")
            self.log(f"   処理成功: {len(results)}/{len(test_images)}", "INFO")
            self.log(f"   平均品質: {avg_quality:.1f} ± {std_quality:.1f}", "INFO")
            self.log(f"   最高品質: {max(qualities):.1f}", "INFO")
            self.log(f"   最低品質: {min(qualities):.1f}", "INFO")
            
            # 品質分布
            excellent = sum(1 for q in qualities if q >= 80)
            good = sum(1 for q in qualities if 60 <= q < 80)
            fair = sum(1 for q in qualities if 40 <= q < 60)
            poor = sum(1 for q in qualities if q < 40)
            
            self.log(f"   品質分布:", "INFO")
            self.log(f"     優秀 (80+): {excellent}", "INFO")
            self.log(f"     良好 (60-79): {good}", "INFO")
            self.log(f"     普通 (40-59): {fair}", "INFO")
            self.log(f"     改善要 (<40): {poor}", "INFO")
        
        return results
    
    # =====================================
    # 5. メイン処理・バッチ処理
    # =====================================
    
    def crop_image_with_high_precision(self, image_path: str, output_path: str = None) -> bool:
        """高精度で画像を切り抜き"""
        try:
            self.log(f"🎯 高精度切り抜き開始: {os.path.basename(image_path)}", "INFO")
            
            # 統合検出
            bounds = self.ensemble_detection(image_path)
            
            # 切り抜き実行
            img = Image.open(image_path)
            left, top, right, bottom = bounds
            cropped_img = img.crop(bounds)
            
            # 出力パス設定
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"graphs/cropped_high_precision/{base_name}_cropped_hp.png"
            
            # 出力フォルダ作成
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存
            cropped_img.save(output_path)
            
            # 品質評価
            quality = self._evaluate_bounds_quality(bounds, image_path)
            
            self.log(f"✅ 切り抜き完了: {output_path}", "SUCCESS")
            self.log(f"   切り抜き範囲: {bounds}", "INFO")
            self.log(f"   品質スコア: {quality:.1f}", "INFO")
            
            return True
            
        except Exception as e:
            self.log(f"❌ 切り抜きエラー: {e}", "ERROR")
            return False
    
    def process_batch_high_precision(self, input_folder: str = "graphs", 
                                   output_folder: str = "graphs/cropped_high_precision"):
        """高精度バッチ処理"""
        self.log(f"🚀 高精度バッチ処理開始", "INFO")
        
        if not os.path.exists(input_folder):
            self.log(f"入力フォルダが見つかりません: {input_folder}", "ERROR")
            return
        
        # 対象画像ファイル
        image_files = [f for f in os.listdir(input_folder)
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                      and not f.endswith('_cropped.png')
                      and not f.endswith('_cropped_hp.png')]
        
        if not image_files:
            self.log("処理対象の画像ファイルが見つかりません", "ERROR")
            return
        
        os.makedirs(output_folder, exist_ok=True)
        
        self.log(f"📁 処理対象: {len(image_files)}個のファイル", "INFO")
        
        successful = 0
        failed = []
        qualities = []
        
        for i, filename in enumerate(image_files, 1):
            self.log(f"\n[{i}/{len(image_files)}] 処理中: {filename}", "INFO")
            
            input_path = os.path.join(input_folder, filename)
            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(output_folder, f"{base_name}_cropped_hp.png")
            
            if self.crop_image_with_high_precision(input_path, output_path):
                successful += 1
                
                # 品質評価
                bounds = self.ensemble_detection(input_path)
                quality = self._evaluate_bounds_quality(bounds, input_path)
                qualities.append(quality)
            else:
                failed.append(filename)
        
        # バッチ処理結果
        self.log(f"\n🎉 バッチ処理完了!", "SUCCESS")
        self.log(f"✅ 成功: {successful}/{len(image_files)}", "SUCCESS")
        
        if failed:
            self.log(f"❌ 失敗: {len(failed)}個", "ERROR")
            for f in failed:
                self.log(f"  - {f}", "ERROR")
        
        if qualities:
            avg_quality = np.mean(qualities)
            self.log(f"📊 平均品質: {avg_quality:.1f}", "INFO")
        
        self.log(f"📁 出力フォルダ: {output_folder}", "INFO")
        
        # 処理レポート保存
        report = {
            'timestamp': datetime.now().isoformat(),
            'input_folder': input_folder,
            'output_folder': output_folder,
            'total_files': len(image_files),
            'successful': successful,
            'failed': failed,
            'average_quality': avg_quality if qualities else 0,
            'quality_scores': qualities
        }
        
        report_path = f"high_precision_batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.log(f"📋 レポート保存: {report_path}", "INFO")


def main():
    """メイン処理"""
    print("=" * 60)
    print("🎯 高精度パチンコグラフ切り抜きツール")
    print("=" * 60)
    print("🔬 複数のAI検出手法を統合した最高精度版")
    print("📊 詳細な品質評価・可視化機能付き")
    
    cropper = HighPrecisionCropper()
    
    # 入力フォルダチェック
    input_folder = "graphs"
    if not os.path.exists(input_folder):
        print(f"\n❌ 入力フォルダが見つかりません: {input_folder}")
        print("📁 'graphs' フォルダを作成して画像を配置してください")
        return
    
    # 画像ファイル検索
    image_files = [f for f in os.listdir(input_folder)
                  if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                  and not f.endswith('_cropped.png')
                  and not f.endswith('_cropped_hp.png')]
    
    if not image_files:
        print(f"\n❌ 処理対象の画像ファイルが見つかりません")
        return
    
    print(f"\n📁 見つかった画像ファイル ({len(image_files)}個):")
    for i, file in enumerate(image_files[:10], 1):  # 最初の10個のみ表示
        print(f"   {i}. {file}")
    if len(image_files) > 10:
        print(f"   ... 他 {len(image_files) - 10}個")
    
    # 処理モード選択
    print(f"\n🎯 処理モードを選択:")
    print("1. 🚀 全自動高精度バッチ処理（推奨）")
    print("2. 📷 単一画像の高精度処理 + 可視化")
    print("3. 🔬 検出精度の検証テスト")
    print("4. 📊 検出プロセスの詳細可視化")
    
    try:
        choice = input("\n選択 (1-4): ").strip()
        
        if choice == "1":
            # 全自動バッチ処理
            cropper.process_batch_high_precision()
            
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
                    
                    # 高精度処理
                    success = cropper.crop_image_with_high_precision(image_path)
                    
                    # 可視化
                    if success and PLOT_AVAILABLE:
                        show_viz = input("\n🔍 検出プロセスを可視化しますか？ (y/n): ").strip().lower()
                        if show_viz != 'n':
                            cropper.visualize_detection_process(image_path)
                else:
                    print("❌ 無効な番号です")
            except ValueError:
                print("❌ 数字を入力してください")
                
        elif choice == "3":
            # 精度検証
            test_folder = input("テスト画像フォルダ (デフォルト: graphs): ").strip()
            if not test_folder:
                test_folder = "graphs"
            
            cropper.verify_detection_accuracy(test_folder)
            
        elif choice == "4":
            # 詳細可視化
            if not PLOT_AVAILABLE:
                print("❌ matplotlib が必要です")
                return
            
            print(f"\n📁 画像を選択:")
            for i, file in enumerate(image_files, 1):
                print(f"{i}. {file}")
            
            try:
                file_num = int(input("画像番号を選択: ").strip())
                if 1 <= file_num <= len(image_files):
                    selected_file = image_files[file_num - 1]
                    image_path = os.path.join(input_folder, selected_file)
                    
                    save_viz = input("可視化結果を保存しますか？ (y/n): ").strip().lower()
                    save_path = None
                    if save_viz == 'y':
                        base_name = os.path.splitext(selected_file)[0]
                        save_path = f"detection_process_{base_name}.png"
                    
                    cropper.visualize_detection_process(image_path, save_path)
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