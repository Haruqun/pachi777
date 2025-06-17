#!/usr/bin/env python3
"""
Visualize final value accuracy comparison
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import glob
import os
import csv

# Font configuration for Japanese
font_path = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
if os.path.exists(font_path):
    font_prop = fm.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = font_prop.get_name()

def parse_results_txt(filepath):
    """Parse the results.txt file to extract reported values"""
    results = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines[1:]:  # Skip header
        # Split by comma but handle quoted values
        reader = csv.reader([line.strip()])
        parts = list(reader)[0] if reader else []
        
        if len(parts) >= 6:
            image_name = parts[0].replace('.jpg', '')
            try:
                # Parse numbers, removing commas and handling empty values
                max_val = parts[4].replace(',', '').replace('"', '') if parts[4] else '0'
                final_val = parts[5].replace(',', '').replace('"', '') if parts[5] else '0'
                
                # Handle empty values
                max_value = float(max_val) if max_val and max_val.strip() else 0
                final_value = float(final_val) if final_val and final_val.strip() else 0
                
                results[image_name] = {
                    'reported_max': max_value,
                    'reported_final': final_value,
                    'machine': parts[3] if len(parts) > 3 else 'Unknown'
                }
            except ValueError as e:
                print(f"Warning: Could not parse values for {image_name}: {e}")
    
    return results

def analyze_csv_data(csv_path):
    """Analyze CSV data to find max and final values"""
    try:
        df = pd.read_csv(csv_path)
        if 'value' in df.columns:
            max_value = df['value'].max()
            final_value = df['value'].iloc[-1]  # Last value
            return max_value, final_value
        else:
            return None, None
    except Exception as e:
        return None, None

def create_accuracy_visualization():
    """Create visualization for final value accuracy"""
    # Parse results.txt
    reported_values = parse_results_txt('results.txt')
    
    # Get all CSV files
    csv_files = glob.glob('graphs/advanced_extracted_data/*_optimal_data.csv')
    
    # Skip blue graphs
    skip_images = ['S__78209160', 'S__78209162', 'S__78209164']
    
    # Prepare data for visualization
    image_names = []
    reported_finals = []
    extracted_finals = []
    differences = []
    accuracy_percentages = []
    
    for csv_file in sorted(csv_files):
        filename = os.path.basename(csv_file)
        image_name = filename.replace('_optimal_data.csv', '')
        
        if image_name in skip_images:
            continue
        
        if image_name in reported_values:
            extracted_max, extracted_final = analyze_csv_data(csv_file)
            
            if extracted_max is not None and extracted_final is not None:
                reported = reported_values[image_name]
                
                image_names.append(image_name)
                reported_finals.append(reported['reported_final'])
                extracted_finals.append(extracted_final)
                diff = extracted_final - reported['reported_final']
                differences.append(diff)
                
                # Calculate accuracy percentage
                if reported['reported_final'] != 0:
                    accuracy = 100 - abs(diff / reported['reported_final'] * 100)
                else:
                    accuracy = 100 if diff == 0 else 0
                accuracy_percentages.append(accuracy)
    
    # Create figure with multiple subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Advanced Graph Extractor Accuracy Analysis', fontsize=16, fontweight='bold')
    
    # 1. Scatter plot: Reported vs Extracted
    ax1 = axes[0, 0]
    ax1.scatter(reported_finals, extracted_finals, alpha=0.7, s=100)
    
    # Add diagonal line for perfect accuracy
    min_val = min(min(reported_finals), min(extracted_finals))
    max_val = max(max(reported_finals), max(extracted_finals))
    ax1.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.5, label='Perfect Match')
    
    # Add labels for each point
    for i, name in enumerate(image_names):
        ax1.annotate(name.replace('S__', ''), 
                    (reported_finals[i], extracted_finals[i]),
                    fontsize=8, alpha=0.7)
    
    ax1.set_xlabel('Reported Final Value')
    ax1.set_ylabel('Extracted Final Value')
    ax1.set_title('Reported vs Extracted Final Values')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 2. Bar chart: Differences
    ax2 = axes[0, 1]
    colors = ['green' if d >= 0 else 'red' for d in differences]
    bars = ax2.bar(range(len(image_names)), differences, color=colors, alpha=0.7)
    ax2.set_xticks(range(len(image_names)))
    ax2.set_xticklabels([name.replace('S__78209', '') for name in image_names], rotation=45)
    ax2.set_xlabel('Image')
    ax2.set_ylabel('Difference (Extracted - Reported)')
    ax2.set_title('Extraction Differences by Image')
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax2.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar, diff in zip(bars, differences):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{diff:+.0f}', ha='center', va='bottom' if height >= 0 else 'top',
                fontsize=8)
    
    # 3. Histogram: Accuracy distribution
    ax3 = axes[1, 0]
    bins = [0, 70, 80, 90, 95, 100]
    counts, _, patches = ax3.hist(accuracy_percentages, bins=bins, edgecolor='black', alpha=0.7)
    
    # Color code the bars
    colors = ['red', 'orange', 'yellow', 'lightgreen', 'green']
    for patch, color in zip(patches, colors):
        patch.set_facecolor(color)
    
    ax3.set_xlabel('Accuracy (%)')
    ax3.set_ylabel('Number of Images')
    ax3.set_title('Final Value Accuracy Distribution')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Add count labels on bars
    for i, count in enumerate(counts):
        if count > 0:
            ax3.text((bins[i] + bins[i+1])/2, count, f'{int(count)}', 
                    ha='center', va='bottom', fontsize=10)
    
    # 4. Box plot: Error distribution
    ax4 = axes[1, 1]
    box_data = [differences, accuracy_percentages]
    bp = ax4.boxplot(box_data, labels=['Differences', 'Accuracy %'], 
                     showmeans=True, meanline=True)
    
    # Add statistics text
    stats_text = f"Differences:\n"
    stats_text += f"  Mean: {np.mean(differences):.0f}\n"
    stats_text += f"  Median: {np.median(differences):.0f}\n"
    stats_text += f"  Std: {np.std(differences):.0f}\n\n"
    stats_text += f"Accuracy:\n"
    stats_text += f"  Mean: {np.mean(accuracy_percentages):.1f}%\n"
    stats_text += f"  Median: {np.median(accuracy_percentages):.1f}%\n"
    stats_text += f"  Min: {min(accuracy_percentages):.1f}%\n"
    stats_text += f"  Max: {max(accuracy_percentages):.1f}%"
    
    ax4.text(0.02, 0.98, stats_text, transform=ax4.transAxes, 
            verticalalignment='top', fontsize=10, family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    ax4.set_title('Error and Accuracy Distribution')
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('final_value_accuracy_analysis.png', dpi=300, bbox_inches='tight')
    print("Saved visualization to: final_value_accuracy_analysis.png")
    
    # Create individual accuracy report for high-error cases
    print("\n=== HIGH ERROR CASES (Accuracy < 90%) ===\n")
    for i, (name, acc, diff, rep, ext) in enumerate(zip(image_names, accuracy_percentages, 
                                                        differences, reported_finals, extracted_finals)):
        if acc < 90:
            print(f"{name}:")
            print(f"  Reported: {rep:,.0f}")
            print(f"  Extracted: {ext:,.0f}")
            print(f"  Difference: {diff:+,.0f}")
            print(f"  Accuracy: {acc:.1f}%")
            print()

if __name__ == "__main__":
    create_accuracy_visualization()