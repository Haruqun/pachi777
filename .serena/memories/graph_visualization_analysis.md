# Graph Visualization Analysis - Claude AI Rotation Marker

## Key Findings

### 1. Where is the graph visualization displayed?
- **File**: `/Users/haruqun/Documents/Work/pachi777/web_app/streamlit_app_full_claude.py`
- **Display location**: Line 3568 - `st.image(result['overlay_image'], use_column_width=True)`
- The cropped graph image with markers is stored in `result['overlay_image']` and displayed using Streamlit's `st.image()` function

### 2. How are the current markers drawn?
- **Library used**: OpenCV (cv2)
- **Implementation location**: Lines 2976-3112 in streamlit_app_full_claude.py
- **Marker drawing code patterns**:
  ```python
  # Circle markers (filled + outline)
  cv2.circle(overlay_img, (int(x), y), 8, color_fill, -1)  # filled circle
  cv2.circle(overlay_img, (int(x), y), 10, color_outline, 2)  # outline circle
  
  # Horizontal lines across full width
  cv2.line(overlay_img, (0, y), (overlay_img.shape[1], y), color, 2)
  
  # Text labels with white background
  cv2.rectangle(overlay_img, (x1, y1), (x2, y2), (255, 255, 255), -1)  # white box
  cv2.putText(overlay_img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, size, color, 1, cv2.LINE_AA)
  ```

### 3. Existing marker colors and implementation

**START (Green marker at zero line)**
- Location: Line 3104-3110
- Position: ゼロライン上 (y = zero_line_in_crop)
- Radius: 10px (filled), 12px (outline)
- Colors: Filled (0, 255, 0), Outline (0, 200, 0)
- Label: "START" positioned above marker

**MAX (Yellow marker)**
- Location: Line 3026-3041
- Colors: Filled (0, 255, 255), Outline (0, 200, 200)
- Radius: 8px (filled), 10px (outline)
- Horizontal line: (0, 255, 255) across full width
- Label: "MAX: {value}" with white background box on the right

**MIN (Magenta marker)**
- Location: Line 3043-3059
- Colors: Filled (255, 0, 255), Outline (200, 0, 200)
- Radius: 8px (filled), 10px (outline)
- Horizontal line: (255, 0, 255) across full width
- Label: "MIN: {value}" with white background box on the right

**CURRENT (Cyan marker at last data point)**
- Location: Line 3061-3077
- Position: Last x-coordinate of graph (graph_data_points[-1][0])
- Colors: Filled (255, 255, 0), Outline (200, 200, 0)
- Radius: 8px (filled), 10px (outline)
- Horizontal line: (255, 255, 0) across full width
- Label: "CURRENT: {value}" with white background box on the right

**FIRST HIT (Purple marker)**
- Location: Line 3079-3096
- Position: At the first hit index in graph_data_points
- Colors: Filled (155, 48, 255), Outline (120, 30, 200)
- Radius: 8px (filled), 10px (outline)
- Horizontal line: (155, 48, 255) across full width
- Label: "FIRST HIT: {value}" with white background box on the right

### 4. How to calculate pixel position from rotation count

**Key Data Available:**
- `spins_per_pixel`: Rotations per pixel (float)
- `rotation_metrics`: Dictionary containing rotation metrics
- `initial_ball_starts`: Claude AI's initial rotations (from Claude API analysis)
- `zero_line_in_crop`: Y-coordinate of zero line in the cropped image
- `graph_start_x`: X-coordinate where the graph starts
- `graph_width`: Total pixel width of the graph

**Formula for X-coordinate from rotation count:**
```python
# If we have initial_ball_starts (rotations) and spins_per_pixel
# X-position from graph start = initial_ball_starts / spins_per_pixel
relative_x_pixels = initial_ball_starts / spins_per_pixel
absolute_x_pixels = graph_start_x + relative_x_pixels
```

**Y-coordinate calculation (value-based):**
```python
# Convert a ball count value to Y-pixel position
def calculate_y_from_value(val):
    return int(zero_line_in_crop - (val / analyzer.scale))
```

### 5. Where rotation metrics data is available

**Data availability:**
- Line 3129-3137: `rotation_metrics` is calculated using `analyzer.calculate_rotation_metrics()`
- Line 3140: Can access `rotation_metrics['spins_per_pixel']`
- Line 3715-3762: Claude AI data including `initial_ball_starts` is displayed in HTML
- Line 3848-3856: `initial_ball_starts` is extracted from prioritized_data

**Key metrics in rotation_metrics dict:**
```python
rotation_metrics = {
    'spins_per_pixel': float,  # Rotations per pixel
    'first_hit_spins': int,     # Rotations to first hit
    'first_hit_balls': int,     # Balls used to first hit
    'rotation_rate_1': float,   # Rate① (rotations per 1000 yen)
    'rotation_rate_2': float,   # Rate② (normal time rotations per 1000 yen)
    'normal_decline_spins': int,# Normal decline rotations
    'normal_decline_balls': int # Normal decline balls
}
```

### 6. How the graph image is created and accessible

**Graph image creation:**
- Line 2976: `overlay_img = cropped_img.copy()`
- The overlay_img is a NumPy array (OpenCV format - BGR)
- All markers are drawn on this image using OpenCV functions

**Graph data availability:**
- `graph_data_points`: List of (x, value) tuples - pixel x-coordinate and ball count value
- `graph_info`: Dictionary with 'start_x' and 'end_x' for graph boundaries
- `zero_line_in_crop`: Y-pixel coordinate of the zero line in cropped image

### 7. Code structure for adding a new marker

**Template for adding Claude AI rotation marker:**
```python
# After line 3111 (after START marker), add:

# Claude AI Rotation Marker (Red marker at initial_ball_starts position)
if initial_ball_starts and spins_per_pixel and spins_per_pixel > 0:
    # Calculate X position from initial_ball_starts
    if 'graph_start_x' in locals() and graph_start_x is not None:
        claude_x = graph_start_x + (initial_ball_starts / spins_per_pixel)
    else:
        claude_x = initial_ball_starts / spins_per_pixel
    
    # Y position at zero line (same as START marker)
    claude_y = zero_line_in_crop
    
    # Only draw if within image bounds
    if 0 <= claude_x < overlay_img.shape[1] and 0 <= claude_y < overlay_img.shape[0]:
        # Draw marker (red color for Claude AI)
        cv2.circle(overlay_img, (int(claude_x), claude_y), 10, (0, 0, 255), -1)      # Red filled
        cv2.circle(overlay_img, (int(claude_x), claude_y), 12, (0, 0, 200), 2)       # Red outline
        
        # Draw label
        label_text = f"Claude AI: {int(initial_ball_starts)} spins"
        cv2.putText(overlay_img, label_text, 
                   (int(claude_x) - 30, claude_y - 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 200), 1, cv2.LINE_AA)
```

### 8. Critical variables at marker drawing stage

When the marker drawing code runs (around line 2976):

Available variables:
- `overlay_img`: NumPy array (OpenCV BGR format) - the image to draw on
- `zero_line_in_crop`: Y-pixel of zero line (int)
- `graph_data_points`: List of (x, value) tuples
- `graph_info`: Dict with 'start_x', 'end_x' keys
- `analyzer`: WebCompatibleAnalyzer instance
- `analyzer.scale`: Balls per pixel ratio
- `cropped_img`: Original cropped image (before overlay)

To access rotation metrics:
- `rotation_metrics`: Already calculated at line 3129 (dict)
- `rotation_metrics['spins_per_pixel']`: Key value for conversion
- `initial_ball_starts`: Available from `prioritized_data` or `claude_data`

### 9. Data flow for Claude AI rotation marker

1. Claude API analyzes detail image (line 3215-3220)
2. `initial_ball_starts` extracted from API result (line 3743-3747)
3. `prioritized_data` aggregates data including `initial_ball_starts` (line 1098-1103)
4. `rotation_metrics` calculated with `spins_per_pixel` (line 3129-3137)
5. Graph overlay drawn with existing markers (line 2976-3112)
6. **THIS IS WHERE CLAUDE AI MARKER SHOULD BE ADDED** (after line 3111)
7. `overlay_img` displayed at line 3568

