#!/usr/bin/env python3
"""
Analyze specific error cases in detail
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# Font configuration for Japanese
font_path = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
if os.path.exists(font_path):
    font_prop = fm.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = font_prop.get_name()

def analyze_error_case(image_name, reported_final, extracted_final):
    """Analyze a specific error case"""
    csv_path = f'graphs/advanced_extracted_data/{image_name}_optimal_data.csv'
    
    if not os.path.exists(csv_path):
        print(f"CSV file not found: {csv_path}")
        return
    
    # Read the data
    df = pd.read_csv(csv_path)
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    fig.suptitle(f'Error Analysis: {image_name}', fontsize=14, fontweight='bold')
    
    # Plot 1: Full extracted data
    ax1.plot(df.index, df['value'], 'b-', alpha=0.7, label='Extracted Values')
    ax1.axhline(y=reported_final, color='r', linestyle='--', alpha=0.7, label=f'Reported Final: {reported_final:,.0f}')
    ax1.axhline(y=extracted_final, color='g', linestyle='--', alpha=0.7, label=f'Extracted Final: {extracted_final:,.0f}')
    
    # Highlight the final portion
    final_portion = len(df) // 10  # Last 10% of data
    ax1.axvspan(len(df) - final_portion, len(df), alpha=0.2, color='yellow', label='Final 10% of data')
    
    ax1.set_xlabel('Data Point Index')
    ax1.set_ylabel('Ball Difference Value')
    ax1.set_title('Full Extracted Data with Reported vs Extracted Comparison')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Focus on final portion
    final_start = max(0, len(df) - final_portion * 2)  # Last 20% of data
    ax2.plot(df.index[final_start:], df['value'].iloc[final_start:], 'b.-', alpha=0.7, markersize=4)
    ax2.axhline(y=reported_final, color='r', linestyle='--', alpha=0.7, label=f'Reported Final: {reported_final:,.0f}')
    ax2.axhline(y=extracted_final, color='g', linestyle='--', alpha=0.7, label=f'Extracted Final: {extracted_final:,.0f}')
    
    # Mark the actual final point
    ax2.plot(df.index[-1], extracted_final, 'go', markersize=10, label='Final Extracted Point')
    
    # Add error annotation
    error = extracted_final - reported_final
    accuracy = 100 - abs(error / reported_final * 100) if reported_final != 0 else 0
    
    ax2.text(0.02, 0.98, f'Error: {error:+,.0f}\nAccuracy: {accuracy:.1f}%', 
            transform=ax2.transAxes, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    ax2.set_xlabel('Data Point Index')
    ax2.set_ylabel('Ball Difference Value')
    ax2.set_title('Focus on Final Portion of Data')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Add statistics
    stats_text = f"Data Statistics:\n"
    stats_text += f"  Total points: {len(df)}\n"
    stats_text += f"  Max value: {df['value'].max():,.0f}\n"
    stats_text += f"  Min value: {df['value'].min():,.0f}\n"
    stats_text += f"  Mean: {df['value'].mean():,.0f}\n"
    stats_text += f"  Std: {df['value'].std():,.0f}\n"
    stats_text += f"  Final 10 values std: {df['value'].iloc[-10:].std():,.0f}"
    
    fig.text(0.02, 0.02, stats_text, transform=fig.transFigure,
            fontsize=10, family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(f'final_value_analysis_{image_name}.png', dpi=300, bbox_inches='tight')
    print(f"Saved analysis for {image_name}")

def main():
    # Analyze the high-error cases
    error_cases = [
        ('S__78209156', 22900, 22705),  # Small error but let's check
        ('S__78209158', -19100, -19573),  # Moderate error
        ('S__78209164', 15450, 15450),  # Blue graph - if data exists
    ]
    
    for image_name, reported, extracted in error_cases:
        print(f"\nAnalyzing {image_name}...")
        analyze_error_case(image_name, reported, extracted)

if __name__ == "__main__":
    main()