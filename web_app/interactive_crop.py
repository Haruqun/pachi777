"""
Interactive Crop Component for Streamlit
Uses HTML5 Canvas for interactive rectangle selection
"""

import streamlit as st
import base64
from io import BytesIO
from PIL import Image
import numpy as np

def create_interactive_crop_component(image_array, current_crop_settings):
    """
    Create an interactive crop component using HTML5 Canvas
    """
    
    # Convert numpy array to base64 for displaying in HTML
    img = Image.fromarray(image_array)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    # Current crop settings
    top = current_crop_settings.get('top', 0)
    bottom = current_crop_settings.get('bottom', image_array.shape[0])
    left = current_crop_settings.get('left', 0)
    right = current_crop_settings.get('right', image_array.shape[1])
    
    # HTML and JavaScript for interactive cropping
    html_code = f"""
    <div style="position: relative; display: inline-block;">
        <canvas id="cropCanvas" style="border: 1px solid #ccc; cursor: crosshair;"></canvas>
    </div>
    
    <script>
    (function() {{
        const canvas = document.getElementById('cropCanvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        // Crop rectangle
        let cropRect = {{
            x: {left},
            y: {top},
            width: {right - left},
            height: {bottom - top}
        }};
        
        let isDragging = false;
        let dragStart = null;
        let dragType = null;
        
        img.onload = function() {{
            canvas.width = img.width;
            canvas.height = img.height;
            draw();
        }};
        
        img.src = 'data:image/png;base64,{img_base64}';
        
        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0);
            
            // Draw semi-transparent overlay
            ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Clear the crop area
            ctx.clearRect(cropRect.x, cropRect.y, cropRect.width, cropRect.height);
            ctx.drawImage(img, 
                cropRect.x, cropRect.y, cropRect.width, cropRect.height,
                cropRect.x, cropRect.y, cropRect.width, cropRect.height
            );
            
            // Draw crop rectangle border
            ctx.strokeStyle = '#00ff00';
            ctx.lineWidth = 2;
            ctx.strokeRect(cropRect.x, cropRect.y, cropRect.width, cropRect.height);
            
            // Draw resize handles
            const handleSize = 8;
            ctx.fillStyle = '#00ff00';
            
            // Corners
            ctx.fillRect(cropRect.x - handleSize/2, cropRect.y - handleSize/2, handleSize, handleSize);
            ctx.fillRect(cropRect.x + cropRect.width - handleSize/2, cropRect.y - handleSize/2, handleSize, handleSize);
            ctx.fillRect(cropRect.x - handleSize/2, cropRect.y + cropRect.height - handleSize/2, handleSize, handleSize);
            ctx.fillRect(cropRect.x + cropRect.width - handleSize/2, cropRect.y + cropRect.height - handleSize/2, handleSize, handleSize);
            
            // Mid points
            ctx.fillRect(cropRect.x + cropRect.width/2 - handleSize/2, cropRect.y - handleSize/2, handleSize, handleSize);
            ctx.fillRect(cropRect.x + cropRect.width/2 - handleSize/2, cropRect.y + cropRect.height - handleSize/2, handleSize, handleSize);
            ctx.fillRect(cropRect.x - handleSize/2, cropRect.y + cropRect.height/2 - handleSize/2, handleSize, handleSize);
            ctx.fillRect(cropRect.x + cropRect.width - handleSize/2, cropRect.y + cropRect.height/2 - handleSize/2, handleSize, handleSize);
        }}
        
        function getMousePos(e) {{
            const rect = canvas.getBoundingClientRect();
            return {{
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            }};
        }}
        
        function getHandleType(mousePos) {{
            const tolerance = 10;
            const x = mousePos.x;
            const y = mousePos.y;
            
            // Check corners
            if (Math.abs(x - cropRect.x) < tolerance && Math.abs(y - cropRect.y) < tolerance) return 'nw';
            if (Math.abs(x - (cropRect.x + cropRect.width)) < tolerance && Math.abs(y - cropRect.y) < tolerance) return 'ne';
            if (Math.abs(x - cropRect.x) < tolerance && Math.abs(y - (cropRect.y + cropRect.height)) < tolerance) return 'sw';
            if (Math.abs(x - (cropRect.x + cropRect.width)) < tolerance && Math.abs(y - (cropRect.y + cropRect.height)) < tolerance) return 'se';
            
            // Check edges
            if (Math.abs(x - cropRect.x) < tolerance && y > cropRect.y && y < cropRect.y + cropRect.height) return 'w';
            if (Math.abs(x - (cropRect.x + cropRect.width)) < tolerance && y > cropRect.y && y < cropRect.y + cropRect.height) return 'e';
            if (Math.abs(y - cropRect.y) < tolerance && x > cropRect.x && x < cropRect.x + cropRect.width) return 'n';
            if (Math.abs(y - (cropRect.y + cropRect.height)) < tolerance && x > cropRect.x && x < cropRect.x + cropRect.width) return 's';
            
            // Check inside
            if (x > cropRect.x && x < cropRect.x + cropRect.width && y > cropRect.y && y < cropRect.y + cropRect.height) return 'move';
            
            return null;
        }}
        
        canvas.addEventListener('mousedown', function(e) {{
            const mousePos = getMousePos(e);
            dragType = getHandleType(mousePos);
            
            if (dragType) {{
                isDragging = true;
                dragStart = mousePos;
            }}
        }});
        
        canvas.addEventListener('mousemove', function(e) {{
            const mousePos = getMousePos(e);
            
            if (isDragging && dragType) {{
                const dx = mousePos.x - dragStart.x;
                const dy = mousePos.y - dragStart.y;
                
                switch(dragType) {{
                    case 'move':
                        cropRect.x += dx;
                        cropRect.y += dy;
                        break;
                    case 'n':
                        cropRect.y += dy;
                        cropRect.height -= dy;
                        break;
                    case 's':
                        cropRect.height += dy;
                        break;
                    case 'e':
                        cropRect.width += dx;
                        break;
                    case 'w':
                        cropRect.x += dx;
                        cropRect.width -= dx;
                        break;
                    case 'nw':
                        cropRect.x += dx;
                        cropRect.y += dy;
                        cropRect.width -= dx;
                        cropRect.height -= dy;
                        break;
                    case 'ne':
                        cropRect.y += dy;
                        cropRect.width += dx;
                        cropRect.height -= dy;
                        break;
                    case 'sw':
                        cropRect.x += dx;
                        cropRect.width -= dx;
                        cropRect.height += dy;
                        break;
                    case 'se':
                        cropRect.width += dx;
                        cropRect.height += dy;
                        break;
                }}
                
                // Constrain to canvas
                cropRect.x = Math.max(0, Math.min(canvas.width - cropRect.width, cropRect.x));
                cropRect.y = Math.max(0, Math.min(canvas.height - cropRect.height, cropRect.y));
                cropRect.width = Math.max(50, Math.min(canvas.width - cropRect.x, cropRect.width));
                cropRect.height = Math.max(50, Math.min(canvas.height - cropRect.y, cropRect.height));
                
                dragStart = mousePos;
                draw();
                
                // Send updated crop data to Streamlit
                window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    key: 'crop_selection',
                    value: {{
                        left: Math.round(cropRect.x),
                        top: Math.round(cropRect.y),
                        right: Math.round(cropRect.x + cropRect.width),
                        bottom: Math.round(cropRect.y + cropRect.height)
                    }}
                }}, '*');
            }} else {{
                // Update cursor
                const handleType = getHandleType(mousePos);
                if (handleType === 'move') canvas.style.cursor = 'move';
                else if (handleType === 'n' || handleType === 's') canvas.style.cursor = 'ns-resize';
                else if (handleType === 'e' || handleType === 'w') canvas.style.cursor = 'ew-resize';
                else if (handleType === 'nw' || handleType === 'se') canvas.style.cursor = 'nwse-resize';
                else if (handleType === 'ne' || handleType === 'sw') canvas.style.cursor = 'nesw-resize';
                else canvas.style.cursor = 'default';
            }}
        }});
        
        canvas.addEventListener('mouseup', function(e) {{
            isDragging = false;
            dragType = null;
        }});
        
        canvas.addEventListener('mouseleave', function(e) {{
            isDragging = false;
            dragType = null;
        }});
    }})();
    </script>
    """
    
    return html_code