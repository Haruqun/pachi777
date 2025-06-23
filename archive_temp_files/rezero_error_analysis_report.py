import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
import os

# Set up font for Japanese text
def setup_japanese_font():
    font_paths = [
        '/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            font_prop = font_manager.FontProperties(fname=font_path)
            plt.rcParams['font.family'] = font_prop.get_name()
            break

setup_japanese_font()

# Read the comparison report
df = pd.read_csv('stable_extraction_comparison_report.csv')

# Filter for Re:Zero machine type
rezero_df = df[df['Machine'].str.contains('e Re：ゼロから始める異世')].copy()

# Clean numeric columns
def clean_numeric(val):
    if pd.isna(val):
        return np.nan
    val_str = str(val).replace(',', '').replace('"', '')
    try:
        return float(val_str)
    except:
        return np.nan

numeric_cols = ['Reported Max', 'Extracted Max', 'Max Diff', 'Reported Final', 'Extracted Final', 'Final Diff']
for col in numeric_cols:
    rezero_df.loc[:, col] = rezero_df[col].apply(clean_numeric)

# Extract accuracy percentages
rezero_df.loc[:, 'Max Acc Float'] = rezero_df['Max Acc %'].str.rstrip('%').astype(float)
rezero_df.loc[:, 'Final Acc Float'] = rezero_df['Final Acc %'].str.rstrip('%').astype(float)

# Create figure with subplots
fig, axes = plt.subplots(2, 2, figsize=(15, 12))
fig.suptitle('Re:Zero Machine Type - Error Analysis Report', fontsize=16, fontweight='bold')

# 1. Accuracy Distribution
ax1 = axes[0, 0]
rezero_df_sorted = rezero_df.sort_values('Final Acc Float')
colors = ['red' if acc < 80 else 'orange' if acc < 90 else 'green' for acc in rezero_df_sorted['Final Acc Float']]
bars = ax1.bar(range(len(rezero_df_sorted)), rezero_df_sorted['Final Acc Float'], color=colors)
ax1.set_xlabel('Image')
ax1.set_ylabel('Final Accuracy %')
ax1.set_title('Final Value Accuracy by Image')
ax1.set_xticks(range(len(rezero_df_sorted)))
ax1.set_xticklabels(rezero_df_sorted['Image'], rotation=45, ha='right')
ax1.axhline(y=80, color='red', linestyle='--', label='80% threshold')
ax1.axhline(y=90, color='orange', linestyle='--', label='90% threshold')
ax1.legend()

# Add value labels on bars
for i, (bar, val) in enumerate(zip(bars, rezero_df_sorted['Final Acc Float'])):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, 
             f'{val:.1f}%', ha='center', va='bottom', fontsize=8)

# 2. Error Magnitude Analysis
ax2 = axes[0, 1]
rezero_df_error = rezero_df.sort_values('Final Diff')
colors2 = ['red' if abs(diff) > 500 else 'orange' if abs(diff) > 300 else 'green' for diff in rezero_df_error['Final Diff']]
bars2 = ax2.bar(range(len(rezero_df_error)), rezero_df_error['Final Diff'], color=colors2)
ax2.set_xlabel('Image')
ax2.set_ylabel('Final Value Difference')
ax2.set_title('Extraction Error (Extracted - Reported)')
ax2.set_xticks(range(len(rezero_df_error)))
ax2.set_xticklabels(rezero_df_error['Image'], rotation=45, ha='right')
ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)

# Add value labels
for i, (bar, val) in enumerate(zip(bars2, rezero_df_error['Final Diff'])):
    ax2.text(bar.get_x() + bar.get_width()/2, 
             bar.get_height() + 50 if val > 0 else bar.get_height() - 50, 
             f'{val:.0f}', ha='center', va='bottom' if val > 0 else 'top', fontsize=8)

# 3. Scatter plot: Max Accuracy vs Final Accuracy
ax3 = axes[1, 0]
scatter_colors = ['red' if acc < 80 else 'orange' if acc < 90 else 'green' for acc in rezero_df['Final Acc Float']]
ax3.scatter(rezero_df['Max Acc Float'], rezero_df['Final Acc Float'], 
            c=scatter_colors, s=100, alpha=0.7, edgecolors='black')
ax3.set_xlabel('Max Value Accuracy %')
ax3.set_ylabel('Final Value Accuracy %')
ax3.set_title('Correlation: Max vs Final Accuracy')
ax3.axhline(y=80, color='red', linestyle='--', alpha=0.5)
ax3.axvline(x=80, color='red', linestyle='--', alpha=0.5)

# Add image labels
for idx, row in rezero_df.iterrows():
    ax3.annotate(row['Image'], (row['Max Acc Float'], row['Final Acc Float']), 
                 xytext=(5, 5), textcoords='offset points', fontsize=8)

# Add correlation coefficient
correlation = rezero_df['Max Acc Float'].corr(rezero_df['Final Acc Float'])
ax3.text(0.05, 0.95, f'Correlation: {correlation:.3f}', transform=ax3.transAxes, 
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# 4. Error Pattern Summary
ax4 = axes[1, 1]
ax4.axis('off')

# Create summary text
summary_text = f"""Error Pattern Summary for Re:Zero Machine Type

Total Images Analyzed: {len(rezero_df)}

Accuracy Distribution:
• High Accuracy (>90%): {len(rezero_df[rezero_df['Final Acc Float'] > 90])} images
• Medium Accuracy (80-90%): {len(rezero_df[(rezero_df['Final Acc Float'] >= 80) & (rezero_df['Final Acc Float'] <= 90)])} images
• Low Accuracy (<80%): {len(rezero_df[rezero_df['Final Acc Float'] < 80])} images

Problematic Images:
"""

# Add details for each problematic image
for _, row in rezero_df[rezero_df['Final Acc Float'] < 80].iterrows():
    summary_text += f"\n{row['Image']}:"
    summary_text += f"\n  • Final Accuracy: {row['Final Acc %']}"
    summary_text += f"\n  • Error: {row['Final Diff']:.0f} balls"
    if row['Extracted Final'] != 0:
        adj_factor = row['Reported Final'] / row['Extracted Final']
        summary_text += f"\n  • Adjustment Factor: {adj_factor:.3f}"

# Add overall statistics
avg_error = rezero_df['Final Diff'].mean()
avg_abs_error = rezero_df['Final Diff'].abs().mean()
summary_text += f"\n\nOverall Statistics:"
summary_text += f"\n• Average Error: {avg_error:.0f} balls"
summary_text += f"\n• Average Absolute Error: {avg_abs_error:.0f} balls"
summary_text += f"\n• Error Direction: {len(rezero_df[rezero_df['Final Diff'] < 0])}/7 underestimated"

ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, 
         fontsize=10, verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))

plt.tight_layout()
plt.savefig('rezero_error_analysis_report.png', dpi=300, bbox_inches='tight')
plt.close()

# Create adjustment factor table
print("\nRe:Zero Machine Type - Adjustment Factor Table")
print("=" * 80)
print(f"{'Image':<15} {'Reported':<10} {'Extracted':<10} {'Accuracy':<10} {'Adj Factor':<10} {'Status'}")
print("-" * 80)

for _, row in rezero_df.sort_values('Final Acc Float').iterrows():
    reported = row['Reported Final']
    extracted = row['Extracted Final']
    accuracy = row['Final Acc Float']
    
    if extracted != 0:
        adj_factor = reported / extracted
    else:
        adj_factor = np.nan
    
    status = "CRITICAL" if accuracy < 80 else "OK" if accuracy > 90 else "WARNING"
    
    print(f"{row['Image']:<15} {reported:>9.0f} {extracted:>10.0f} {accuracy:>9.1f}% {adj_factor:>10.3f} {status}")

# Special analysis for S__78209170
print("\n" + "=" * 80)
print("SPECIAL CASE ANALYSIS: S__78209170")
print("=" * 80)
s170_data = pd.read_csv('graphs/unified_extracted_data/S__78209170_optimal_data.csv')
print(f"Data points analyzed: {len(s170_data)}")
print(f"Value range: {s170_data['value'].min():.0f} to {s170_data['value'].max():.0f}")
print(f"Final extracted value: {s170_data['value'].iloc[-1]:.0f}")
print("\nThis image shows a sign error - the graph was read as negative when it should be positive.")
print("Possible causes:")
print("  1. Zero-line detection failure")
print("  2. Y-axis scale misinterpretation")
print("  3. Graph orientation confusion")

print("\n✓ Analysis complete. Report saved as 'rezero_error_analysis_report.png'")