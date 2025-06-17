# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a pachinko (Japanese pinball gambling) data analysis toolkit written in Python. The project extracts and analyzes data from pachinko machine screenshots, particularly focusing on:
- Graph data extraction from images (difference in ball count over spins)
- Statistical analysis of game performance
- OCR-based text extraction for game statistics
- Image cropping and preprocessing for accurate data extraction

## Development Environment Setup

```bash
# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install dependencies (if needed)
pip install -r requirements.txt  # Note: requirements.txt doesn't exist yet
# Current key dependencies: opencv-python, pillow, numpy, pandas, matplotlib, pytesseract
```

## Common Development Commands

```bash
# Run the main integrated analyzer
python complete_integrated_analyzer.py

# Run specific tools
python perfect_graph_cropper.py      # Crop graphs from screenshots
python perfect_data_extractor.py     # Extract data from cropped graphs
python pachinko_stats_extractor.py   # Extract statistics using OCR

# Test on specific images
python test_precision_on_images.py
python test_with_csv.py
```

## Architecture Overview

### Core Processing Pipeline
1. **Image Input**: Screenshots from pachinko machines (stored in `graphs/`)
2. **Graph Cropping**: 
   - 最適: `graphs/cropped/*_optimal.png` のような689×558px (98%以上の精度)
   - Legacy: `perfect_graph_cropper.py` - 911×797px
3. **Data Extraction**: `perfect_data_extractor.py` - Extracts numerical data from graphs
4. **Statistical Analysis**: Various analyzer scripts process the extracted data
5. **Output**: CSV files, visualization images, and JSON reports

### Key Components

- **Graph Processing**:
  - Optimal graph dimensions: 689×558 pixels (最高精度を実現)
  - Legacy dimensions: 911×797 pixels (perfect_graph_cropper.py)
  - Y-axis range: -30,000 to +30,000 (ball difference)
  - Zero-line detection for accurate calibration
  - Orange bar detection for graph area identification
  - Note: graphs/cropped/*_optimal.png が最適な切り抜きサンプル

- **OCR Integration**:
  - Uses Tesseract for Japanese text recognition
  - Extracts game statistics from UI elements

- **Font Handling**:
  - macOS-specific Japanese font configuration (Hiragino Sans GB)
  - Fallback font handling for cross-platform compatibility

### Data Workflow
1. Place screenshot images in `graphs/` directory
2. Run cropping tool to create standardized graph images in `graphs/cropped_perfect/`
3. Extract data to create CSV files and visualizations in `graphs/extracted_data/`
4. Analysis results saved as JSON reports with timestamps

### Image Processing Standards
- Input images: Various sizes from pachinko machine screenshots
- Optimal cropped graphs: 689×558 pixels (stable_graph_extractor.py用)
- Legacy cropped graphs: 911×797 pixels (perfect_graph_cropper.py)
- Color detection uses HSV color space for reliability
- Multiple detection algorithms for robustness (orange bars, grid lines, zero line)

## Key Technical Details

- **Python Version**: 3.13 (uses .venv virtual environment)
- **Image Processing**: OpenCV for detection, PIL/Pillow for manipulation
- **Data Analysis**: NumPy, Pandas, SciPy for numerical processing
- **Visualization**: Matplotlib with Japanese font support
- **OCR**: Tesseract via pytesseract wrapper

## File Naming Conventions
- Cropped images: `{original_name}_perfect.png`
- Extracted data: `{image_name}_data.csv`
- Visualizations: `{image_name}_visualization.png`, `{image_name}_overlay.png`
- Reports: `perfect_extraction_report_{timestamp}.json`