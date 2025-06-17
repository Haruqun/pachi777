import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

# Load the image
img_path = 'graphs/optimal/S__78209130_optimal.png'
img = cv2.imread(img_path)
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
height, width = img.shape[:2]

print(f"Image dimensions: {width}x{height}")

# Convert to HSV for better color detection
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# Define color range for the pink/magenta graph line
# Pink/Magenta in HSV
lower_pink = np.array([140, 50, 50])
upper_pink = np.array([170, 255, 255])

# Create mask for pink line
mask = cv2.inRange(hsv, lower_pink, upper_pink)

# Find the rightmost point of the graph line
rightmost_x = 0
for x in range(width-1, -1, -1):
    if np.any(mask[:, x] > 0):
        rightmost_x = x
        break

print(f"Rightmost point of graph line: x={rightmost_x}")

# Also check for any non-background pixels (graph elements)
# Convert to grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Find the background color (most common color)
hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
background_color = np.argmax(hist)

print(f"Background color value: {background_color}")

# Create visualization
fig, axes = plt.subplots(2, 2, figsize=(12, 8))

# Original image
axes[0, 0].imshow(img_rgb)
axes[0, 0].set_title('Original Image')
axes[0, 0].axvline(x=620, color='red', linestyle='--', label='Current end_x=620')
axes[0, 0].axvline(x=rightmost_x, color='green', linestyle='--', label=f'Graph end x={rightmost_x}')
axes[0, 0].legend()

# Pink mask
axes[0, 1].imshow(mask, cmap='gray')
axes[0, 1].set_title('Pink Line Mask')
axes[0, 1].axvline(x=620, color='red', linestyle='--')
axes[0, 1].axvline(x=rightmost_x, color='green', linestyle='--')

# Check for text/labels on the right side
# Look for non-background pixels in the right portion
right_portion = gray[:, 550:]
non_bg_mask = np.abs(right_portion.astype(int) - background_color) > 20

axes[1, 0].imshow(right_portion, cmap='gray')
axes[1, 0].set_title('Right portion (x>550)')

axes[1, 1].imshow(non_bg_mask, cmap='gray')
axes[1, 1].set_title('Non-background pixels (right portion)')

plt.tight_layout()
plt.savefig('graphs/graph_end_analysis.png', dpi=150, bbox_inches='tight')
plt.close()

# Find rightmost non-background element
rightmost_element = 550
for x in range(right_portion.shape[1]-1, -1, -1):
    if np.any(non_bg_mask[:, x]):
        rightmost_element = 550 + x
        break

print(f"Rightmost non-background element: x={rightmost_element}")

# Analyze the graph area more precisely
# Look for the actual graph boundary (where the grid/axis lines end)
# Check for vertical lines (edge detection)
edges = cv2.Canny(gray, 50, 150)

# Find vertical lines in the right portion
vertical_lines = []
for x in range(width-1, width-100, -1):  # Check last 100 pixels
    edge_column = edges[:, x]
    if np.sum(edge_column > 0) > height * 0.3:  # Significant vertical edge
        vertical_lines.append(x)
        
if vertical_lines:
    print(f"Detected vertical lines at x positions: {vertical_lines[:5]}")  # Show first 5

# Save edge detection result
plt.figure(figsize=(10, 6))
plt.imshow(edges, cmap='gray')
plt.title('Edge Detection')
plt.axvline(x=620, color='red', linestyle='--', label='Current end_x=620')
if vertical_lines:
    plt.axvline(x=vertical_lines[0], color='yellow', linestyle='--', label=f'First vertical edge x={vertical_lines[0]}')
plt.legend()
plt.savefig('graphs/edge_detection_analysis.png', dpi=150, bbox_inches='tight')
plt.close()

print("\nAnalysis complete. Check 'graphs/graph_end_analysis.png' and 'graphs/edge_detection_analysis.png'")