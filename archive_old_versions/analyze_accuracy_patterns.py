import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# 日本語フォントの設定
plt.rcParams['font.family'] = ['Hiragino Sans GB', 'Yu Gothic', 'Meirio', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']

# CSVファイルの読み込み
df = pd.read_csv('advanced_method_accuracy_results.csv')

# データの基本統計
print("=== データの基本情報 ===")
print(f"データ数: {len(df)}")
print(f"\n各手法の誤差の基本統計:")
error_columns = ['従来手法_誤差', '保守的SP_誤差', '高度な手法_誤差']
print(df[error_columns].describe())

# 1. 誤差の符号（プラス/マイナス）の傾向分析
print("\n=== 1. 誤差の符号の傾向 ===")
for col in error_columns:
    positive = (df[col] > 0).sum()
    negative = (df[col] < 0).sum()
    zero = (df[col] == 0).sum()
    print(f"\n{col}:")
    print(f"  プラス誤差: {positive} ({positive/len(df)*100:.1f}%)")
    print(f"  マイナス誤差: {negative} ({negative/len(df)*100:.1f}%)")
    print(f"  誤差なし: {zero} ({zero/len(df)*100:.1f}%)")
    print(f"  平均誤差: {df[col].mean():.1f}")
    print(f"  誤差の絶対値平均: {df[col].abs().mean():.1f}")

# 2. 誤差の大きさと実際の値の関係
print("\n=== 2. 誤差と実際の値の相関 ===")
fig, axes = plt.subplots(2, 3, figsize=(15, 10))

# 最終差玉との関係
for i, col in enumerate(error_columns):
    ax = axes[0, i]
    ax.scatter(df['実際の最終差玉'], df[col], alpha=0.6)
    ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel('実際の最終差玉')
    ax.set_ylabel(col)
    ax.set_title(f'{col} vs 実際の最終差玉')
    
    # 相関係数を計算
    corr = df['実際の最終差玉'].corr(df[col])
    ax.text(0.05, 0.95, f'相関係数: {corr:.3f}', transform=ax.transAxes, 
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# 最大値との関係
for i, col in enumerate(error_columns):
    ax = axes[1, i]
    ax.scatter(df['実際の最大値'], df[col], alpha=0.6)
    ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel('実際の最大値')
    ax.set_ylabel(col)
    ax.set_title(f'{col} vs 実際の最大値')
    
    # 相関係数を計算
    corr = df['実際の最大値'].corr(df[col])
    ax.text(0.05, 0.95, f'相関係数: {corr:.3f}', transform=ax.transAxes,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig('graphs/unified_extracted_data/error_vs_actual_values.png', dpi=300, bbox_inches='tight')
plt.close()

# 3. 台番号との相関分析
print("\n=== 3. 台番号グループ別の誤差分析 ===")
# 台番号を100番台でグループ化
df['台番号グループ'] = (df['台番号'] // 100) * 100

# グループ別の誤差統計
group_stats = df.groupby('台番号グループ')[error_columns].agg(['mean', 'std', 'count'])
print("\n台番号グループ別の平均誤差:")
for col in error_columns:
    print(f"\n{col}:")
    print(group_stats[col].sort_values('mean'))

# 4. 系統的なバイアスの分析
print("\n=== 4. 系統的バイアスの検定 ===")
for col in error_columns:
    # t検定（誤差の平均が0と有意に異なるか）
    t_stat, p_value = stats.ttest_1samp(df[col], 0)
    print(f"\n{col}:")
    print(f"  平均誤差: {df[col].mean():.2f}")
    print(f"  t統計量: {t_stat:.3f}")
    print(f"  p値: {p_value:.4f}")
    if p_value < 0.05:
        print(f"  → 有意な系統的バイアスあり（{'過大評価' if df[col].mean() > 0 else '過小評価'}の傾向）")
    else:
        print(f"  → 有意な系統的バイアスなし")

# 5. 誤差が大きい/小さいケースの特徴
print("\n=== 5. 極端な誤差のケース分析 ===")
for col in error_columns:
    print(f"\n{col}:")
    
    # 誤差の絶対値でソート
    df[f'{col}_絶対値'] = df[col].abs()
    
    # 誤差が大きいトップ5
    print("\n誤差が大きいトップ5:")
    top5 = df.nlargest(5, f'{col}_絶対値')[['画像番号', '台番号', '実際の最終差玉', '実際の最大値', col]]
    print(top5)
    
    # 誤差が小さいトップ5
    print("\n誤差が小さいトップ5:")
    bottom5 = df.nsmallest(5, f'{col}_絶対値')[['画像番号', '台番号', '実際の最終差玉', '実際の最大値', col]]
    print(bottom5)

# 誤差の分布を可視化
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# 誤差のヒストグラム
for i, col in enumerate(error_columns):
    ax = axes[i//2, i%2]
    ax.hist(df[col], bins=30, alpha=0.7, edgecolor='black')
    ax.axvline(x=0, color='r', linestyle='--', alpha=0.5)
    ax.axvline(x=df[col].mean(), color='g', linestyle='-', alpha=0.7, label=f'平均: {df[col].mean():.1f}')
    ax.set_xlabel('誤差')
    ax.set_ylabel('頻度')
    ax.set_title(f'{col}の分布')
    ax.legend()

# 手法間の比較（箱ひげ図）
ax = axes[1, 1]
df[error_columns].plot(kind='box', ax=ax)
ax.set_ylabel('誤差')
ax.set_title('手法間の誤差比較')
ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig('graphs/unified_extracted_data/error_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# 誤差の相関行列
print("\n=== 手法間の誤差の相関 ===")
error_corr = df[error_columns].corr()
print(error_corr)

# 相関行列のヒートマップ（手動で作成）
plt.figure(figsize=(8, 6))
im = plt.imshow(error_corr, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)
plt.colorbar(im, shrink=0.8)

# 相関係数を表示
for i in range(len(error_columns)):
    for j in range(len(error_columns)):
        plt.text(j, i, f'{error_corr.iloc[i, j]:.3f}', 
                ha='center', va='center', color='black', fontsize=10)

plt.xticks(range(len(error_columns)), error_columns, rotation=45, ha='right')
plt.yticks(range(len(error_columns)), error_columns)
plt.title('手法間の誤差の相関行列')
plt.tight_layout()
plt.savefig('graphs/unified_extracted_data/error_correlation_heatmap.png', dpi=300, bbox_inches='tight')
plt.close()

# 改善値の分析
print("\n=== 高度な手法の改善効果 ===")
print(f"改善値の平均: {df['高度な手法_改善値'].mean():.1f}")
print(f"改善値の中央値: {df['高度な手法_改善値'].median():.1f}")
print(f"改善したケース: {(df['高度な手法_改善値'] > 0).sum()} ({(df['高度な手法_改善値'] > 0).sum()/len(df)*100:.1f}%)")
print(f"悪化したケース: {(df['高度な手法_改善値'] < 0).sum()} ({(df['高度な手法_改善値'] < 0).sum()/len(df)*100:.1f}%)")

# 値の範囲別の誤差分析
print("\n=== 値の範囲別の誤差分析 ===")
df['最終差玉範囲'] = pd.cut(df['実際の最終差玉'], 
                         bins=[-30000, -20000, -10000, 0, 10000, 20000, 30000],
                         labels=['極端にマイナス', '大きくマイナス', 'マイナス', 'プラス', '大きくプラス', '極端にプラス'])

for col in error_columns:
    print(f"\n{col}の範囲別平均誤差:")
    range_errors = df.groupby('最終差玉範囲')[col].agg(['mean', 'std', 'count'])
    print(range_errors)

print("\n分析完了!")