import streamlit as st
import anthropic
import base64
import json
import os
from PIL import Image
import io
from datetime import datetime
import pandas as pd

st.set_page_config(
    page_title="Claude OCR",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Claude 3 Haiku 画像読み取り")

# APIキー設定
with st.sidebar:
    st.header("⚙️ 設定")
    
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        help="Claude APIキーを入力してください"
    )
    
    st.divider()
    
    st.header("📸 画像アップロード")
    uploaded_file = st.file_uploader(
        "パチンコ画像を選択",
        type=['png', 'jpg', 'jpeg'],
        help="画像をアップロード"
    )
    
    st.divider()
    
    # 処理オプション
    st.header("🎯 処理オプション")
    crop_upper_half = st.checkbox("上半分のみ処理（コスト50%削減）", value=True)
    output_format = st.radio("出力形式", ["JSON", "テキスト"], index=0)

# メインエリア
if uploaded_file is not None:
    # 画像読み込み
    image = Image.open(uploaded_file)
    
    # 上半分のみ処理する場合
    if crop_upper_half:
        width, height = image.size
        image_to_process = image.crop((0, 0, width, height // 2))
        st.info(f"💡 上半分のみ処理: {width}×{height//2}px（元: {width}×{height}px）")
    else:
        image_to_process = image
    
    # 2カラムレイアウト
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("📷 処理対象画像")
        st.image(image_to_process, use_column_width=True)
        
        # 画像サイズとトークン推定
        width, height = image_to_process.size
        estimated_tokens = (width * height) // 750
        st.info(f"画像サイズ: {width}×{height}px")
        st.info(f"推定トークン数: 約{estimated_tokens:,}")
        
        # コスト計算
        input_cost = estimated_tokens * 0.25 / 1000000  # $0.25/1M tokens
        output_cost = 150 * 1.25 / 1000000  # 約150トークン × $1.25/1M
        total_cost_usd = input_cost + output_cost
        total_cost_jpy = total_cost_usd * 150  # 1ドル=150円で計算
        
        st.success(f"推定コスト: ${total_cost_usd:.4f} (約{total_cost_jpy:.2f}円)")
    
    with col_right:
        st.subheader("📊 解析結果")
        
        if st.button("🚀 Claude Haikuで解析", type="primary", use_container_width=True):
            if not api_key:
                st.error("APIキーを入力してください")
            else:
                with st.spinner("Claude 3 Haikuで解析中..."):
                    try:
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
  "時刻": "string",
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
  "チャンス中大当り": number,
  "チャンス中確率": "string",
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
                        
                        # 使用トークン数とコスト
                        if hasattr(message, 'usage'):
                            input_tokens = message.usage.input_tokens
                            output_tokens = message.usage.output_tokens
                            actual_input_cost = input_tokens * 0.25 / 1000000
                            actual_output_cost = output_tokens * 1.25 / 1000000
                            actual_total_cost_usd = actual_input_cost + actual_output_cost
                            actual_total_cost_jpy = actual_total_cost_usd * 150
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("入力トークン", f"{input_tokens:,}")
                            with col2:
                                st.metric("出力トークン", f"{output_tokens:,}")
                            with col3:
                                st.metric("実際のコスト", f"${actual_total_cost_usd:.4f} (約{actual_total_cost_jpy:.2f}円)")
                        
                        # 結果表示
                        if output_format == "JSON":
                            try:
                                # JSON形式でパース
                                json_data = json.loads(result)
                                
                                # JSON表示
                                st.json(json_data)
                                
                                # データフレーム表示
                                with st.expander("📋 テーブル表示"):
                                    df = pd.DataFrame([json_data])
                                    st.dataframe(df.T, use_container_width=True)
                                
                                # JSONダウンロード
                                json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
                                st.download_button(
                                    label="📥 JSONをダウンロード",
                                    data=json_str,
                                    file_name=f"ocr_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                    mime="application/json"
                                )
                                
                                # CSVダウンロード
                                csv = df.to_csv(index=False, encoding='utf-8-sig')
                                st.download_button(
                                    label="📥 CSVをダウンロード",
                                    data=csv,
                                    file_name=f"ocr_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv"
                                )
                                
                            except json.JSONDecodeError:
                                st.warning("JSON形式の解析に失敗しました。生データを表示します。")
                                st.text_area("生データ", result, height=400)
                        else:
                            # テキスト形式で表示
                            st.text_area("抽出されたテキスト", result, height=400)
                            
                            # テキストダウンロード
                            st.download_button(
                                label="📥 テキストをダウンロード",
                                data=result,
                                file_name=f"ocr_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                mime="text/plain"
                            )
                        
                    except Exception as e:
                        st.error(f"エラーが発生しました: {str(e)}")
                        st.info("APIキーが正しいか、インターネット接続を確認してください。")

else:
    # 使い方説明
    st.info("👈 サイドバーから画像をアップロードしてください")
    
    st.markdown("""
    ### 使い方
    
    1. **APIキーを設定**  
       Anthropic社のAPIキーを入力してください。
       [APIキーの取得はこちら](https://console.anthropic.com/)
    
    2. **画像をアップロード**  
       解析したいパチンコ台の画像を選択してください。
    
    3. **処理オプションを選択**  
       - 上半分のみ処理: コストを50%削減できます
       - 出力形式: JSONまたはテキスト形式を選択
    
    4. **解析実行**  
       「Claude Haikuで解析」ボタンをクリック
    
    ### 料金の目安
    
    - **1枚あたり**: 約0.06円
    - **1,000枚**: 約63円
    - **上半分のみ**: 約0.03円/枚
    
    ※料金は2024年10月時点の参考価格です。
    """)
    
    # コスト計算機
    with st.expander("💰 コスト計算機"):
        num_images = st.number_input("処理枚数", min_value=1, max_value=10000, value=100)
        use_half = st.checkbox("上半分のみ処理", value=True, key="calc_half")
        
        cost_per_image = 0.03 if use_half else 0.06
        total_cost = num_images * cost_per_image
        
        st.success(f"""
        **計算結果**
        - 1枚あたり: {cost_per_image:.3f}円
        - 合計: {total_cost:.2f}円
        """)