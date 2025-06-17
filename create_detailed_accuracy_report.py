#!/usr/bin/env python3
"""
最終差玉と最大値の精度に焦点を当てた詳細レポート作成
"""

import pandas as pd
import numpy as np

def create_detailed_accuracy_report():
    """最終差玉と最大値の精度に特化したレポートを作成"""
    
    # 元のレポートを読み込み
    df = pd.read_csv('accuracy_report.csv')
    
    # 最終差玉の精度に関する詳細レポート
    final_value_report = pd.DataFrame({
        '画像番号': df['画像名'].str.extract(r'(\d+)')[0],
        '台番号': df['台番号'],
        '機種': df['機種'].str.replace('P大海物語5 MTE2', 'P大海').str.replace('e Re：ゼロから始める異世', 'eRe:ゼロ'),
        '実際の最終差玉': df['実際の最終値'].round(0).astype('Int64'),
        '抽出した最終差玉': df['抽出最終値'].round(0).astype('Int64'),
        '最終差玉の誤差': df['最終値誤差'].round(0).astype('Int64'),
        '最終差玉の精度(%)': df['最終値精度(%)'].round(1),
    })
    
    # 最大値の精度に関する詳細レポート
    max_value_report = pd.DataFrame({
        '画像番号': df['画像名'].str.extract(r'(\d+)')[0],
        '実際の最大値': df['実際の最大値'].round(0).astype('Int64'),
        '抽出した最大値': df['抽出最大値'].round(0).astype('Int64'),
        '最大値の誤差': df['最大値誤差'].round(0).astype('Int64'),
        '最大値の精度(%)': df['最大値精度(%)'].round(1),
    })
    
    # 総合レポート（両方の精度を含む）
    comprehensive_report = pd.DataFrame({
        '画像番号': df['画像名'].str.extract(r'(\d+)')[0],
        '台番号': df['台番号'],
        '機種': df['機種'].str.replace('P大海物語5 MTE2', 'P大海').str.replace('e Re：ゼロから始める異世', 'eRe:ゼロ'),
        # 最終差玉関連
        '実際の最終差玉': df['実際の最終値'].round(0).astype('Int64'),
        '抽出した最終差玉': df['抽出最終値'].round(0).astype('Int64'),
        '最終差玉誤差': df['最終値誤差'].round(0).astype('Int64'),
        '最終差玉精度(%)': df['最終値精度(%)'].round(1),
        # 最大値関連
        '実際の最大値': df['実際の最大値'].round(0).astype('Int64'),
        '抽出した最大値': df['抽出最大値'].round(0).astype('Int64'),
        '最大値誤差': df['最大値誤差'].round(0).astype('Int64'),
        '最大値精度(%)': df['最大値精度(%)'].round(1),
    })
    
    # 画像番号でソート
    final_value_report = final_value_report.sort_values('画像番号').reset_index(drop=True)
    max_value_report = max_value_report.sort_values('画像番号').reset_index(drop=True)
    comprehensive_report = comprehensive_report.sort_values('画像番号').reset_index(drop=True)
    
    # ファイル保存
    final_value_report.to_csv('final_value_accuracy_report.csv', index=False, encoding='utf-8')
    max_value_report.to_csv('max_value_accuracy_report.csv', index=False, encoding='utf-8')
    comprehensive_report.to_csv('comprehensive_accuracy_report.csv', index=False, encoding='utf-8')
    
    print("📄 レポートを保存しました:")
    print("  - final_value_accuracy_report.csv (最終差玉の精度)")
    print("  - max_value_accuracy_report.csv (最大値の精度)")
    print("  - comprehensive_accuracy_report.csv (総合レポート)")
    
    # 統計サマリーを計算
    valid_final = df[df['最終値精度(%)'].notna()]
    valid_max = df[df['最大値精度(%)'].notna()]
    
    # 最終差玉の精度統計
    final_stats = pd.DataFrame({
        '項目': [
            '有効データ数',
            '平均精度',
            '最高精度',
            '最低精度',
            '標準偏差',
            '平均誤差（絶対値）',
            '最大誤差（絶対値）',
            '誤差100玉以内',
            '誤差200玉以内',
            '誤差300玉以内',
            '精度99%以上',
            '精度98%以上',
            '精度95%以上'
        ],
        '最終差玉': [
            f"{len(valid_final)}件",
            f"{valid_final['最終値精度(%)'].mean():.2f}%",
            f"{valid_final['最終値精度(%)'].max():.1f}%",
            f"{valid_final['最終値精度(%)'].min():.1f}%",
            f"{valid_final['最終値精度(%)'].std():.2f}%",
            f"{valid_final['最終値絶対誤差'].mean():.0f}玉",
            f"{valid_final['最終値絶対誤差'].max():.0f}玉",
            f"{len(valid_final[valid_final['最終値絶対誤差'] <= 100])}件 ({len(valid_final[valid_final['最終値絶対誤差'] <= 100])/len(valid_final)*100:.0f}%)",
            f"{len(valid_final[valid_final['最終値絶対誤差'] <= 200])}件 ({len(valid_final[valid_final['最終値絶対誤差'] <= 200])/len(valid_final)*100:.0f}%)",
            f"{len(valid_final[valid_final['最終値絶対誤差'] <= 300])}件 ({len(valid_final[valid_final['最終値絶対誤差'] <= 300])/len(valid_final)*100:.0f}%)",
            f"{len(valid_final[valid_final['最終値精度(%)'] >= 99])}件 ({len(valid_final[valid_final['最終値精度(%)'] >= 99])/len(valid_final)*100:.0f}%)",
            f"{len(valid_final[valid_final['最終値精度(%)'] >= 98])}件 ({len(valid_final[valid_final['最終値精度(%)'] >= 98])/len(valid_final)*100:.0f}%)",
            f"{len(valid_final[valid_final['最終値精度(%)'] >= 95])}件 ({len(valid_final[valid_final['最終値精度(%)'] >= 95])/len(valid_final)*100:.0f}%)"
        ]
    })
    
    # 最大値の精度統計
    max_stats_values = [
        f"{len(valid_max)}件",
        f"{valid_max['最大値精度(%)'].mean():.2f}%",
        f"{valid_max['最大値精度(%)'].max():.1f}%",
        f"{valid_max['最大値精度(%)'].min():.1f}%",
        f"{valid_max['最大値精度(%)'].std():.2f}%",
        f"{valid_max['最大値絶対誤差'].mean():.0f}玉",
        f"{valid_max['最大値絶対誤差'].max():.0f}玉",
        f"{len(valid_max[valid_max['最大値絶対誤差'] <= 100])}件 ({len(valid_max[valid_max['最大値絶対誤差'] <= 100])/len(valid_max)*100:.0f}%)",
        f"{len(valid_max[valid_max['最大値絶対誤差'] <= 200])}件 ({len(valid_max[valid_max['最大値絶対誤差'] <= 200])/len(valid_max)*100:.0f}%)",
        f"{len(valid_max[valid_max['最大値絶対誤差'] <= 300])}件 ({len(valid_max[valid_max['最大値絶対誤差'] <= 300])/len(valid_max)*100:.0f}%)",
        f"{len(valid_max[valid_max['最大値精度(%)'] >= 99])}件 ({len(valid_max[valid_max['最大値精度(%)'] >= 99])/len(valid_max)*100:.0f}%)",
        f"{len(valid_max[valid_max['最大値精度(%)'] >= 98])}件 ({len(valid_max[valid_max['最大値精度(%)'] >= 98])/len(valid_max)*100:.0f}%)",
        f"{len(valid_max[valid_max['最大値精度(%)'] >= 95])}件 ({len(valid_max[valid_max['最大値精度(%)'] >= 95])/len(valid_max)*100:.0f}%)"
    ]
    
    final_stats['最大値'] = max_stats_values
    
    # 統計サマリーを保存
    final_stats.to_csv('accuracy_statistics_summary.csv', index=False, encoding='utf-8')
    
    # コンソール出力
    print("\n" + "="*80)
    print("📊 最終差玉と最大値の精度統計サマリー")
    print("="*80)
    print(final_stats.to_string(index=False))
    
    # 最高精度と最低精度のケースを表示
    print("\n" + "="*80)
    print("📈 最終差玉の精度 - 特筆すべきケース")
    print("="*80)
    
    best_final = valid_final.loc[valid_final['最終値精度(%)'].idxmax()]
    print(f"\n✅ 最高精度: 画像{best_final['画像名'].replace('S__78209', '').replace('_optimal', '')}")
    print(f"   実際: {best_final['実際の最終値']:.0f}玉, 抽出: {best_final['抽出最終値']:.0f}玉")
    print(f"   誤差: {best_final['最終値誤差']:.0f}玉, 精度: {best_final['最終値精度(%)']:.1f}%")
    
    worst_final = valid_final.loc[valid_final['最終値精度(%)'].idxmin()]
    print(f"\n❌ 最低精度: 画像{worst_final['画像名'].replace('S__78209', '').replace('_optimal', '')}")
    print(f"   実際: {worst_final['実際の最終値']:.0f}玉, 抽出: {worst_final['抽出最終値']:.0f}玉")
    print(f"   誤差: {worst_final['最終値誤差']:.0f}玉, 精度: {worst_final['最終値精度(%)']:.1f}%")
    
    print("\n" + "="*80)
    print("📈 最大値の精度 - 特筆すべきケース")
    print("="*80)
    
    best_max = valid_max.loc[valid_max['最大値精度(%)'].idxmax()]
    print(f"\n✅ 最高精度: 画像{best_max['画像名'].replace('S__78209', '').replace('_optimal', '')}")
    print(f"   実際: {best_max['実際の最大値']:.0f}玉, 抽出: {best_max['抽出最大値']:.0f}玉")
    print(f"   誤差: {best_max['最大値誤差']:.0f}玉, 精度: {best_max['最大値精度(%)']:.1f}%")
    
    worst_max = valid_max.loc[valid_max['最大値精度(%)'].idxmin()]
    print(f"\n❌ 最低精度: 画像{worst_max['画像名'].replace('S__78209', '').replace('_optimal', '')}")
    print(f"   実際: {worst_max['実際の最大値']:.0f}玉, 抽出: {worst_max['抽出最大値']:.0f}玉")
    print(f"   誤差: {worst_max['最大値誤差']:.0f}玉, 精度: {worst_max['最大値精度(%)']:.1f}%")

if __name__ == "__main__":
    create_detailed_accuracy_report()