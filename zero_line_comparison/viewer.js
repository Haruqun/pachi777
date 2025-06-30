// 複数画像比較ビューワー JavaScript

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
document.addEventListener('DOMContentLoaded', init);