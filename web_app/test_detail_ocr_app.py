import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import anthropic
import base64
import json
import os
import io
from datetime import datetime
import pandas as pd

st.set_page_config(
    page_title="パチンコOCR",
    page_icon="🎰",
    layout="wide"
)

st.title("🎰 パチンコ画像OCR")

# サイドバー
with st.sidebar:
    st.header("📸 画像アップロード")
    uploaded_file = st.file_uploader(
        "パチンコ画像を選択",
        type=['png', 'jpg', 'jpeg'],
        help="画像をアップロード"
    )
    
    st.divider()
    
    # OCR方式選択
    st.header("🔧 OCR方式")
    ocr_method = st.radio(
        "OCR方式を選択",
        ["Tesseract（無料）", "Claude 3 Haiku（高精度・有料）"],
        index=0
    )
    
    # Claude API設定
    if ocr_method == "Claude 3 Haiku（高精度・有料）":
        st.divider()
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            value=os.getenv("ANTHROPIC_API_KEY", ""),
            help="Claude APIキーを入力してください"
        )
        
        crop_upper_half = st.checkbox("上半分のみ処理（コスト50%削減）", value=True)
        output_format = st.radio("出力形式", ["JSON", "テキスト"], index=0)
    
    # 表示設定
    st.divider()
    st.header("⚙️ 表示設定")
    show_overlay = st.checkbox("検出領域を表示", value=True)

# メインエリア
if uploaded_file is not None:
    # 画像読み込み
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    # BGRに変換（OpenCV用）
    if len(img_array.shape) == 3:
        if img_array.shape[2] == 4:  # RGBA
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        elif img_array.shape[2] == 3:  # RGB
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img_array
    else:
        img_bgr = img_array
    
    # 2カラムレイアウト
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("🖼️ 画像")
        
        # Claude APIで上半分処理の場合
        if ocr_method == "Claude 3 Haiku（高精度・有料）" and crop_upper_half:
            width, height = image.size
            display_image = image.crop((0, 0, width, height // 2))
            st.image(display_image, use_column_width=True)
            st.info(f"上半分のみ表示: {width}×{height//2}px")
        # Tesseractでオーバーレイ表示
        elif ocr_method == "Tesseract（無料）" and show_overlay and 'ocr_data' in st.session_state:
            overlay_img = img_bgr.copy()
            data = st.session_state['ocr_data']
            
            # 各検出領域に枠を描画
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:  # 信頼度が0より大きい場合のみ
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    conf = int(data['conf'][i])
                    
                    # 信頼度に応じて色を変更
                    if conf > 80:
                        color = (0, 255, 0)  # 緑（高信頼度）
                    elif conf > 50:
                        color = (0, 165, 255)  # オレンジ（中信頼度）
                    else:
                        color = (0, 0, 255)  # 赤（低信頼度）
                    
                    # 矩形を描画
                    cv2.rectangle(overlay_img, (x, y), (x+w, y+h), color, 2)
                    
                    # 信頼度を表示
                    label = f"{conf}%"
                    cv2.putText(overlay_img, label, (x, y-5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # RGB変換して表示
            display_img = cv2.cvtColor(overlay_img, cv2.COLOR_BGR2RGB)
            st.image(display_img, use_column_width=True)
        else:
            st.image(image, use_column_width=True)
        
        st.info(f"画像サイズ: {img_array.shape[1]} x {img_array.shape[0]}px")
        
        # Claude APIのコスト表示
        if ocr_method == "Claude 3 Haiku（高精度・有料）":
            if crop_upper_half:
                width, height = image.size
                estimated_tokens = (width * height // 2) // 750
            else:
                width, height = image.size
                estimated_tokens = (width * height) // 750
            
            input_cost = estimated_tokens * 0.25 / 1000000
            output_cost = 150 * 1.25 / 1000000
            total_cost_usd = input_cost + output_cost
            total_cost_jpy = total_cost_usd * 150
            
            st.success(f"推定コスト: ${total_cost_usd:.4f} (約{total_cost_jpy:.2f}円)")
    
    with col_right:
        st.subheader("📊 OCR結果")
        
        if st.button("🔍 OCR実行", type="primary", use_container_width=True):
            with st.spinner("OCR処理中..."):
                
                # Tesseract OCR
                if ocr_method == "Tesseract（無料）":
                    try:
                        # テキスト抽出
                        text = pytesseract.image_to_string(image, lang='jpn')
                        
                        # 詳細データも取得（枠表示用）
                        data = pytesseract.image_to_data(
                            image, 
                            lang='jpn',
                            output_type=pytesseract.Output.DICT
                        )
                        
                        # セッションに保存
                        st.session_state['ocr_data'] = data
                        
                        # 結果表示
                        st.success("OCR完了！")
                        
                        # 検出統計
                        word_count = len([w for w in data['text'] if w.strip()])
                        avg_conf = np.mean([int(c) for c in data['conf'] if c > 0]) if word_count > 0 else 0
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("検出単語数", word_count)
                        with col2:
                            st.metric("平均信頼度", f"{avg_conf:.1f}%")
                        
                        # 抽出されたテキスト
                        st.markdown("### 📝 抽出されたテキスト")
                        st.text_area("", text, height=300)
                        
                        # デバッグ情報
                        with st.expander("🔧 OCRデバッグ情報", expanded=False):
                            # 検出された全単語の詳細
                            debug_data = []
                            for i in range(len(data['text'])):
                                if data['text'][i].strip():  # 空でないテキストのみ
                                    debug_data.append({
                                        'テキスト': data['text'][i],
                                        '信頼度': f"{data['conf'][i]}%",
                                        '位置(x,y)': f"({data['left'][i]}, {data['top'][i]})",
                                        'サイズ(w×h)': f"{data['width'][i]}×{data['height'][i]}"
                                    })
                            
                            if debug_data:
                                df = pd.DataFrame(debug_data)
                                st.dataframe(df, use_container_width=True)
                        
                        # 再実行でオーバーレイを更新
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"OCRエラー: {str(e)}")
                
                # Claude API OCR
                else:  # Claude 3 Haiku
                    if not api_key:
                        st.error("APIキーを入力してください")
                    else:
                        try:
                            # 画像の準備
                            if crop_upper_half:
                                width, height = image.size
                                image_to_process = image.crop((0, 0, width, height // 2))
                            else:
                                image_to_process = image
                            
                            # 画像をbase64エンコード
                            buffered = io.BytesIO()
                            image_to_process.save(buffered, format="PNG")
                            img_base64 = base64.b64encode(buffered.getvalue()).decode()
                            
                            # Claude APIクライアント初期化
                            client = anthropic.Anthropic(api_key=api_key)
                            
                            # プロンプト作成
                            if output_format == "JSON":
                                prompt = """
この画像からパチンコ台のデータを抽出してJSON形式で返してください。
以下の項目を抽出してください（存在しない項目はnullとしてください）：

{
  "店舗番号": "string",
  "機種名": "string", 
  "番台": "string",
  "日付": "string",
  "大当り回数": number,
  "大当り確率": "string",
  "初当り回数": number,
  "初当り確率": "string",
  "累計スタート": number,
  "通常": number,
  "チャンス中": number,
  "超": number,
  "中": number,
  "小": number,
  "スタート": number,
  "最高出玉": number,
  "最高一撃獲得": number,
  "初回特賞スタート": number,
  "前日最終スタート": number
}

JSONのみを返してください。説明は不要です。
"""
                            else:
                                prompt = "この画像に含まれるすべてのテキストと数値を読み取って、整理して出力してください。"
                            
                            # API呼び出し
                            message = client.messages.create(
                                model="claude-3-haiku-20240307",
                                max_tokens=1000,
                                messages=[
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
                                                    "data": img_base64
                                                }
                                            }
                                        ]
                                    }
                                ]
                            )
                            
                            # 結果取得
                            result = message.content[0].text
                            
                            # 結果表示
                            st.success("✅ 解析完了！")
                            
                            # 結果表示
                            if output_format == "JSON":
                                try:
                                    # JSON形式でパース
                                    json_data = json.loads(result)
                                    
                                    # JSON表示
                                    st.json(json_data)
                                    
                                    # JSONダウンロード
                                    json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
                                    st.download_button(
                                        label="📥 JSONをダウンロード",
                                        data=json_str,
                                        file_name=f"ocr_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                        mime="application/json"
                                    )
                                    
                                except json.JSONDecodeError:
                                    st.warning("JSON形式の解析に失敗しました。生データを表示します。")
                                    st.text_area("生データ", result, height=400)
                            else:
                                # テキスト形式で表示
                                st.text_area("抽出されたテキスト", result, height=400)
                            
                        except Exception as e:
                            st.error(f"エラーが発生しました: {str(e)}")

else:
    # 使い方説明
    st.info("👈 サイドバーから画像をアップロードしてください")
    
    st.markdown("""
    ### OCR方式の比較
    
    #### Tesseract（無料）
    - 料金: 無料
    - 精度: 60-70%
    - 処理速度: 遅い
    - 日本語: 対応（精度低め）
    
    #### Claude 3 Haiku（高精度・有料）
    - 料金: 約0.06円/枚（上半分なら0.03円）
    - 精度: 85-90%
    - 処理速度: 速い
    - 日本語: 高精度
    
    ### 使い方
    1. サイドバーから画像をアップロード
    2. OCR方式を選択
    3. 「OCR実行」ボタンをクリック
    """)