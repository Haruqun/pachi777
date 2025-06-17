#!/usr/bin/env python3
"""
抽出データの精度検証ツール
results.txtの実際の値と比較して精度を評価
"""

import os
import csv
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

class AccuracyChecker:
    """精度検証クラス"""
    
    def __init__(self, results_file="results.txt", extracted_data_dir="graphs/improved_extracted_data"):
        self.results_file = results_file
        self.extracted_data_dir = extracted_data_dir
        self.results_data = self.load_results()
        
    def load_results(self) -> Dict[str, Dict]:
        """results.txtを読み込み"""
        data = {}
        with open(self.results_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # ファイル名をキーにして保存
                base_name = row['画像名'].replace('.jpg', '')
                data[base_name] = {
                    '台番号': row['台番号'],
                    '機種': row['機種'],
                    '実際の最大値': self.parse_number(row['実際の最大値']),
                    '実際の最終差玉': self.parse_number(row['実際の最終差玉']),
                    '目視予想最終差玉': self.parse_number(row['目視予想最終差玉']),
                    '誤差': self.parse_number(row['誤差'])
                }
        return data
    
    def parse_number(self, value: str) -> float:
        """カンマ区切りの数値をパース"""
        if not value or value == '':
            return None
        # カンマと引用符を除去
        cleaned = value.strip('"').replace(',', '')
        # マイナス記号の処理
        if cleaned.startswith('-'):
            return -float(cleaned[1:])
        return float(cleaned)
    
    def load_extracted_data(self, image_name: str) -> Tuple[float, float]:
        """抽出されたCSVデータから最大値と最終値を取得"""
        csv_path = os.path.join(self.extracted_data_dir, f"{image_name}_optimal_data.csv")
        
        if not os.path.exists(csv_path):
            return None, None
        
        df = pd.read_csv(csv_path)
        if df.empty:
            return None, None
        
        max_value = df['value'].max()
        final_value = df['value'].iloc[-1]
        
        return max_value, final_value
    
    def calculate_accuracy(self, actual: float, predicted: float) -> Dict:
        """精度指標を計算"""
        if actual is None or predicted is None:
            return {
                'error': None,
                'absolute_error': None,
                'percentage_error': None,
                'accuracy': None
            }
        
        error = predicted - actual
        absolute_error = abs(error)
        
        # パーセンテージエラー（実際の値が0の場合の処理）
        if actual != 0:
            percentage_error = (absolute_error / abs(actual)) * 100
        else:
            percentage_error = 100 if predicted != 0 else 0
        
        # 精度スコア（0-100%）
        # 30000玉を基準にして精度を計算
        accuracy = max(0, 100 - (absolute_error / 30000 * 100))
        
        return {
            'error': error,
            'absolute_error': absolute_error,
            'percentage_error': percentage_error,
            'accuracy': accuracy
        }
    
    def analyze_all(self) -> pd.DataFrame:
        """全画像の精度を分析"""
        results = []
        
        for image_name, actual_data in self.results_data.items():
            # 抽出データを読み込み
            extracted_max, extracted_final = self.load_extracted_data(image_name)
            
            # 最終値の精度を計算
            final_accuracy = self.calculate_accuracy(
                actual_data['実際の最終差玉'],
                extracted_final
            )
            
            # 最大値の精度を計算
            max_accuracy = self.calculate_accuracy(
                actual_data['実際の最大値'],
                extracted_max
            )
            
            results.append({
                '画像名': image_name,
                '台番号': actual_data['台番号'],
                '機種': actual_data['機種'],
                # 実際の値
                '実際の最大値': actual_data['実際の最大値'],
                '実際の最終値': actual_data['実際の最終差玉'],
                # 抽出値
                '抽出最大値': extracted_max,
                '抽出最終値': extracted_final,
                # 最終値の精度
                '最終値誤差': final_accuracy['error'],
                '最終値絶対誤差': final_accuracy['absolute_error'],
                '最終値誤差率(%)': final_accuracy['percentage_error'],
                '最終値精度(%)': final_accuracy['accuracy'],
                # 最大値の精度
                '最大値誤差': max_accuracy['error'],
                '最大値絶対誤差': max_accuracy['absolute_error'],
                '最大値誤差率(%)': max_accuracy['percentage_error'],
                '最大値精度(%)': max_accuracy['accuracy'],
                # 目視予想との比較
                '目視予想': actual_data['目視予想最終差玉'],
                '目視誤差': actual_data['誤差']
            })
        
        return pd.DataFrame(results)
    
    def print_summary(self, df: pd.DataFrame):
        """サマリーを表示"""
        print("\n" + "="*80)
        print("🎯 精度検証結果サマリー")
        print("="*80)
        
        # 有効なデータのみでフィルタリング
        valid_final = df[df['最終値精度(%)'].notna()]
        valid_max = df[df['最大値精度(%)'].notna()]
        
        if not valid_final.empty:
            print("\n📊 最終値の精度:")
            print(f"  平均精度: {valid_final['最終値精度(%)'].mean():.1f}%")
            print(f"  最高精度: {valid_final['最終値精度(%)'].max():.1f}%")
            print(f"  最低精度: {valid_final['最終値精度(%)'].min():.1f}%")
            print(f"  平均絶対誤差: {valid_final['最終値絶対誤差'].mean():.0f}玉")
            
            # 高精度（80%以上）のケース
            high_accuracy = valid_final[valid_final['最終値精度(%)'] >= 80]
            print(f"  高精度(80%以上): {len(high_accuracy)}/{len(valid_final)}件")
        
        if not valid_max.empty:
            print("\n📊 最大値の精度:")
            print(f"  平均精度: {valid_max['最大値精度(%)'].mean():.1f}%")
            print(f"  最高精度: {valid_max['最大値精度(%)'].max():.1f}%")
            print(f"  最低精度: {valid_max['最大値精度(%)'].min():.1f}%")
            print(f"  平均絶対誤差: {valid_max['最大値絶対誤差'].mean():.0f}玉")
        
        print("\n📈 機種別の精度:")
        for machine_type in df['機種'].unique():
            machine_data = valid_final[valid_final['機種'] == machine_type]
            if not machine_data.empty:
                print(f"  {machine_type}: 平均精度 {machine_data['最終値精度(%)'].mean():.1f}%")
        
        # 最も精度が高かった画像
        if not valid_final.empty:
            best = valid_final.loc[valid_final['最終値精度(%)'].idxmax()]
            print(f"\n✅ 最高精度: {best['画像名']} (精度: {best['最終値精度(%)']:.1f}%)")
            print(f"   実際: {best['実際の最終値']:.0f}, 抽出: {best['抽出最終値']:.0f}, 誤差: {best['最終値絶対誤差']:.0f}")
        
        # 最も精度が低かった画像
        if not valid_final.empty:
            worst = valid_final.loc[valid_final['最終値精度(%)'].idxmin()]
            print(f"\n❌ 最低精度: {worst['画像名']} (精度: {worst['最終値精度(%)']:.1f}%)")
            print(f"   実際: {worst['実際の最終値']:.0f}, 抽出: {worst['抽出最終値']:.0f}, 誤差: {worst['最終値絶対誤差']:.0f}")
    
    def save_report(self, df: pd.DataFrame, output_file: str = "accuracy_report.csv"):
        """詳細レポートを保存"""
        # 数値を見やすくフォーマット
        for col in df.columns:
            if '精度(%)' in col or '誤差率(%)' in col:
                df[col] = df[col].round(1)
            elif '値' in col or '誤差' in col:
                if col not in ['画像名', '台番号', '機種']:
                    df[col] = df[col].round(0)
        
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\n📄 詳細レポートを保存: {output_file}")

def main():
    """メイン処理"""
    print("🔍 抽出データ精度検証ツール")
    print("📊 results.txtと抽出データを比較します")
    
    # 精度チェッカーを初期化
    checker = AccuracyChecker()
    
    # 全データを分析
    results_df = checker.analyze_all()
    
    # サマリーを表示
    checker.print_summary(results_df)
    
    # 詳細レポートを保存
    checker.save_report(results_df)
    
    # 個別の結果を表示（上位5件）
    print("\n" + "="*80)
    print("📋 個別結果（精度上位5件）:")
    print("="*80)
    
    valid_df = results_df[results_df['最終値精度(%)'].notna()].sort_values('最終値精度(%)', ascending=False)
    
    for idx, row in valid_df.head(5).iterrows():
        print(f"\n{row['画像名']}:")
        print(f"  台番号: {row['台番号']}, 機種: {row['機種']}")
        print(f"  実際の最終値: {row['実際の最終値']:.0f}")
        print(f"  抽出最終値: {row['抽出最終値']:.0f}")
        print(f"  誤差: {row['最終値誤差']:.0f} (精度: {row['最終値精度(%)']:.1f}%)")

if __name__ == "__main__":
    main()