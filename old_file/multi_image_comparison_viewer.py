#!/usr/bin/env python3
"""
複数画像比較ビューワー
ゼロライン検出結果やスケールテスト結果を一括で比較表示
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

class MultiImageComparisonViewer:
    """複数画像比較ビューワークラス"""
    
    def __init__(self, output_dir="comparison_viewer"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
    
    def generate_comparison_html(self, test_name, image_sets):
        """比較用HTMLを生成
        
        Args:
            test_name: テスト名
            image_sets: [
                {
                    'name': '画像名',
                    'original': '元画像パス',
                    'results': [
                        {'label': 'Method 1', 'path': '結果画像パス1', 'data': {...}},
                        {'label': 'Method 2', 'path': '結果画像パス2', 'data': {...}}
                    ]
                }
            ]
        """
        
        # 画像をコピー
        for img_set in image_sets:
            # 元画像
            if 'original' in img_set and os.path.exists(img_set['original']):
                dest_name = f"{img_set['name']}_original.png"
                dest_path = os.path.join(self.output_dir, "images", dest_name)
                shutil.copy2(img_set['original'], dest_path)
                img_set['original_web'] = f"images/{dest_name}"
            
            # 結果画像
            for i, result in enumerate(img_set.get('results', [])):
                if 'path' in result and os.path.exists(result['path']):
                    dest_name = f"{img_set['name']}_{i}_{result['label'].replace(' ', '_')}.png"
                    dest_path = os.path.join(self.output_dir, "images", dest_name)
                    shutil.copy2(result['path'], dest_path)
                    result['web_path'] = f"images/{dest_name}"
        
        # HTML生成
        html_content = self._generate_html_content(test_name, image_sets)
        
        # JavaScript生成
        js_content = self._generate_js_content()
        
        # CSS生成
        css_content = self._generate_css_content()
        
        # ファイル保存
        with open(os.path.join(self.output_dir, "index.html"), 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        with open(os.path.join(self.output_dir, "viewer.js"), 'w', encoding='utf-8') as f:
            f.write(js_content)
        
        with open(os.path.join(self.output_dir, "viewer.css"), 'w', encoding='utf-8') as f:
            f.write(css_content)
        
        # データをJSONで保存
        with open(os.path.join(self.output_dir, "data.json"), 'w', encoding='utf-8') as f:
            json.dump({
                'test_name': test_name,
                'timestamp': datetime.now().isoformat(),
                'image_sets': image_sets
            }, f, ensure_ascii=False, indent=2)
        
        print(f"比較ビューワー生成完了: {os.path.join(self.output_dir, 'index.html')}")
    
    def _generate_html_content(self, test_name, image_sets):
        """HTML内容を生成"""
        return f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{test_name} - 複数画像比較ビューワー</title>
    <link rel="stylesheet" href="viewer.css">
</head>
<body>
    <header>
        <h1>🔍 {test_name}</h1>
        <div class="controls">
            <button onclick="toggleSync()" class="btn btn-primary">
                <span id="sync-icon">🔗</span> 同期: <span id="sync-status">ON</span>
            </button>
            <button onclick="resetZoom()" class="btn">🔄 ズームリセット</button>
            <button onclick="toggleOverlay()" class="btn">
                <span id="overlay-icon">👁️</span> オーバーレイ: <span id="overlay-status">OFF</span>
            </button>
        </div>
    </header>
    
    <main>
        <div class="image-grid" id="imageGrid">
            <!-- 画像セットはJavaScriptで動的に生成 -->
        </div>
    </main>
    
    <aside class="sidebar">
        <h2>画像リスト</h2>
        <div id="imageList" class="image-list">
            <!-- 画像リストはJavaScriptで動的に生成 -->
        </div>
        
        <h2>比較モード</h2>
        <div class="comparison-modes">
            <label>
                <input type="radio" name="mode" value="grid" checked onchange="changeMode('grid')">
                グリッド表示
            </label>
            <label>
                <input type="radio" name="mode" value="slider" onchange="changeMode('slider')">
                スライダー比較
            </label>
            <label>
                <input type="radio" name="mode" value="diff" onchange="changeMode('diff')">
                差分表示
            </label>
        </div>
        
        <h2>詳細データ</h2>
        <div id="detailData" class="detail-data">
            <p>画像を選択してください</p>
        </div>
    </aside>
    
    <script src="viewer.js"></script>
</body>
</html>'''
    
    def _generate_js_content(self):
        """JavaScript内容を生成"""
        return '''// 複数画像比較ビューワー JavaScript

let imageData = null;
let syncEnabled = true;
let overlayEnabled = false;
let currentMode = 'grid';
let zoomLevel = 1;
let panX = 0;
let panY = 0;

// 初期化
async function init() {
    try {
        const response = await fetch('data.json');
        const data = await response.json();
        imageData = data.image_sets;
        renderImageGrid();
        renderImageList();
    } catch (error) {
        console.error('データ読み込みエラー:', error);
    }
}

// 画像グリッドを描画
function renderImageGrid() {
    const grid = document.getElementById('imageGrid');
    grid.innerHTML = '';
    
    imageData.forEach((imgSet, index) => {
        const setDiv = document.createElement('div');
        setDiv.className = 'image-set';
        setDiv.innerHTML = `
            <h3>${imgSet.name}</h3>
            <div class="image-row">
                ${imgSet.original_web ? `
                    <div class="image-container" onclick="selectImage(${index}, 'original')">
                        <img src="${imgSet.original_web}" alt="Original">
                        <div class="image-label">元画像</div>
                    </div>
                ` : ''}
                ${imgSet.results.map((result, i) => `
                    <div class="image-container" onclick="selectImage(${index}, ${i})">
                        <img src="${result.web_path}" alt="${result.label}">
                        <div class="image-label">${result.label}</div>
                    </div>
                `).join('')}
            </div>
        `;
        grid.appendChild(setDiv);
    });
    
    // ズーム・パン機能を追加
    addZoomPanListeners();
}

// 画像リストを描画
function renderImageList() {
    const list = document.getElementById('imageList');
    list.innerHTML = imageData.map((imgSet, index) => `
        <div class="list-item ${index === 0 ? 'active' : ''}" onclick="scrollToImage(${index})">
            📷 ${imgSet.name}
        </div>
    `).join('');
}

// 画像選択
function selectImage(setIndex, resultIndex) {
    const imgSet = imageData[setIndex];
    const detailDiv = document.getElementById('detailData');
    
    let data = {};
    let label = '';
    
    if (resultIndex === 'original') {
        label = '元画像';
    } else {
        const result = imgSet.results[resultIndex];
        label = result.label;
        data = result.data || {};
    }
    
    detailDiv.innerHTML = `
        <h4>${imgSet.name} - ${label}</h4>
        ${Object.entries(data).map(([key, value]) => `
            <div class="data-item">
                <span class="data-key">${key}:</span>
                <span class="data-value">${JSON.stringify(value)}</span>
            </div>
        `).join('')}
    `;
}

// 同期切り替え
function toggleSync() {
    syncEnabled = !syncEnabled;
    document.getElementById('sync-status').textContent = syncEnabled ? 'ON' : 'OFF';
    document.getElementById('sync-icon').textContent = syncEnabled ? '🔗' : '🔓';
}

// オーバーレイ切り替え
function toggleOverlay() {
    overlayEnabled = !overlayEnabled;
    document.getElementById('overlay-status').textContent = overlayEnabled ? 'ON' : 'OFF';
    document.getElementById('overlay-icon').textContent = overlayEnabled ? '👁️' : '👁️‍🗨️';
    
    if (overlayEnabled) {
        enableOverlay();
    } else {
        disableOverlay();
    }
}

// モード変更
function changeMode(mode) {
    currentMode = mode;
    const grid = document.getElementById('imageGrid');
    
    switch(mode) {
        case 'grid':
            grid.className = 'image-grid';
            renderImageGrid();
            break;
        case 'slider':
            renderSliderMode();
            break;
        case 'diff':
            renderDiffMode();
            break;
    }
}

// ズームリセット
function resetZoom() {
    zoomLevel = 1;
    panX = 0;
    panY = 0;
    updateAllImageTransforms();
}

// ズーム・パン機能
function addZoomPanListeners() {
    const containers = document.querySelectorAll('.image-container');
    
    containers.forEach(container => {
        const img = container.querySelector('img');
        let isDragging = false;
        let startX, startY;
        
        // マウスホイールでズーム
        container.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            zoomLevel *= delta;
            zoomLevel = Math.max(0.5, Math.min(5, zoomLevel));
            
            if (syncEnabled) {
                updateAllImageTransforms();
            } else {
                updateImageTransform(img);
            }
        });
        
        // ドラッグでパン
        container.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX - panX;
            startY = e.clientY - panY;
            container.style.cursor = 'grabbing';
        });
        
        container.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            panX = e.clientX - startX;
            panY = e.clientY - startY;
            
            if (syncEnabled) {
                updateAllImageTransforms();
            } else {
                updateImageTransform(img);
            }
        });
        
        container.addEventListener('mouseup', () => {
            isDragging = false;
            container.style.cursor = 'grab';
        });
    });
}

// 画像変換を更新
function updateImageTransform(img) {
    img.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomLevel})`;
}

// 全画像の変換を更新
function updateAllImageTransforms() {
    const images = document.querySelectorAll('.image-container img');
    images.forEach(img => updateImageTransform(img));
}

// 画像へスクロール
function scrollToImage(index) {
    const imageSets = document.querySelectorAll('.image-set');
    if (imageSets[index]) {
        imageSets[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // アクティブ状態を更新
        document.querySelectorAll('.list-item').forEach((item, i) => {
            item.classList.toggle('active', i === index);
        });
    }
}

// スライダーモードを描画
function renderSliderMode() {
    const grid = document.getElementById('imageGrid');
    grid.className = 'image-grid slider-mode';
    grid.innerHTML = '<div class="slider-container">スライダーモード（実装予定）</div>';
}

// 差分モードを描画
function renderDiffMode() {
    const grid = document.getElementById('imageGrid');
    grid.className = 'image-grid diff-mode';
    grid.innerHTML = '<div class="diff-container">差分モード（実装予定）</div>';
}

// オーバーレイ有効化
function enableOverlay() {
    // 実装予定：画像を重ねて表示
}

// オーバーレイ無効化
function disableOverlay() {
    // 実装予定：オーバーレイを解除
}

// ページ読み込み時に初期化
document.addEventListener('DOMContentLoaded', init);'''
    
    def _generate_css_content(self):
        """CSS内容を生成"""
        return '''/* 複数画像比較ビューワー CSS */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Hiragino Sans', 'Meiryo', sans-serif;
    background-color: #1a1a1a;
    color: #ffffff;
    display: grid;
    grid-template-columns: 1fr 300px;
    grid-template-rows: auto 1fr;
    height: 100vh;
    overflow: hidden;
}

header {
    grid-column: 1 / -1;
    background-color: #2a2a2a;
    padding: 20px;
    border-bottom: 2px solid #444;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

h1 {
    font-size: 24px;
    color: #ffffff;
}

.controls {
    display: flex;
    gap: 10px;
}

.btn {
    background-color: #444;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.3s;
}

.btn:hover {
    background-color: #555;
}

.btn-primary {
    background-color: #007bff;
}

.btn-primary:hover {
    background-color: #0056b3;
}

main {
    overflow-y: auto;
    padding: 20px;
    background-color: #1a1a1a;
}

.sidebar {
    background-color: #2a2a2a;
    padding: 20px;
    overflow-y: auto;
    border-left: 1px solid #444;
}

.sidebar h2 {
    font-size: 18px;
    margin-bottom: 15px;
    color: #ddd;
}

.image-grid {
    display: flex;
    flex-direction: column;
    gap: 30px;
}

.image-set {
    background-color: #2a2a2a;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

.image-set h3 {
    font-size: 20px;
    margin-bottom: 15px;
    color: #ffffff;
}

.image-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 15px;
}

.image-container {
    position: relative;
    background-color: #1a1a1a;
    border-radius: 4px;
    overflow: hidden;
    cursor: grab;
    transition: transform 0.2s;
}

.image-container:hover {
    transform: scale(1.02);
    box-shadow: 0 0 20px rgba(0, 123, 255, 0.5);
}

.image-container img {
    width: 100%;
    height: auto;
    display: block;
    transition: transform 0.1s;
}

.image-label {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 8px;
    font-size: 14px;
    text-align: center;
}

.image-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 30px;
}

.list-item {
    padding: 10px;
    background-color: #333;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
    font-size: 14px;
}

.list-item:hover {
    background-color: #444;
}

.list-item.active {
    background-color: #007bff;
}

.comparison-modes {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 30px;
}

.comparison-modes label {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    font-size: 14px;
}

.detail-data {
    background-color: #333;
    border-radius: 4px;
    padding: 15px;
    font-size: 14px;
}

.detail-data h4 {
    margin-bottom: 10px;
    color: #007bff;
}

.data-item {
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    border-bottom: 1px solid #444;
}

.data-key {
    color: #aaa;
}

.data-value {
    color: #fff;
    font-family: monospace;
}

/* スライダーモード */
.slider-mode .slider-container {
    height: 600px;
    background-color: #333;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #666;
}

/* 差分モード */
.diff-mode .diff-container {
    height: 600px;
    background-color: #333;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #666;
}

/* スクロールバー */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: #1a1a1a;
}

::-webkit-scrollbar-thumb {
    background: #444;
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #555;
}'''

# 使用例
def create_zero_line_comparison():
    """ゼロライン検出の比較ビューワーを作成"""
    viewer = MultiImageComparisonViewer("zero_line_comparison")
    
    # テスト画像を収集
    test_images = list(Path("graphs/manual_crop/cropped").glob("*.png"))[:5]  # 最初の5枚
    
    image_sets = []
    
    for img_path in test_images:
        img_set = {
            'name': img_path.stem,
            'original': str(img_path),
            'results': []
        }
        
        # 各検出結果を追加（存在する場合）
        detection_result_path = f"zero_detection_results/{img_path.stem}_detection.png"
        if os.path.exists(detection_result_path):
            img_set['results'].append({
                'label': '検出結果',
                'path': detection_result_path,
                'data': {
                    'method': 'advanced_detection',
                    'zero_line': 260  # 実際の検出結果を使用
                }
            })
        
        # スケールテスト結果も追加（存在する場合）
        for scale in [115, 120, 125]:
            scale_test_path = f"test_results/scale_test_{scale}_{img_path.name}"
            if os.path.exists(scale_test_path):
                img_set['results'].append({
                    'label': f'Scale {scale}',
                    'path': scale_test_path,
                    'data': {
                        'scale': scale,
                        'pixel_per_value': scale
                    }
                })
        
        if img_set['results']:  # 結果がある場合のみ追加
            image_sets.append(img_set)
    
    # HTML生成
    viewer.generate_comparison_html("ゼロライン検出＆スケールテスト比較", image_sets)

if __name__ == "__main__":
    create_zero_line_comparison()