import cv2
import numpy as np
import os
from PIL import Image

def find_graph_endpoint(img_path):
    """Find where the graph line actually ends"""
    img = cv2.imread(img_path)
    if img is None:
        return None
    
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    height, width = img.shape[:2]
    
    # Define color ranges for different graph colors
    color_ranges = [
        # Pink/Magenta
        (np.array([140, 50, 50]), np.array([170, 255, 255])),
        # Purple
        (np.array([120, 50, 50]), np.array([150, 255, 255])),
        # Blue
        (np.array([90, 50, 50]), np.array([120, 255, 255]))
    ]
    
    rightmost_x = 0
    
    for lower, upper in color_ranges:
        mask = cv2.inRange(hsv, lower, upper)
        
        # Find rightmost point
        for x in range(width-1, -1, -1):
            if np.any(mask[:, x] > 0):
                rightmost_x = max(rightmost_x, x)
                break
    
    return rightmost_x

# Check all images
input_folder = "graphs/optimal"
results = []

print("Checking where graph data actually ends in each image...")
print(f"{'Image':<30} {'Data ends at X':<15} {'% of width':<15}")
print("-" * 60)

for filename in sorted(os.listdir(input_folder)):
    if filename.endswith('.png'):
        img_path = os.path.join(input_folder, filename)
        img = Image.open(img_path)
        width = img.size[0]
        
        endpoint = find_graph_endpoint(img_path)
        if endpoint:
            percentage = (endpoint / width) * 100
            results.append({
                'file': filename,
                'endpoint': endpoint,
                'width': width,
                'percentage': percentage
            })
            print(f"{filename:<30} {endpoint:<15} {percentage:<15.1f}%")

# Summary statistics
if results:
    endpoints = [r['endpoint'] for r in results]
    percentages = [r['percentage'] for r in results]
    
    print("\nSummary:")
    print(f"Average endpoint: {np.mean(endpoints):.0f} pixels")
    print(f"Min endpoint: {min(endpoints)} pixels")
    print(f"Max endpoint: {max(endpoints)} pixels")
    print(f"Average % of width: {np.mean(percentages):.1f}%")
    print(f"Min % of width: {min(percentages):.1f}%")
    print(f"Max % of width: {max(percentages):.1f}%")
    
    # Check how many stop early
    early_stop_count = sum(1 for p in percentages if p < 90)
    print(f"\nImages where data stops early (< 90% width): {early_stop_count}/{len(results)}")