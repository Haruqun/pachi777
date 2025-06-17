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

# Let's analyze the x-axis to understand the scale
# The bottom area of the graph where we can see axis labels
bottom_area = img_rgb[320:, :]  # Bottom portion where axis labels are

# Look for the "80,000" text
# We need to find where the x-axis actually ends based on the axis line, not the data line

# Convert to grayscale for edge detection
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Detect horizontal lines (for x-axis)
edges = cv2.Canny(gray, 50, 150)

# Focus on the area where the x-axis should be (around y=240-250 based on zero line)
x_axis_region = edges[230:260, :]
horizontal_projection = np.sum(x_axis_region, axis=0)

# Find where the x-axis line ends
x_axis_end = 0
for x in range(width-1, -1, -1):
    if horizontal_projection[x] > 5:  # Threshold for detecting line
        x_axis_end = x
        break

print(f"X-axis line detected until x={x_axis_end}")

# Visualize
fig, axes = plt.subplots(3, 1, figsize=(12, 10))

# Original image with markers
axes[0].imshow(img_rgb)
axes[0].set_title('Original Image with Analysis')
axes[0].axvline(x=414, color='green', linestyle='--', label='Data line end (x=414)')
axes[0].axvline(x=620, color='red', linestyle='--', label='Current boundary (x=620)')
axes[0].axvline(x=x_axis_end, color='blue', linestyle='--', label=f'X-axis end (x={x_axis_end})')
axes[0].axhline(y=240, color='yellow', linestyle=':', alpha=0.5, label='X-axis location')
axes[0].legend()

# Edge detection
axes[1].imshow(edges, cmap='gray')
axes[1].set_title('Edge Detection')
axes[1].axvline(x=x_axis_end, color='blue', linestyle='--')

# Horizontal projection of x-axis region
axes[2].plot(horizontal_projection)
axes[2].set_title('Horizontal Line Detection (X-axis region)')
axes[2].set_xlabel('X position')
axes[2].set_ylabel('Edge strength')
axes[2].axvline(x=x_axis_end, color='blue', linestyle='--', label=f'X-axis end (x={x_axis_end})')
axes[2].axvline(x=620, color='red', linestyle='--', label='Current boundary')
axes[2].legend()

plt.tight_layout()
plt.savefig('graphs/graph_structure_analysis.png', dpi=150, bbox_inches='tight')
plt.close()

# Now let's understand the scaling
# We know:
# - The graph starts at x=36 (from config)
# - The pink line ends at x=414
# - The x-axis label shows 80,000
# - The "最大値 : 9060" at the bottom suggests max rotation value

# Let's try to find the actual graph boundaries by detecting the grid/axis lines
# Look for vertical grid lines
vertical_edges = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
vertical_edges = np.abs(vertical_edges)

# Sum vertically to find strong vertical lines
vertical_projection = np.sum(vertical_edges[50:300, :], axis=0)  # Focus on graph area

# Find peaks (vertical lines)
from scipy.signal import find_peaks
peaks, _ = find_peaks(vertical_projection, height=1000, distance=20)

print(f"\nDetected vertical lines at x positions: {peaks[:10]}...")  # Show first 10

# The rightmost significant vertical line
if len(peaks) > 0:
    rightmost_grid = peaks[-1]
    print(f"Rightmost vertical grid line at x={rightmost_grid}")

# Create a detailed view of the right edge
fig, ax = plt.subplots(1, 1, figsize=(10, 6))
ax.imshow(img_rgb[:, 400:], aspect='auto')
ax.set_title('Right portion of graph (x > 400)')
ax.axvline(x=14, color='green', linestyle='--', label='Data ends here')
ax.axvline(x=220, color='red', linestyle='--', label='Current boundary')

# Add text annotations for key x-positions
ax.text(14, 50, 'x=414', rotation=90, color='green')
ax.text(220, 50, 'x=620', rotation=90, color='red')
ax.text(200, 320, '80,000', color='black', bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.5))

ax.legend()
plt.savefig('graphs/right_edge_detail.png', dpi=150, bbox_inches='tight')
plt.close()

print("\nAnalysis complete. The issue is that the data line ends at x=414, but the x-axis scale continues to 80,000.")
print("The extraction should map the x-axis range (36 to ~620) to the rotation range (0 to 80,000).")
print("\nCheck 'graphs/graph_structure_analysis.png' and 'graphs/right_edge_detail.png' for visualizations.")