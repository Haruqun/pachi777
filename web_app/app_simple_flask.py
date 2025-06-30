#!/usr/bin/env python3
"""
シンプルなFlask版API
より軽量で、どこでも動作する
"""

from flask import Flask, request, jsonify, send_file, render_template_string
import tempfile
import os
import sys
from pathlib import Path
import zipfile
from datetime import datetime
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB

# 処理中のジョブを管理
processing_jobs = {}

# HTMLテンプレート
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>パチンコグラフ解析システム</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #4CAF50;
            text-align: center;
            margin-bottom: 30px;
        }
        .upload-area {
            border: 3px dashed #4CAF50;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            margin-bottom: 20px;
            transition: all 0.3s;
            cursor: pointer;
        }
        .upload-area:hover {
            background-color: #f0f8ff;
            border-color: #45a049;
        }
        .upload-area.dragover {
            background-color: #e8f5e9;
            border-color: #45a049;
        }
        #fileInput {
            display: none;
        }
        .file-list {
            margin: 20px 0;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 5px;
        }
        .file-item {
            padding: 5px;
            margin: 5px 0;
            background: white;
            border-radius: 3px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 12px 30px;
            font-size: 16px;
            border-radius: 5px;
            cursor: pointer;
            width: 100%;
            transition: all 0.3s;
        }
        button:hover {
            background-color: #45a049;
            transform: translateY(-2px);
        }
        button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .progress {
            width: 100%;
            height: 30px;
            background-color: #f0f0f0;
            border-radius: 15px;
            margin: 20px 0;
            overflow: hidden;
            display: none;
        }
        .progress-bar {
            height: 100%;
            background-color: #4CAF50;
            width: 0%;
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .results {
            margin-top: 30px;
            padding: 20px;
            background: #e8f5e9;
            border-radius: 10px;
            display: none;
        }
        .download-btn {
            background-color: #2196F3;
            margin: 10px 0;
        }
        .download-btn:hover {
            background-color: #1976D2;
        }
        .error {
            color: #d32f2f;
            padding: 10px;
            background: #ffebee;
            border-radius: 5px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎰 パチンコグラフ解析システム</h1>
        
        <div class="upload-area" onclick="document.getElementById('fileInput').click()">
            <p style="font-size: 24px; margin: 0;">📸</p>
            <p>画像をドラッグ&ドロップ<br>またはクリックして選択</p>
            <input type="file" id="fileInput" multiple accept="image/*">
        </div>
        
        <div class="file-list" id="fileList" style="display: none;">
            <h3>選択されたファイル:</h3>
            <div id="fileItems"></div>
        </div>
        
        <button id="uploadBtn" onclick="uploadFiles()" disabled>
            🚀 解析開始
        </button>
        
        <div class="progress" id="progress">
            <div class="progress-bar" id="progressBar">0%</div>
        </div>
        
        <div id="error" class="error" style="display: none;"></div>
        
        <div class="results" id="results">
            <h3>✅ 解析完了！</h3>
            <p id="resultText"></p>
            <button class="download-btn" id="downloadReport" style="display: none;">
                📄 レポートをダウンロード
            </button>
            <button class="download-btn" id="downloadZip" style="display: none;">
                📦 ZIPパッケージをダウンロード
            </button>
        </div>
    </div>
    
    <script>
        let selectedFiles = [];
        let currentJobId = null;
        
        // ドラッグ&ドロップ設定
        const uploadArea = document.querySelector('.upload-area');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight(e) {
            uploadArea.classList.add('dragover');
        }
        
        function unhighlight(e) {
            uploadArea.classList.remove('dragover');
        }
        
        uploadArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        }
        
        // ファイル選択
        document.getElementById('fileInput').addEventListener('change', function(e) {
            handleFiles(e.target.files);
        });
        
        function handleFiles(files) {
            selectedFiles = Array.from(files);
            displayFiles();
            document.getElementById('uploadBtn').disabled = selectedFiles.length === 0;
        }
        
        function displayFiles() {
            const fileList = document.getElementById('fileList');
            const fileItems = document.getElementById('fileItems');
            
            if (selectedFiles.length > 0) {
                fileList.style.display = 'block';
                fileItems.innerHTML = selectedFiles.map(file => 
                    `<div class="file-item">📸 ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)</div>`
                ).join('');
            } else {
                fileList.style.display = 'none';
            }
        }
        
        // アップロードと処理
        async function uploadFiles() {
            if (selectedFiles.length === 0) return;
            
            const formData = new FormData();
            selectedFiles.forEach(file => {
                formData.append('images', file);
            });
            
            // UI更新
            document.getElementById('uploadBtn').disabled = true;
            document.getElementById('progress').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            document.getElementById('results').style.display = 'none';
            
            updateProgress(10, '画像をアップロード中...');
            
            try {
                // アップロードと処理開始
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('アップロードに失敗しました');
                }
                
                const data = await response.json();
                currentJobId = data.job_id;
                
                // 進捗確認
                checkProgress();
                
            } catch (error) {
                showError(error.message);
                resetUI();
            }
        }
        
        async function checkProgress() {
            try {
                const response = await fetch(`/api/status/${currentJobId}`);
                const data = await response.json();
                
                if (data.status === 'processing') {
                    updateProgress(data.progress * 100, data.message);
                    setTimeout(checkProgress, 1000);
                } else if (data.status === 'completed') {
                    updateProgress(100, '完了！');
                    showResults(data);
                } else if (data.status === 'error') {
                    throw new Error(data.error);
                }
            } catch (error) {
                showError(error.message);
                resetUI();
            }
        }
        
        function updateProgress(percent, message) {
            const progressBar = document.getElementById('progressBar');
            progressBar.style.width = percent + '%';
            progressBar.textContent = message || percent + '%';
        }
        
        function showResults(data) {
            document.getElementById('results').style.display = 'block';
            document.getElementById('resultText').textContent = 
                `${data.processed_count}枚の画像を処理しました。`;
            
            // ダウンロードボタン設定
            if (data.report_url) {
                const reportBtn = document.getElementById('downloadReport');
                reportBtn.style.display = 'block';
                reportBtn.onclick = () => window.location.href = data.report_url;
            }
            
            if (data.zip_url) {
                const zipBtn = document.getElementById('downloadZip');
                zipBtn.style.display = 'block';
                zipBtn.onclick = () => window.location.href = data.zip_url;
            }
            
            resetUI();
        }
        
        function showError(message) {
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = '❌ エラー: ' + message;
            errorDiv.style.display = 'block';
        }
        
        function resetUI() {
            document.getElementById('uploadBtn').disabled = false;
            document.getElementById('progress').style.display = 'none';
            updateProgress(0, '');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """メインページ"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """画像解析API"""
    try:
        files = request.files.getlist('images')
        if not files:
            return jsonify({'error': '画像がアップロードされていません'}), 400
        
        # ジョブID生成
        job_id = str(uuid.uuid4())
        
        # 非同期処理を開始（ここでは簡易的に同期処理）
        processing_jobs[job_id] = {
            'status': 'processing',
            'progress': 0.1,
            'message': '処理を開始しました'
        }
        
        # 実際の処理はバックグラウンドで実行
        # ここでは簡易的なレスポンスを返す
        process_images_async(job_id, files)
        
        return jsonify({
            'job_id': job_id,
            'status': 'accepted'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<job_id>')
def check_status(job_id):
    """処理状況確認API"""
    if job_id not in processing_jobs:
        return jsonify({'error': 'ジョブが見つかりません'}), 404
    
    return jsonify(processing_jobs[job_id])

@app.route('/api/download/<job_id>/<file_type>')
def download_result(job_id, file_type):
    """結果ダウンロードAPI"""
    # 実際の実装では、処理結果のファイルパスを管理する
    if file_type == 'report':
        # HTMLレポートを返す
        return send_file('temp/report.html', as_attachment=True)
    elif file_type == 'zip':
        # ZIPファイルを返す
        return send_file('temp/package.zip', as_attachment=True)
    else:
        return jsonify({'error': '無効なファイルタイプ'}), 400

def process_images_async(job_id, files):
    """画像処理（実際は非同期で実行）"""
    try:
        # 進捗更新
        processing_jobs[job_id]['progress'] = 0.3
        processing_jobs[job_id]['message'] = '画像を処理中...'
        
        # ここで実際の処理を実行
        # ...
        
        # 完了
        processing_jobs[job_id] = {
            'status': 'completed',
            'progress': 1.0,
            'message': '処理完了',
            'processed_count': len(files),
            'report_url': f'/api/download/{job_id}/report',
            'zip_url': f'/api/download/{job_id}/zip'
        }
        
    except Exception as e:
        processing_jobs[job_id] = {
            'status': 'error',
            'error': str(e)
        }

if __name__ == '__main__':
    # 開発サーバー起動
    app.run(host='0.0.0.0', port=5000, debug=True)