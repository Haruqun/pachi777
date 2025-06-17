#!/usr/bin/env python3
"""
精度比較の視覚化
実際の値と抽出値の比較グラフを生成
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

def create_accuracy_visualization():
    """精度比較の視覚化"""
    # データ読み込み
    df = pd.read_csv('accuracy_report.csv')
    df = df[df['実際の最終値'].notna()]
    
    # Figure設定
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('パチンコグラフデータ抽出システム 精度分析', fontsize=16, y=0.98)
    
    # 1. 散布図: 実際の値 vs 抽出値
    ax1 = axes[0, 0]
    ax1.scatter(df['実際の最終値'], df['抽出最終値'], alpha=0.6, s=100)
    
    # 理想的な線（y=x）
    min_val = min(df['実際の最終値'].min(), df['抽出最終値'].min())
    max_val = max(df['実際の最終値'].max(), df['抽出最終値'].max())
    ax1.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.5, label='理想線(y=x)')
    
    # 相関係数を計算して表示
    correlation = df['実際の最終値'].corr(df['抽出最終値'])
    ax1.text(0.05, 0.95, f'相関係数: {correlation:.4f}', 
             transform=ax1.transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    ax1.set_xlabel('実際の最終差玉')
    ax1.set_ylabel('抽出された最終差玉')
    ax1.set_title('実際の値 vs 抽出値')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 2. 誤差分布のヒストグラム
    ax2 = axes[0, 1]
    errors = df['最終値絶対誤差']
    ax2.hist(errors, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
    ax2.axvline(errors.mean(), color='red', linestyle='--', 
                label=f'平均誤差: {errors.mean():.0f}玉')
    ax2.axvline(errors.median(), color='green', linestyle='--', 
                label=f'中央値: {errors.median():.0f}玉')
    
    ax2.set_xlabel('絶対誤差（玉）')
    ax2.set_ylabel('頻度')
    ax2.set_title('誤差分布')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 精度の分布
    ax3 = axes[1, 0]
    accuracy = df['最終値精度(%)']
    ax3.hist(accuracy, bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
    ax3.axvline(accuracy.mean(), color='red', linestyle='--', 
                label=f'平均精度: {accuracy.mean():.1f}%')
    ax3.axvline(95, color='orange', linestyle='--', label='95%ライン')
    
    ax3.set_xlabel('精度（%）')
    ax3.set_ylabel('頻度')
    ax3.set_title('精度分布')
    ax3.set_xlim(90, 100)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 機種別精度比較
    ax4 = axes[1, 1]
    machine_accuracy = df.groupby('機種')['最終値精度(%)'].agg(['mean', 'std', 'count'])
    machines = machine_accuracy.index
    x_pos = np.arange(len(machines))
    
    bars = ax4.bar(x_pos, machine_accuracy['mean'], yerr=machine_accuracy['std'], 
                    capsize=5, alpha=0.7, color=['lightblue', 'lightcoral'])
    
    # バーの上に数値を表示
    for i, (mean, count) in enumerate(zip(machine_accuracy['mean'], machine_accuracy['count'])):
        ax4.text(i, mean + 0.1, f'{mean:.1f}%\n(n={count})', 
                ha='center', va='bottom')
    
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(machines, rotation=15, ha='right')
    ax4.set_ylabel('平均精度（%）')
    ax4.set_title('機種別精度比較')
    ax4.set_ylim(95, 100)
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('accuracy_visualization.png', dpi=300, bbox_inches='tight')
    print("📊 精度比較グラフを保存: accuracy_visualization.png")
    
    # 個別の比較グラフ
    fig2, ax = plt.subplots(figsize=(12, 6))
    
    # 画像名でソート
    df_sorted = df.sort_values('画像名')
    x = np.arange(len(df_sorted))
    width = 0.35
    
    # 実際の値と抽出値のバー
    bars1 = ax.bar(x - width/2, df_sorted['実際の最終値'], width, 
                    label='実際の値', alpha=0.7, color='steelblue')
    bars2 = ax.bar(x + width/2, df_sorted['抽出最終値'], width, 
                    label='抽出値', alpha=0.7, color='coral')
    
    # ゼロライン
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    ax.set_xlabel('画像')
    ax.set_ylabel('差玉数')
    ax.set_title('各画像の実際の値と抽出値の比較')
    ax.set_xticks(x)
    ax.set_xticklabels([name.replace('S__78209', '') for name in df_sorted['画像名']], 
                       rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('value_comparison.png', dpi=300, bbox_inches='tight')
    print("📊 値比較グラフを保存: value_comparison.png")

if __name__ == "__main__":
    create_accuracy_visualization()