#!/usr/bin/env python3
"""
Compare stable extracted graph data with reported values from results.txt
"""

import pandas as pd
import numpy as np
import glob
import os
import csv

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
        # stable版では 'smoothed_value' カラムを使用
        if 'smoothed_value' in df.columns:
            max_value = df['smoothed_value'].max()
            final_value = df['smoothed_value'].iloc[-1]  # Last value
            return max_value, final_value
        elif 'value' in df.columns:
            max_value = df['value'].max()
            final_value = df['value'].iloc[-1]  # Last value
            return max_value, final_value
        else:
            print(f"Warning: 'value' or 'smoothed_value' column not found in {csv_path}")
            return None, None
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
        return None, None

def main():
    # Parse results.txt
    reported_values = parse_results_txt('results.txt')
    
    # Get all CSV files from stable extraction
    csv_files = glob.glob('graphs/stable_extracted_data/*_stable_data.csv')
    
    # Prepare comparison data
    comparison_data = []
    
    # Images to skip (blue graphs as mentioned) - 実際には安定版では全て処理
    skip_images = []  # 安定版では全ての画像を処理
    
    for csv_file in sorted(csv_files):
        filename = os.path.basename(csv_file)
        image_name = filename.replace('_optimal_stable_data.csv', '').replace('_stable_data.csv', '')
        
        if image_name in skip_images:
            print(f"Skipping {image_name}")
            continue
        
        if image_name in reported_values:
            extracted_max, extracted_final = analyze_csv_data(csv_file)
            
            if extracted_max is not None and extracted_final is not None:
                reported = reported_values[image_name]
                
                max_diff = extracted_max - reported['reported_max']
                final_diff = extracted_final - reported['reported_final']
                
                # Calculate accuracy percentage
                max_accuracy = 100 - abs(max_diff / reported['reported_max'] * 100) if reported['reported_max'] != 0 else 0
                final_accuracy = 100 - abs(final_diff / reported['reported_final'] * 100) if reported['reported_final'] != 0 else 0
                
                comparison_data.append({
                    'Image': image_name,
                    'Machine': reported['machine'][:20],  # Truncate for display
                    'Reported Max': f"{reported['reported_max']:,.0f}",
                    'Extracted Max': f"{extracted_max:,.0f}",
                    'Max Diff': f"{max_diff:+,.0f}",
                    'Max Acc %': f"{max_accuracy:.1f}%",
                    'Reported Final': f"{reported['reported_final']:,.0f}",
                    'Extracted Final': f"{extracted_final:,.0f}",
                    'Final Diff': f"{final_diff:+,.0f}",
                    'Final Acc %': f"{final_accuracy:.1f}%"
                })
    
    # Print results
    print("\n=== STABLE GRAPH EXTRACTOR COMPARISON REPORT ===\n")
    print("Comparing stable extracted values with reported values from results.txt")
    print("(Positive differences mean extracted value is higher than reported)\n")
    
    if comparison_data:
        # Convert to DataFrame for better formatting
        df = pd.DataFrame(comparison_data)
        
        # Print detailed table
        print(df.to_string(index=False))
        
        # Calculate overall statistics
        print("\n=== OVERALL STATISTICS ===\n")
        
        # Extract numeric values for statistics
        max_diffs = []
        final_diffs = []
        max_accuracies = []
        final_accuracies = []
        for item in comparison_data:
            max_diff = float(item['Max Diff'].replace(',', '').replace('+', ''))
            final_diff = float(item['Final Diff'].replace(',', '').replace('+', ''))
            max_acc = float(item['Max Acc %'].replace('%', ''))
            final_acc = float(item['Final Acc %'].replace('%', ''))
            max_diffs.append(max_diff)
            final_diffs.append(final_diff)
            max_accuracies.append(max_acc)
            final_accuracies.append(final_acc)
        
        print(f"Maximum Value Statistics:")
        print(f"  Average difference: {np.mean(max_diffs):+,.0f}")
        print(f"  Average accuracy: {np.mean(max_accuracies):.1f}%")
        print(f"  Median difference: {np.median(max_diffs):+,.0f}")
        print(f"  Standard deviation: {np.std(max_diffs):,.0f}")
        print(f"  Min difference: {min(max_diffs):+,.0f}")
        print(f"  Max difference: {max(max_diffs):+,.0f}")
        
        print(f"\nFinal Value Statistics:")
        print(f"  Average difference: {np.mean(final_diffs):+,.0f}")
        print(f"  Average accuracy: {np.mean(final_accuracies):.1f}%")
        print(f"  Median difference: {np.median(final_diffs):+,.0f}")
        print(f"  Standard deviation: {np.std(final_diffs):,.0f}")
        print(f"  Min difference: {min(final_diffs):+,.0f}")
        print(f"  Max difference: {max(final_diffs):+,.0f}")
        
        # Count accuracy levels
        high_accuracy_final = sum(1 for acc in final_accuracies if acc >= 90)
        medium_accuracy_final = sum(1 for acc in final_accuracies if 70 <= acc < 90)
        low_accuracy_final = sum(1 for acc in final_accuracies if acc < 70)
        
        print(f"\nFinal Value Accuracy Distribution:")
        print(f"  High accuracy (≥90%): {high_accuracy_final} images")
        print(f"  Medium accuracy (70-90%): {medium_accuracy_final} images")
        print(f"  Low accuracy (<70%): {low_accuracy_final} images")
        
        # 平均絶対誤差で精度計算（300で割る方式）
        avg_abs_max_diff = np.mean([abs(d) for d in max_diffs])
        avg_abs_final_diff = np.mean([abs(d) for d in final_diffs])
        precision_max = 100 - avg_abs_max_diff / 300
        precision_final = 100 - avg_abs_final_diff / 300
        
        print(f"\n精度計算（300で割る方式）:")
        print(f"  最大値精度: {precision_max:.1f}%")
        print(f"  最終値精度: {precision_final:.1f}%")
        
        # Save to CSV
        df.to_csv('stable_extraction_comparison_report.csv', index=False)
        print(f"\nDetailed report saved to: stable_extraction_comparison_report.csv")
        
    else:
        print("No matching data found for comparison.")

if __name__ == "__main__":
    main()