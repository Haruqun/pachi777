#!/usr/bin/env python3
"""
超シンプルなWebサーバー版
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
from urllib.parse import parse_qs
import cgi

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>パチンコグラフ解析</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .upload-area { 
            border: 2px dashed #4CAF50; 
            padding: 40px; 
            text-align: center; 
            margin: 20px 0;
            background: #f9f9f9;
        }
        button { 
            background: #4CAF50; 
            color: white; 
            padding: 10px 20px; 
            border: none; 
            cursor: pointer;
            font-size: 16px;
        }
        button:hover { background: #45a049; }
        #result { margin-top: 20px; padding: 20px; background: #e8f5e9; display: none; }
    </style>
</head>
<body>
    <h1>🎰 パチンコグラフ解析システム</h1>
    
    <div class="upload-area">
        <p>画像をアップロード</p>
        <input type="file" id="fileInput" multiple accept="image/*">
    </div>
    
    <button onclick="processImages()">🚀 解析開始</button>
    
    <div id="result">
        <h3>✅ 処理完了！</h3>
        <p id="resultText"></p>
    </div>
    
    <script>
        function processImages() {
            const files = document.getElementById('fileInput').files;
            if (files.length === 0) {
                alert('画像を選択してください');
                return;
            }
            
            const formData = new FormData();
            for (let file of files) {
                formData.append('images', file);
            }
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('result').style.display = 'block';
                document.getElementById('resultText').textContent = 
                    data.message + ' (処理画像数: ' + data.count + '枚)';
            })
            .catch(error => {
                alert('エラー: ' + error);
            });
        }
    </script>
</body>
</html>
            """
            self.wfile.write(html.encode('utf-8'))
            
    def do_POST(self):
        if self.path == '/upload':
            content_type, pdict = cgi.parse_header(self.headers['Content-Type'])
            
            if content_type == 'multipart/form-data':
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD': 'POST'}
                )
                
                file_count = len(form.getlist('images'))
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response = {
                    'status': 'success',
                    'message': 'デモ処理が完了しました',
                    'count': file_count
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
            else:
                self.send_error(400, 'Bad Request')

def run_server(port=8000):
    server_address = ('localhost', port)
    httpd = HTTPServer(server_address, SimpleHandler)
    print(f"🌐 サーバー起動: http://localhost:{port}")
    print("Ctrl+C で終了")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()