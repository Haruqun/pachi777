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

    # ===== ログ方法テスト =====
    print("TEST 1: print() - これはテストです")
    import logging
    logging.info("TEST 2: logging.info() - これはテストです")
    logging.warning("TEST 3: logging.warning() - これはテストです")
    st.write("TEST 4: st.write() - これはテストです")
    st.info("TEST 5: st.info() - これはテストです")
    st.success("TEST 6: st.success() - これはテストです")
    st.warning("TEST 7: st.warning() - これはテストです")
    st.error("TEST 8: st.error() - これはテストです")
    import sys
    sys.stdout.write("TEST 9: sys.stdout.write() - これはテストです\n")
    sys.stderr.write("TEST 10: sys.stderr.write() - これはテストです\n")
    import os
    os.write(1, b"TEST 11: os.write(1) - これはテストです\n")
    os.write(2, b"TEST 12: os.write(2) - これはテストです\n")
    # ===== テスト終了 =====

    # NumPy配列をPIL Imageに変換
    import numpy as np
    if isinstance(image, np.ndarray):
        st.write(f"🔄 NumPy配列をPIL Imageに変換中... (shape: {image.shape})")
        image = Image.fromarray(image)

    st.write(f"📐 画像サイズ: {image.width} x {image.height}px")

    # 画像をbase64エンコード
    buffered = io.BytesIO()

    # 画像が大きすぎる場合はリサイズ
    max_size = 1024
    if image.width > max_size or image.height > max_size:
        st.write(f"⚠️ 画像が大きいためリサイズします: {image.width}x{image.height} → {max_size}x{max_size}")
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        st.write(f"✅ リサイズ完了: {image.width} x {image.height}px")

    st.write("🔐 画像をBase64エンコード中...")
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    img_size_kb = len(buffered.getvalue()) / 1024
    st.write(f"✅ エンコード完了: {img_size_kb:.1f}KB")

    prompt = """この画像から以下の情報を正確に抽出してJSON形式で返してください：

1. machine_number: 台番号（数字のみ）
2. machine_name: パチンコ機種名（完全な名前）
3. date: 日付（表示形式のまま）
4. total_jackpots: 大当り回数合計
5. first_jackpots: 初当り回数
6. big_jackpots: 超（10R）の回数
7. medium_jackpots: 中（5R）の回数  
8. small_jackpots: 小（2-3R）の回数
9. total_rotations: 累計スタート（総回転数）
10. normal_rotations: 通常（通常回転数）
11. max_balls: 最高出玉
12. initial_ball_starts: 初回特賞スタート

数値が読み取れない場合はnullを設定してください。

重要：
- 画像に表示されている値のみを返してください
- 推測や計算は行わないでください
- 超中小の個別回数も正確に読み取ってください"""
    
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

        st.write(f"🌐 Claude API ({model}) にリクエスト送信中...")
        request_start = time.time()
        response = requests.post(url, headers=headers, json=data, timeout=30)
        request_time = time.time() - request_start
        st.write(f"✅ APIレスポンス受信完了: {request_time:.1f}秒 (ステータス: {response.status_code})")
        
        if response.status_code == 200:
            st.write("📦 APIレスポンスをJSON解析中...")
            response_data = response.json()

            # レスポンスから内容を抽出
            content = response_data.get('content', [])
            if content and len(content) > 0:
                result_text = content[0].get('text', '')
                st.write(f"📝 Claude応答テキスト長: {len(result_text)}文字")
            else:
                st.error("❌ レスポンスが空です")
                return {
                    'success': False,
                    'error': "レスポンスが空です",
                    'data': None,
                    'raw_text': None
                }

            # JSONを抽出してパース
            st.write("🔍 JSON形式のデータを抽出中...")
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                try:
                    st.write("✅ JSONデータ発見、パース中...")
                    extracted_data = json.loads(json_match.group())
                    st.write(f"✅ JSONパース成功: {len(extracted_data)}個のフィールド")
                    
                    # 現在値の修正（通常時使用玉数から逆算）
                    if extracted_data.get('normal_usage_balls') and extracted_data.get('total_balls'):
                        total_balls = extracted_data['total_balls']
                        normal_usage = extracted_data['normal_usage_balls']
                        
                        # 現在値 = 総払い出し - 通常時使用
                        current_value = total_balls - normal_usage
                        extracted_data['current_value_calculated'] = current_value
                    
                    st.success("✅ Claude API解析完了！")
                    return {
                        'success': True,
                        'error': None,
                        'data': extracted_data,
                        'raw_text': result_text
                    }
                except json.JSONDecodeError as e:
                    st.error(f"❌ JSON解析エラー: {str(e)}")
                    return {
                        'success': False,
                        'error': f"JSON解析エラー: {str(e)}",
                        'data': None,
                        'raw_text': result_text
                    }
            else:
                # JSONが見つからない場合でも、テキストは返す
                st.warning("⚠️ JSONデータが見つかりませんでした")
                return {
                    'success': False,
                    'error': "JSONデータが見つかりませんでした",
                    'data': None,
                    'raw_text': result_text
                }
                
        elif response.status_code == 401:
            st.error("❌ APIキー認証エラー (401)")
            return {
                'success': False,
                'error': "APIキーが無効です。正しいキーを入力してください。",
                'data': None,
                'raw_text': None
            }
        elif response.status_code == 429:
            st.error("❌ APIレート制限エラー (429)")
            return {
                'success': False,
                'error': "APIレート制限に達しました。しばらく待ってから再試行してください。",
                'data': None,
                'raw_text': None
            }
        else:
            error_detail = response.json() if response.text else {"error": "Unknown error"}
            st.error(f"❌ APIエラー ({response.status_code}): {error_detail}")
            return {
                'success': False,
                'error': f"APIエラー ({response.status_code}): {error_detail}",
                'data': None,
                'raw_text': None
            }

    except requests.exceptions.Timeout:
        st.error("❌ APIリクエストがタイムアウトしました (30秒)")
        return {
            'success': False,
            'error': "APIリクエストがタイムアウトしました",
            'data': None,
            'raw_text': None
        }
    except Exception as e:
        from modules.error_handler import log_error
        log_error('Claude API Error', str(e), {'function': 'analyze_with_claude', 'image_type': 'detail_analysis'})
        st.error(f"❌ 予期しないエラー: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'data': None,
            'raw_text': None
        }