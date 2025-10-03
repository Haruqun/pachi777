"""Claude API関連の処理"""
import streamlit as st
import requests
import base64
import json
import re
from PIL import Image
import io


def analyze_with_claude(image, api_key, model="claude-3-5-haiku-20241022"):
    """Claude APIを使って出玉詳細画像を解析する（HTTP API版）"""
    import time
    
    if not api_key:
        return {
            'success': False,
            'error': "APIキーが設定されていません",
            'data': None,
            'raw_text': None
        }
    
    # NumPy配列をPIL Imageに変換
    import numpy as np
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)

    # 画像をbase64エンコード
    buffered = io.BytesIO()

    # 画像が大きすぎる場合はリサイズ
    max_size = 1024
    if image.width > max_size or image.height > max_size:
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    prompt = """この画像から以下の情報を正確に抽出してJSON形式で返してください：

1. machine_name: パチンコ機種名（例：「P戦国乙女」）
2. big_jackpots: 超（10R）の回数
3. medium_jackpots: 中（5R）の回数  
4. small_jackpots: 小（2-3R）の回数
5. total_jackpots: 大当り回数合計
6. total_balls: 総払い出し球数
7. spin_count: 累計スタート回数
8. normal_spins: 通常時の累計回転数
9. current_spins: 現在の回転数

数値が読み取れない場合はnullを設定してください。

重要：
- 総払い出し球数は「総」と「玉」の間にある数値です
- 超中小の個別回数も正確に読み取ってください
- 「現在」と表示されている回転数をcurrent_spinsに設定してください"""
    
    try:
        # HTTP APIを直接使用
        url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": model,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img_str
                            }
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            
            # レスポンスから内容を抽出
            content = response_data.get('content', [])
            if content and len(content) > 0:
                result_text = content[0].get('text', '')
            else:
                return {
                    'success': False,
                    'error': "レスポンスが空です",
                    'data': None,
                    'raw_text': None
                }
            
            # JSONを抽出してパース
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                try:
                    extracted_data = json.loads(json_match.group())
                    
                    # 現在値の修正（通常時使用玉数から逆算）
                    if extracted_data.get('normal_usage_balls') and extracted_data.get('total_balls'):
                        total_balls = extracted_data['total_balls']
                        normal_usage = extracted_data['normal_usage_balls']
                        
                        # 現在値 = 総払い出し - 通常時使用
                        current_value = total_balls - normal_usage
                        extracted_data['current_value_calculated'] = current_value
                    
                    return {
                        'success': True,
                        'error': None,
                        'data': extracted_data,
                        'raw_text': result_text
                    }
                except json.JSONDecodeError as e:
                    return {
                        'success': False,
                        'error': f"JSON解析エラー: {str(e)}",
                        'data': None,
                        'raw_text': result_text
                    }
            else:
                # JSONが見つからない場合でも、テキストは返す
                return {
                    'success': False,
                    'error': "JSONデータが見つかりませんでした",
                    'data': None,
                    'raw_text': result_text
                }
                
        elif response.status_code == 401:
            return {
                'success': False,
                'error': "APIキーが無効です。正しいキーを入力してください。",
                'data': None,
                'raw_text': None
            }
        else:
            error_detail = response.json() if response.text else {"error": "Unknown error"}
            return {
                'success': False,
                'error': f"APIエラー ({response.status_code}): {error_detail}",
                'data': None,
                'raw_text': None
            }
            
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': "APIリクエストがタイムアウトしました",
            'data': None,
            'raw_text': None
        }
    except Exception as e:
        from modules.error_handler import log_error
        log_error('Claude API Error', str(e), {'function': 'analyze_with_claude', 'image_type': 'detail_analysis'})
        return {
            'success': False,
            'error': str(e),
            'data': None,
            'raw_text': None
        }