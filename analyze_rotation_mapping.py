import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

# Load image
img_path = 'graphs/optimal/S__78209130_optimal.png'
img = cv2.imread(img_path)
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# Current boundaries
boundaries = {
    "start_x": 36,
    "end_x": 620,
    "top_y": 29,
    "zero_y": 274,
    "bottom_y": 520
}

# Analysis results
data_end_x = 414  # Where the pink line ends
x_axis_end = 610  # Where the x-axis line ends
max_rotation_label = 80000  # The label we see on the right

# Current mapping calculation
current_width = boundaries["end_x"] - boundaries["start_x"]  # 584 pixels
current_mapping = f"0 to {max_rotation_label} mapped to x={boundaries['start_x']} to x={boundaries['end_x']}"

# Where data actually ends
data_width = data_end_x - boundaries["start_x"]  # 378 pixels
data_end_rotation = int((data_end_x - boundaries["start_x"]) * max_rotation_label / current_width)

print("Current Configuration Analysis:")
print(f"X-axis range: {boundaries['start_x']} to {boundaries['end_x']} ({current_width} pixels)")
print(f"Rotation range: 0 to {max_rotation_label}")
print(f"Pixels per 10,000 rotations: {current_width / (max_rotation_label/10000):.1f}")
print()
print("Actual Data Analysis:")
print(f"Data line ends at x={data_end_x}")
print(f"This corresponds to rotation: {data_end_rotation}")
print(f"Data exists for {data_width/current_width*100:.1f}% of the x-axis range")
print()
print("The Issue:")
print(f"The extraction is trying to extract data from x={data_end_x} to x={boundaries['end_x']}")
print(f"But there's no graph line in that region!")
print()
print("Solution Options:")
print("1. Stop extraction at x=414 (where data ends)")
print("2. Adjust the rotation mapping to account for partial data")
print("3. Use the x-axis labels to determine correct scaling")

# Visualize the mapping issue
fig, ax = plt.subplots(1, 1, figsize=(12, 6))

# Create a diagram showing the mapping
ax.set_xlim(0, 650)
ax.set_ylim(0, 100)

# X-axis representation
ax.plot([boundaries["start_x"], boundaries["end_x"]], [50, 50], 'k-', linewidth=3, label='Current extraction range')
ax.plot([boundaries["start_x"], data_end_x], [50, 50], 'g-', linewidth=6, label='Actual data range')

# Add markers
ax.scatter([boundaries["start_x"]], [50], s=100, c='blue', zorder=5)
ax.scatter([data_end_x], [50], s=100, c='green', zorder=5)
ax.scatter([boundaries["end_x"]], [50], s=100, c='red', zorder=5)

# Labels
ax.text(boundaries["start_x"], 40, 'x=36\n(0)', ha='center', va='top')
ax.text(data_end_x, 40, f'x={data_end_x}\n({data_end_rotation})', ha='center', va='top', color='green')
ax.text(boundaries["end_x"], 40, f'x=620\n({max_rotation_label})', ha='center', va='top', color='red')

# Add rotation scale
y_scale = 70
ax.plot([boundaries["start_x"], boundaries["end_x"]], [y_scale, y_scale], 'b--', alpha=0.5)
for i in range(0, max_rotation_label+1, 20000):
    x_pos = boundaries["start_x"] + (boundaries["end_x"] - boundaries["start_x"]) * i / max_rotation_label
    ax.plot([x_pos, x_pos], [y_scale-2, y_scale+2], 'b-', alpha=0.5)
    ax.text(x_pos, y_scale+5, f'{i//1000}k', ha='center', fontsize=8, color='blue')

ax.set_title('X-axis to Rotation Mapping Issue', fontsize=14)
ax.legend()
ax.set_yticks([])
ax.set_xlabel('X coordinate (pixels)')

plt.tight_layout()
plt.savefig('graphs/rotation_mapping_analysis.png', dpi=150, bbox_inches='tight')
plt.close()

print("\nVisualization saved to 'graphs/rotation_mapping_analysis.png'")