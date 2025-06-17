#!/usr/bin/env python3
"""
Compare extracted graph data with reported values from results.txt
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
        if 'value' in df.columns:
            max_value = df['value'].max()
            final_value = df['value'].iloc[-1]  # Last value
            return max_value, final_value
        else:
            print(f"Warning: 'value' column not found in {csv_path}")
            return None, None
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
        return None, None

def main():
    # Parse results.txt
    reported_values = parse_results_txt('results.txt')
    
    # Get all CSV files
    csv_files = glob.glob('graphs/advanced_extracted_data/*_optimal_data.csv')
    
    # Prepare comparison data
    comparison_data = []
    
    # Images to skip (blue graphs as mentioned)
    skip_images = ['S__78209160', 'S__78209162', 'S__78209164']
    
    for csv_file in sorted(csv_files):
        filename = os.path.basename(csv_file)
        image_name = filename.replace('_optimal_data.csv', '')
        
        if image_name in skip_images:
            print(f"Skipping {image_name} (blue graph)")
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
    print("\n=== ADVANCED GRAPH EXTRACTOR COMPARISON REPORT ===\n")
    print("Comparing extracted values with reported values from results.txt")
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
        for item in comparison_data:
            max_diff = float(item['Max Diff'].replace(',', '').replace('+', ''))
            final_diff = float(item['Final Diff'].replace(',', '').replace('+', ''))
            max_diffs.append(max_diff)
            final_diffs.append(final_diff)
        
        print(f"Maximum Value Differences:")
        print(f"  Average difference: {np.mean(max_diffs):+,.0f}")
        print(f"  Median difference: {np.median(max_diffs):+,.0f}")
        print(f"  Standard deviation: {np.std(max_diffs):,.0f}")
        print(f"  Min difference: {min(max_diffs):+,.0f}")
        print(f"  Max difference: {max(max_diffs):+,.0f}")
        
        print(f"\nFinal Value Differences:")
        print(f"  Average difference: {np.mean(final_diffs):+,.0f}")
        print(f"  Median difference: {np.median(final_diffs):+,.0f}")
        print(f"  Standard deviation: {np.std(final_diffs):,.0f}")
        print(f"  Min difference: {min(final_diffs):+,.0f}")
        print(f"  Max difference: {max(final_diffs):+,.0f}")
        
        # Count accuracy levels
        high_accuracy_final = sum(1 for item in comparison_data if float(item['Final Acc %'].replace('%', '')) >= 90)
        medium_accuracy_final = sum(1 for item in comparison_data if 70 <= float(item['Final Acc %'].replace('%', '')) < 90)
        low_accuracy_final = sum(1 for item in comparison_data if float(item['Final Acc %'].replace('%', '')) < 70)
        
        print(f"\nFinal Value Accuracy Distribution:")
        print(f"  High accuracy (≥90%): {high_accuracy_final} images")
        print(f"  Medium accuracy (70-90%): {medium_accuracy_final} images")
        print(f"  Low accuracy (<70%): {low_accuracy_final} images")
        
        # Save to CSV
        df.to_csv('extraction_comparison_report.csv', index=False)
        print(f"\nDetailed report saved to: extraction_comparison_report.csv")
        
    else:
        print("No matching data found for comparison.")

if __name__ == "__main__":
    main()