import pandas as pd
import numpy as np

# Read the CSV file
df = pd.read_csv('stable_extraction_comparison_report.csv')

# Filter for Re:Zero machine type
rezero_df = df[df['Machine'].str.contains('e Re：ゼロから始める異世')]

# Clean numeric columns
def clean_numeric(val):
    if pd.isna(val):
        return np.nan
    val_str = str(val).replace(',', '').replace('"', '')
    try:
        return float(val_str)
    except:
        return np.nan

# Apply cleaning to numeric columns
numeric_cols = ['Reported Max', 'Extracted Max', 'Max Diff', 'Reported Final', 'Extracted Final', 'Final Diff']
for col in numeric_cols:
    rezero_df[col] = rezero_df[col].apply(clean_numeric)

# Extract accuracy percentages
rezero_df['Max Acc Float'] = rezero_df['Max Acc %'].str.rstrip('%').astype(float)
rezero_df['Final Acc Float'] = rezero_df['Final Acc %'].str.rstrip('%').astype(float)

# Sort by Final Accuracy
rezero_df = rezero_df.sort_values('Final Acc Float')

print("Analysis of Re:Zero Machine Type Images")
print("=" * 80)
print("\n1. Images with Low Accuracy (< 80% final value accuracy):")
print("-" * 80)

low_accuracy = rezero_df[rezero_df['Final Acc Float'] < 80]
for _, row in low_accuracy.iterrows():
    print(f"\nImage: {row['Image']}")
    print(f"  Final Accuracy: {row['Final Acc %']}")
    print(f"  Reported Final: {row['Reported Final']:,.0f}")
    print(f"  Extracted Final: {row['Extracted Final']:,.0f}")
    print(f"  Difference: {row['Final Diff']:,.0f}")
    print(f"  Max Value Accuracy: {row['Max Acc %']}")

print("\n2. Adjustment Factors Needed:")
print("-" * 80)

# Calculate adjustment factors for low accuracy images
for _, row in rezero_df.iterrows():
    if row['Final Acc Float'] < 80:
        if row['Extracted Final'] != 0:
            adjustment_factor = row['Reported Final'] / row['Extracted Final']
            print(f"\n{row['Image']}:")
            print(f"  Adjustment Factor: {adjustment_factor:.3f}")
            print(f"  Formula: Extracted Value × {adjustment_factor:.3f} = Reported Value")
            print(f"  Verification: {row['Extracted Final']:,.0f} × {adjustment_factor:.3f} = {row['Extracted Final'] * adjustment_factor:,.0f} (Target: {row['Reported Final']:,.0f})")

print("\n3. Error Pattern Analysis:")
print("-" * 80)

# Analyze patterns
print(f"\nTotal Re:Zero images analyzed: {len(rezero_df)}")
print(f"Images with >90% accuracy: {len(rezero_df[rezero_df['Final Acc Float'] > 90])}")
print(f"Images with 80-90% accuracy: {len(rezero_df[(rezero_df['Final Acc Float'] >= 80) & (rezero_df['Final Acc Float'] <= 90)])}")
print(f"Images with <80% accuracy: {len(rezero_df[rezero_df['Final Acc Float'] < 80])}")

# Check for systematic errors
print("\nError Direction Analysis:")
underestimated = rezero_df[rezero_df['Final Diff'] < 0]
overestimated = rezero_df[rezero_df['Final Diff'] > 0]
print(f"  Underestimated (extracted < reported): {len(underestimated)} images")
print(f"  Overestimated (extracted > reported): {len(overestimated)} images")

# Average errors
avg_error = rezero_df['Final Diff'].mean()
avg_abs_error = rezero_df['Final Diff'].abs().mean()
print(f"\nAverage Error: {avg_error:,.0f}")
print(f"Average Absolute Error: {avg_abs_error:,.0f}")

# Look for correlation between max accuracy and final accuracy
print("\nCorrelation Analysis:")
correlation = rezero_df['Max Acc Float'].corr(rezero_df['Final Acc Float'])
print(f"  Correlation between Max Accuracy and Final Accuracy: {correlation:.3f}")

# Special case analysis for S__78209170
print("\nSpecial Case - S__78209170:")
s170 = rezero_df[rezero_df['Image'] == 'S__78209170'].iloc[0]
print(f"  This image shows extreme error (-521.1% accuracy)")
print(f"  Reported: {s170['Reported Final']:,.0f}")
print(f"  Extracted: {s170['Extracted Final']:,.0f}")
print(f"  The extraction resulted in wrong sign (positive vs negative)")
print(f"  This suggests a fundamental reading error, possibly due to:")
print(f"    - Graph scale misinterpretation")
print(f"    - Zero-line detection failure")
print(f"    - Image quality issues")

# Summary statistics for all Re:Zero images
print("\n4. Summary Statistics:")
print("-" * 80)
print(f"Final Accuracy Statistics:")
print(f"  Mean: {rezero_df['Final Acc Float'].mean():.1f}%")
print(f"  Median: {rezero_df['Final Acc Float'].median():.1f}%")
print(f"  Std Dev: {rezero_df['Final Acc Float'].std():.1f}%")
print(f"  Min: {rezero_df['Final Acc Float'].min():.1f}%")
print(f"  Max: {rezero_df['Final Acc Float'].max():.1f}%")