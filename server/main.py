from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from pathlib import Path
import requests
from PIL import Image
from io import BytesIO
import numpy as np
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️ pytesseract not available, OCR will be disabled")

try:
    from coloraide import Color
    OKLCH_AVAILABLE = True
except ImportError:
    OKLCH_AVAILABLE = False
    print("⚠️ coloraide not available, OKLCH suggestions will be disabled")

app = FastAPI(title="Color Accessibility Checker MCP Server")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get base URL from environment or default
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Serve static files from dist directory if they exist (optional)
dist_path = Path(__file__).parent.parent / "web" / "dist"
assets_path = dist_path / "assets"

if assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

@app.get("/")
async def root():
    return {"message": "Color Accessibility Checker MCP Server", "status": "running"}

@app.get("/widget")
async def widget():
    """Serve the widget HTML for testing"""
    widget_html_path = dist_path / "index.html"
    
    if not widget_html_path.exists():
        return HTMLResponse(
            content="<h1>Widget not built yet. Run 'npm run build' in the web directory.</h1>",
            status_code=404
        )
    
    with open(widget_html_path, "r") as f:
        html_content = f.read()
    
    # Replace relative paths with absolute URLs
    html_content = html_content.replace('href="/', f'href="{BASE_URL}/')
    html_content = html_content.replace('src="/', f'src="{BASE_URL}/')
    
    return HTMLResponse(content=html_content)

# Store generated widgets in memory
WIDGET_CACHE = {}

def calculate_luminance(r, g, b):
    """Calculate relative luminance according to WCAG"""
    def normalize(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * normalize(r) + 0.7152 * normalize(g) + 0.0722 * normalize(b)

def calculate_contrast_ratio(rgb1, rgb2):
    """Calculate contrast ratio between two RGB colors"""
    l1 = calculate_luminance(rgb1[0], rgb1[1], rgb1[2])
    l2 = calculate_luminance(rgb2[0], rgb2[1], rgb2[2])
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

def rgb_to_hex(r, g, b):
    """Convert RGB to hex color"""
    return f"#{r:02x}{g:02x}{b:02x}".upper()

def evaluate_wcag(ratio):
    """Evaluate WCAG compliance for a contrast ratio"""
    return {
        "passes_aa_normal": ratio >= 4.5,
        "passes_aa_large": ratio >= 3.0,
        "passes_aaa_normal": ratio >= 7.0,
        "passes_aaa_large": ratio >= 4.5
    }

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def generate_oklch_suggestions(bg_hex, fg_hex, target_ratio=4.5):
    """Generate OKLCH color suggestions to improve contrast"""
    suggestions = []
    
    if not OKLCH_AVAILABLE:
        return suggestions
    
    try:
        # Convert to OKLCH using coloraide
        bg_color = Color(bg_hex)
        fg_color = Color(fg_hex)
        
        bg_oklch = bg_color.convert('oklch')
        fg_oklch = fg_color.convert('oklch')
        
        # Option 1: Lighten background
        for delta in [0.1, 0.2, 0.3, 0.4, 0.5]:
            new_bg_oklch = bg_oklch.clone()
            new_bg_oklch.set('lightness', min(1.0, bg_oklch.lightness + delta))
            new_bg_hex = new_bg_oklch.convert('srgb').to_string(hex=True, fit=True)
            new_bg_rgb = hex_to_rgb(new_bg_hex)
            fg_rgb = hex_to_rgb(fg_hex)
            
            ratio = calculate_contrast_ratio(new_bg_rgb, fg_rgb)
            if ratio >= target_ratio:
                suggestions.append({
                    "type": "lighten_bg",
                    "background_oklch": new_bg_oklch.to_string(),
                    "foreground_oklch": fg_oklch.to_string(),
                    "new_contrast_ratio": round(ratio, 1),
                    "preview_hex_bg": new_bg_hex,
                    "preview_hex_fg": fg_hex
                })
                break
        
        # Option 2: Darken background
        for delta in [-0.1, -0.2, -0.3, -0.4, -0.5]:
            new_bg_oklch = bg_oklch.clone()
            new_bg_oklch.set('lightness', max(0.0, bg_oklch.lightness + delta))
            new_bg_hex = new_bg_oklch.convert('srgb').to_string(hex=True, fit=True)
            new_bg_rgb = hex_to_rgb(new_bg_hex)
            fg_rgb = hex_to_rgb(fg_hex)
            
            ratio = calculate_contrast_ratio(new_bg_rgb, fg_rgb)
            if ratio >= target_ratio:
                suggestions.append({
                    "type": "darken_bg",
                    "background_oklch": new_bg_oklch.to_string(),
                    "foreground_oklch": fg_oklch.to_string(),
                    "new_contrast_ratio": round(ratio, 1),
                    "preview_hex_bg": new_bg_hex,
                    "preview_hex_fg": fg_hex
                })
                break
        
        # Option 3: Adjust foreground
        fg_delta = -0.3 if fg_oklch.lightness > 0.5 else 0.3
        new_fg_oklch = fg_oklch.clone()
        new_fg_oklch.set('lightness', max(0.0, min(1.0, fg_oklch.lightness + fg_delta)))
        new_fg_hex = new_fg_oklch.convert('srgb').to_string(hex=True, fit=True)
        new_fg_rgb = hex_to_rgb(new_fg_hex)
        bg_rgb = hex_to_rgb(bg_hex)
        
        ratio = calculate_contrast_ratio(bg_rgb, new_fg_rgb)
        if ratio >= target_ratio:
            suggestions.append({
                "type": "adjust_fg",
                "background_oklch": bg_oklch.to_string(),
                "foreground_oklch": new_fg_oklch.to_string(),
                "new_contrast_ratio": round(ratio, 1),
                "preview_hex_bg": bg_hex,
                "preview_hex_fg": new_fg_hex
            })
    
    except Exception as e:
        print(f"⚠️ Error generating OKLCH suggestions: {e}")
    
    return suggestions

def analyze_image_colors_from_pil(img: Image.Image, wcag_level: str = "AA"):
    """Analyze color accessibility from a PIL Image object"""
    try:
        img = img.convert('RGB')
        
        # Resize if too large for faster processing
        max_size = 1000
        if img.width > max_size or img.height > max_size:
            ratio = min(max_size / img.width, max_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            print(f"📐 Resized to: {new_size}")
        
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        print(f"🖼️ Image dimensions: {width}x{height}")
        
        color_pairs = []
        
        # Try OCR first if available
        if OCR_AVAILABLE:
            try:
                print("🔍 Using OCR to detect text...")
                # Use pytesseract to get word bounding boxes
                ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang='eng+spa')
                
                words_found = []
                for i in range(len(ocr_data['text'])):
                    text = ocr_data['text'][i].strip()
                    conf = int(ocr_data['conf'][i])
                    if text and conf > 60:  # Confidence threshold
                        x = ocr_data['left'][i]
                        y = ocr_data['top'][i]
                        w = ocr_data['width'][i]
                        h = ocr_data['height'][i]
                        words_found.append({
                            'text': text,
                            'bbox': (x, y, x + w, y + h),
                            'confidence': conf
                        })
                
                print(f"📝 Found {len(words_found)} text regions with OCR")
                
                # Analyze each word region
                for word in words_found[:50]:  # Limit to 50 words
                    x0, y0, x1, y1 = word['bbox']
                    x0, y0 = max(0, x0 - 5), max(0, y0 - 5)
                    x1, y1 = min(width, x1 + 5), min(height, y1 + 5)
                    
                    if x1 <= x0 or y1 <= y0:
                        continue
                    
                    region = img_array[y0:y1, x0:x1]
                    if region.size == 0:
                        continue
                    
                    pixels = region.reshape(-1, 3)
                    
                    # Foreground: center of text region
                    center_y, center_x = (y1 - y0) // 2, (x1 - x0) // 2
                    if center_y * (x1 - x0) + center_x < len(pixels):
                        fg_color = tuple(pixels[center_y * (x1 - x0) + center_x])
                    else:
                        continue
                    
                    # Background: average of edge pixels
                    edge_pixels = []
                    if region.shape[0] > 0 and region.shape[1] > 0:
                        edge_pixels.extend(region[0, :].reshape(-1, 3))
                        if region.shape[0] > 1:
                            edge_pixels.extend(region[-1, :].reshape(-1, 3))
                        edge_pixels.extend(region[:, 0].reshape(-1, 3))
                        if region.shape[1] > 1:
                            edge_pixels.extend(region[:, -1].reshape(-1, 3))
                    
                    if not edge_pixels:
                        continue
                    
                    bg_color = tuple(np.mean(edge_pixels, axis=0).astype(int))
                    
                    # Calculate contrast
                    ratio = calculate_contrast_ratio(fg_color, bg_color)
                    wcag = evaluate_wcag(ratio)
                    
                    # Determine which is foreground (darker) and background (lighter)
                    fg_lum = calculate_luminance(*fg_color)
                    bg_lum = calculate_luminance(*bg_color)
                    
                    if fg_lum > bg_lum:
                        fg_color, bg_color = bg_color, fg_color
                        ratio = calculate_contrast_ratio(fg_color, bg_color)
                        wcag = evaluate_wcag(ratio)
                    
                    bg_hex = rgb_to_hex(*bg_color)
                    fg_hex = rgb_to_hex(*fg_color)
                    
                    # Generate OKLCH suggestions if it doesn't pass
                    suggestions = []
                    target_ratio = 7.0 if wcag_level == "AAA" else 4.5
                    if not wcag["passes_aa_normal"]:
                        suggestions = generate_oklch_suggestions(bg_hex, fg_hex, target_ratio)
                    
                    color_pairs.append({
                        "text_sample": word['text'],
                        "background": bg_hex,
                        "foreground": fg_hex,
                        "ratio": round(ratio, 1),
                        "passes_aa_normal": wcag["passes_aa_normal"],
                        "passes_aa_large": wcag["passes_aa_large"],
                        "passes_aaa_normal": wcag["passes_aaa_normal"],
                        "passes_aaa_large": wcag["passes_aaa_large"],
                        "suggestions": suggestions
                    })
            
            except Exception as e:
                print(f"⚠️ OCR failed: {e}, falling back to region sampling")
        
        # Fallback: sample regions if OCR not available or failed
        if not color_pairs:
            print("📊 Sampling regions (OCR not available or failed)...")
            # Ensure we always sample at least some regions
            sample_regions = max(10, min(30, (width * height) // 5000))
            print(f"📊 Will sample {sample_regions} regions")
            
            for i in range(sample_regions):
                x = np.random.randint(0, max(1, width - 50))
                y = np.random.randint(0, max(1, height - 50))
                region_w = min(50, width - x)
                region_h = min(50, height - y)
                
                region = img_array[y:y+region_h, x:x+region_w]
                
                # Validate region
                if region.size == 0 or region.shape[0] == 0 or region.shape[1] == 0:
                    continue
                
                pixels = region.reshape(-1, 3)
                
                if len(pixels) == 0:
                    continue
                
                center_y, center_x = region_h // 2, region_w // 2
                pixel_idx = center_y * region_w + center_x
                
                if pixel_idx >= len(pixels):
                    pixel_idx = len(pixels) // 2
                
                fg_color = tuple(pixels[pixel_idx])
                
                # Get edge pixels safely
                edge_pixels = []
                if region.shape[0] > 0:
                    edge_pixels.extend(region[0, :].reshape(-1, 3))
                if region.shape[0] > 1:
                    edge_pixels.extend(region[-1, :].reshape(-1, 3))
                if region.shape[1] > 0:
                    edge_pixels.extend(region[:, 0].reshape(-1, 3))
                if region.shape[1] > 1:
                    edge_pixels.extend(region[:, -1].reshape(-1, 3))
                
                if not edge_pixels:
                    # Fallback: use corners
                    edge_pixels = [
                        region[0, 0],
                        region[0, -1] if region.shape[1] > 1 else region[0, 0],
                        region[-1, 0] if region.shape[0] > 1 else region[0, 0],
                        region[-1, -1] if (region.shape[0] > 1 and region.shape[1] > 1) else region[0, 0]
                    ]
                
                bg_color = tuple(np.mean(edge_pixels, axis=0).astype(int))
                
                ratio = calculate_contrast_ratio(fg_color, bg_color)
                wcag = evaluate_wcag(ratio)
                
                fg_lum = calculate_luminance(*fg_color)
                bg_lum = calculate_luminance(*bg_color)
                
                if fg_lum > bg_lum:
                    fg_color, bg_color = bg_color, fg_color
                    ratio = calculate_contrast_ratio(fg_color, bg_color)
                    wcag = evaluate_wcag(ratio)
                
                bg_hex = rgb_to_hex(*bg_color)
                fg_hex = rgb_to_hex(*fg_color)
                
                # Generate OKLCH suggestions if it doesn't pass
                suggestions = []
                target_ratio = 7.0 if wcag_level == "AAA" else 4.5
                if not wcag["passes_aa_normal"]:
                    suggestions = generate_oklch_suggestions(bg_hex, fg_hex, target_ratio)
                
                color_pairs.append({
                    "text_sample": f"Sample {i+1}",
                    "background": bg_hex,
                    "foreground": fg_hex,
                    "ratio": round(ratio, 1),
                    "passes_aa_normal": wcag["passes_aa_normal"],
                    "passes_aa_large": wcag["passes_aa_large"],
                    "passes_aaa_normal": wcag["passes_aaa_normal"],
                    "passes_aaa_large": wcag["passes_aaa_large"],
                    "suggestions": suggestions
                })
        
        # Remove duplicates and sort by ratio
        unique_pairs = {}
        for pair in color_pairs:
            key = (pair["background"], pair["foreground"])
            if key not in unique_pairs or pair["ratio"] < unique_pairs[key]["ratio"]:
                unique_pairs[key] = pair
        
        color_pairs = list(unique_pairs.values())
        color_pairs.sort(key=lambda x: x["ratio"], reverse=True)
        
        passed_pairs = sum(1 for p in color_pairs if p["passes_aa_normal"])
        failed_pairs = len(color_pairs) - passed_pairs
        
        print(f"✅ Analysis complete: {len(color_pairs)} unique color pairs found")
        print(f"   - Passed: {passed_pairs}, Failed: {failed_pairs}")
        
        if len(color_pairs) == 0:
            print("⚠️ WARNING: No color pairs found! This might indicate an issue with image processing.")
            print(f"   Image size: {width}x{height}, Array shape: {img_array.shape}")
        
        return {
            "total_pairs": len(color_pairs),
            "passed_pairs": passed_pairs,
            "failed_pairs": failed_pairs,
            "color_pairs": color_pairs[:15]  # Limit to top 15
        }
        
    except Exception as e:
        print(f"❌ Error analyzing image: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty data on error
        return {
            "total_pairs": 0,
            "passed_pairs": 0,
            "failed_pairs": 0,
            "color_pairs": []
        }

def analyze_image_colors(image_url: str, wcag_level: str = "AA"):
    """Analyze color accessibility in an image from URL"""
    try:
        print(f"📥 Downloading image from: {image_url}")
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        print(f"✅ Image downloaded, size: {len(response.content)} bytes")
        img = Image.open(BytesIO(response.content))
        return analyze_image_colors_from_pil(img, wcag_level)
        
    except Exception as e:
        print(f"❌ Error downloading/analyzing image: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "total_pairs": 0,
            "passed_pairs": 0,
            "failed_pairs": 0,
            "color_pairs": []
        }

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP JSON-RPC 2.0 endpoint"""
    body = await request.json()
    
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")
    
    # Handle MCP protocol methods
    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "serverInfo": {
                    "name": "color-accessibility-checker",
                    "version": "1.0.0"
                }
            }
        })
    
    elif method == "resources/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "resources": [
                    {
                        "uri": "ui://widget/color-accessibility.html",
                        "name": "Color Accessibility Widget",
                        "description": "Interactive widget for color accessibility analysis",
                        "mimeType": "text/html+skybridge"
                    }
                ]
            }
        })
    
    elif method == "resources/read":
        uri = params.get("uri")
        
        # Static HTML template with client-side rendering logic
        # Using the improved UI from web/ui-template.html
        widget_html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Color Accessibility Checker</title>
  <!-- DATA_INJECTION_POINT -->
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: transparent; padding: 20px; min-height: 600px; }
    .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 16px; padding: 32px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07); }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
    .header h1 { font-size: 24px; font-weight: 600; display: flex; align-items: center; gap: 8px; color: #1d1d1f; }
    .share-btn { background: #f0f0f0; border: none; border-radius: 8px; padding: 10px 12px; cursor: pointer; font-size: 18px; }
    .summary-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 32px; }
    .summary-card { background: #f8f8f8; border-radius: 12px; padding: 24px; text-align: center; }
    .summary-icon { font-size: 32px; margin-bottom: 8px; }
    .summary-value { font-size: 32px; font-weight: 700; margin-bottom: 4px; color: #1d1d1f; }
    .summary-label { font-size: 14px; color: #86868b; text-transform: capitalize; }
    .tabs { display: flex; gap: 8px; margin-bottom: 24px; }
    .tab { flex: 1; padding: 12px 24px; border: none; border-radius: 8px; font-size: 16px; font-weight: 500; cursor: pointer; transition: all 0.2s; }
    .tab.active { background: #007AFF; color: white; }
    .tab:not(.active) { background: #f0f0f0; color: #1d1d1f; }
    .tab:not(.active):hover { background: #e5e5e5; }
    .color-pairs-list { display: flex; flex-direction: column; gap: 24px; }
    .color-pair-card { border: 1px solid #e5e5e5; border-radius: 12px; padding: 20px; }
    .pair-header { font-size: 14px; color: #86868b; margin-bottom: 12px; font-weight: 500; }
    .color-preview-section { display: flex; gap: 16px; align-items: center; margin-bottom: 16px; }
    .color-preview { flex: 1; height: 80px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: 600; border: 1px solid rgba(0, 0, 0, 0.1); }
    .ratio-info { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
    .ratio-badge { background: #34C759; color: white; padding: 6px 12px; border-radius: 6px; font-weight: 600; font-size: 14px; }
    .ratio-badge.fail { background: #FF3B30; }
    .ratio-value { font-size: 20px; font-weight: 600; color: #1d1d1f; }
    .color-codes { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
    .color-code { font-family: 'Monaco', 'Courier New', monospace; font-size: 13px; padding: 8px 12px; background: #f5f5f5; border-radius: 6px; color: #1d1d1f; }
    .color-code-label { font-size: 11px; color: #86868b; margin-bottom: 4px; text-transform: uppercase; font-weight: 600; }
    .suggestions-section { border-top: 1px solid #e5e5e5; padding-top: 20px; margin-top: 16px; }
    .suggestions-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
    .suggestions-header h4 { font-size: 14px; font-weight: 600; color: #1d1d1f; }
    .fail-badge { background: #FF3B30; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }
    .suggestions-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
    .suggestion-card { border: 2px solid #34C759; border-radius: 10px; padding: 16px; background: #f9fff9; }
    .suggestion-preview { height: 60px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 600; margin-bottom: 12px; border: 1px solid rgba(0, 0, 0, 0.1); }
    .suggestion-badge { background: #34C759; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; margin-bottom: 8px; }
    .suggestion-type { font-size: 11px; color: #86868b; text-transform: uppercase; margin-bottom: 6px; font-weight: 600; }
    .suggestion-color { font-family: 'Monaco', 'Courier New', monospace; font-size: 11px; background: white; padding: 6px 8px; border-radius: 4px; margin-bottom: 4px; color: #1d1d1f; }
    .suggestion-ratio { font-size: 13px; font-weight: 600; color: #34C759; margin-top: 6px; }
    .wcag-levels { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
    .wcag-badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
    .wcag-badge.pass { background: #d1f4e0; color: #0f6537; }
    .wcag-badge.fail { background: #ffe5e5; color: #c41e3a; }
    .empty-state { text-align: center; padding: 60px 20px; color: #86868b; }
    .empty-state-icon { font-size: 48px; margin-bottom: 16px; }
    #loading { text-align: center; padding: 60px 20px; color: #86868b; }
    #content { display: none; }
    #debug-log { font-family: monospace; font-size: 10px; color: #999; margin-top: 20px; padding: 10px; background: #f5f5f5; border-radius: 4px; white-space: pre-wrap; display: none; }
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <div class="header">
      <h1>Color Accessibility Checker 🎨✅</h1>
      <button class="share-btn">📤</button>
    </div>

    <div id="loading">
        <p>Waiting for analysis data...</p>
    </div>

    <div id="content">
        <!-- Summary Cards -->
        <div class="summary-cards">
        <div class="summary-card">
            <div class="summary-icon">✅</div>
            <div class="summary-value" id="passing-count">0</div>
            <div class="summary-label">Passing</div>
        </div>
        <div class="summary-card">
            <div class="summary-icon">❌</div>
            <div class="summary-value" id="failing-count">0</div>
            <div class="summary-label">Failures</div>
        </div>
        <div class="summary-card">
            <div class="summary-icon">👁️</div>
            <div class="summary-value" id="texts-count">0</div>
            <div class="summary-label">Texts</div>
        </div>
        </div>

        <!-- Tabs -->
        <div class="tabs">
        <button class="tab active" onclick="showTab('colors')">Colors</button>
        <button class="tab" onclick="showTab('vision')">Vision</button>
        </div>

        <!-- Content -->
        <div id="colors-content" class="color-pairs-list">
        <!-- Color pairs will be injected here -->
        </div>

        <div id="vision-content" style="display: none;">
        <div class="empty-state">
            <div class="empty-state-icon">👁️</div>
            <p>Vision simulation coming soon...</p>
        </div>
        </div>
    </div>
    
    <div id="debug-log"></div>
  </div>

  <script>
    function log(msg) {
        const el = document.getElementById('debug-log');
        el.textContent += msg + '\\n';
        console.log(msg);
    }

    // Show debug log if loading takes too long
    setTimeout(() => {
        if (document.getElementById('loading').style.display !== 'none') {
            document.getElementById('debug-log').style.display = 'block';
            log('⚠️ Timeout waiting for data. Showing debug log.');
            log('Current window.__ACCESSIBILITY_DATA__: ' + (window.__ACCESSIBILITY_DATA__ ? 'Present' : 'Missing'));
        }
    }, 3000);

    function showTab(tabName) {
      document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
      });
      event.target.classList.add('active');

      document.getElementById('colors-content').style.display = 
        tabName === 'colors' ? 'flex' : 'none';
      document.getElementById('vision-content').style.display = 
        tabName === 'vision' ? 'block' : 'none';
    }

    function getWCAGBadge(level, passes) {
      return `<span class="wcag-badge ${passes ? 'pass' : 'fail'}">${level}: ${passes ? '✓' : '✗'}</span>`;
    }

    function renderColorPair(pair) {
      const suggestionTypeLabels = {
        lighten_bg: 'Lighten Background',
        darken_bg: 'Darken Background',
        adjust_fg: 'Adjust Foreground'
      };

      // Handle suggestions if they exist (assuming future implementation)
      const suggestions = pair.suggestions || [];
      
      const suggestionsHTML = suggestions.length > 0 ? `
        <div class="suggestions-section">
          <div class="suggestions-header">
            <span class="fail-badge">Fail</span>
            <h4>OKLCH Suggestions</h4>
          </div>
          <div class="suggestions-grid">
            ${suggestions.map(sugg => `
              <div class="suggestion-card">
                <div class="suggestion-preview" style="background: ${sugg.preview_hex_bg}; color: ${sugg.preview_hex_fg};">
                  Aa
                </div>
                <div class="suggestion-badge">✅ Fixed</div>
                <div class="suggestion-type">${suggestionTypeLabels[sugg.type] || sugg.type}</div>
                <div class="suggestion-color">${sugg.background_oklch}</div>
                <div class="suggestion-color">${sugg.foreground_oklch}</div>
                <div class="suggestion-ratio">Ratio: ${sugg.new_contrast_ratio}:1</div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : '';

      // Determine status based on passes_aa_normal (or other logic)
      const isPass = pair.passes_aa_normal;
      const statusLabel = isPass ? 'Pass' : 'Fail';

      return `
        <div class="color-pair-card">
          <div class="pair-header">Original ${pair.text_sample ? `"${pair.text_sample}"` : ''}</div>
          
          <div class="color-preview-section">
            <div class="color-preview" style="background: ${pair.background}; color: ${pair.foreground};">
              Aa
            </div>
            
            <div class="ratio-info">
              <div class="ratio-badge ${isPass ? '' : 'fail'}">
                ${statusLabel}
              </div>
              <div class="ratio-value">Ratio: ${pair.ratio}:1</div>
            </div>
          </div>

          <div class="color-codes">
            <div>
              <div class="color-code-label">Background</div>
              <div class="color-code">${pair.background}</div>
            </div>
            <div>
              <div class="color-code-label">Foreground</div>
              <div class="color-code">${pair.foreground}</div>
            </div>
          </div>

          <div class="wcag-levels">
            ${getWCAGBadge('AA Normal', pair.passes_aa_normal)}
            ${getWCAGBadge('AA Large', pair.passes_aa_large)}
            ${getWCAGBadge('AAA Normal', pair.passes_aaa_normal)}
            ${getWCAGBadge('AAA Large', pair.passes_aaa_large)}
          </div>

          ${suggestionsHTML}
        </div>
      `;
    }

    function renderResults(data) {
      log('Rendering results...');
      log('Data received: ' + JSON.stringify({
        total_pairs: data.total_pairs,
        passed_pairs: data.passed_pairs,
        failed_pairs: data.failed_pairs,
        color_pairs_length: data.color_pairs ? data.color_pairs.length : 0
      }));
      
      if (!data || !data.color_pairs || data.color_pairs.length === 0) {
        log('⚠️ No color pairs to render! Data structure: ' + JSON.stringify(data, null, 2));
        document.getElementById('loading').style.display = 'none';
        document.getElementById('content').style.display = 'block';
        document.getElementById('passing-count').textContent = '0';
        document.getElementById('failing-count').textContent = '0';
        document.getElementById('texts-count').textContent = '0';
        document.getElementById('colors-content').innerHTML = '<div class="empty-state"><p>No color pairs found in the image</p></div>';
        return;
      }
      
      document.getElementById('loading').style.display = 'none';
      document.getElementById('content').style.display = 'block';

      // Update summary
      document.getElementById('passing-count').textContent = data.passed_pairs || 0;
      document.getElementById('failing-count').textContent = data.failed_pairs || 0;
      document.getElementById('texts-count').textContent = data.total_pairs || 0;

      // Render color pairs
      const container = document.getElementById('colors-content');
      container.innerHTML = data.color_pairs.map(pair => renderColorPair(pair)).join('');
      log('Render complete.');
    }

    // Check for server-injected data immediately (Tutorial Pattern)
    log('Checking for injected data...');
    if (window.__ACCESSIBILITY_DATA__) {
        log('✅ Injected data found!');
        renderResults(window.__ACCESSIBILITY_DATA__);
    } else {
        log('⏳ No injected data found. Waiting for toolOutput...');
    }

    // Listen for data from ChatGPT (Standard Pattern)
    window.addEventListener('openai:set_globals', (event) => {
        const globals = event.detail?.globals;
        if (!globals) {
            return;
        }
        
        // Update window.openai with the new globals
        if (!window.openai) {
            window.openai = {};
        }
        Object.assign(window.openai, globals);
        
        // Only process if toolOutput exists and has data
        if (!globals.toolOutput) {
            // This is normal - toolInput arrives first, toolOutput comes later
            return;
        }
        
        log('📩 Received openai:set_globals event with toolOutput');
        log('toolOutput keys: ' + JSON.stringify(Object.keys(globals.toolOutput)));
        
        // Try to find data in different possible locations
        let data = null;
        
        // Check if toolOutput is the data itself
        if (globals.toolOutput.total_pairs !== undefined) {
            data = globals.toolOutput;
            log('✅ Found data directly in toolOutput');
        } 
        // Check toolOutput.accessibility
        else if (globals.toolOutput.accessibility) {
            data = globals.toolOutput.accessibility;
            log('✅ Found globals.toolOutput.accessibility');
        }
        // Check toolOutput.data
        else if (globals.toolOutput.data) {
            data = globals.toolOutput.data;
            log('✅ Found globals.toolOutput.data');
        }
        
        // Check other possible locations
        if (!data && globals.data) {
            data = globals.data;
            log('✅ Found globals.data');
        } else if (!data && globals.accessibility) {
            data = globals.accessibility;
            log('✅ Found globals.accessibility');
        }
        
        if (data) {
            renderResults(data);
        } else {
            log('⚠️ toolOutput exists but no recognizable data structure found');
        }
    });

    // Also check if data is already available on window.openai
    if (window.openai && window.openai.toolOutput) {
        log('Checking window.openai for existing data...');
        const globals = window.openai;
        
        let data = null;
        
        // Check if toolOutput is the data itself
        if (globals.toolOutput.total_pairs !== undefined) {
            data = globals.toolOutput;
            log('✅ Found data directly in window.openai.toolOutput');
        }
        // Check toolOutput.accessibility
        else if (globals.toolOutput.accessibility) {
            data = globals.toolOutput.accessibility;
            log('✅ Found window.openai.toolOutput.accessibility');
        }
        // Check toolOutput.data
        else if (globals.toolOutput.data) {
            data = globals.toolOutput.data;
            log('✅ Found window.openai.toolOutput.data');
        }
        
        if (data) {
            renderResults(data);
        }
    }
  </script>
</body>
</html>
"""
        
        if uri == "ui://widget/color-accessibility.html":
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "text/html+skybridge",
                            "text": widget_html
                        }
                    ]
                }
            })
        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Resource not found: {uri}"
                }
            })
    
    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "analyze_color_accessibility",
                        "description": "Analyze color accessibility in an image according to WCAG standards. Detects text and background colors, calculates contrast ratios, and provides OKLCH color suggestions for improvements. Provide the image URL when available.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "image_url": {
                                    "type": "string",
                                    "description": "URL of the image to analyze (required)"
                                },
                                "wcag_level": {
                                    "type": "string",
                                    "enum": ["AA", "AAA"],
                                    "description": "WCAG conformance level to check against (default: AA)",
                                    "default": "AA"
                                }
                            },
                            "required": ["image_url"]
                        },
                        "_meta": {
                            "openai/outputTemplate": "ui://widget/color-accessibility.html",
                            "openai/widgetAccessible": True
                        }
                    }
                ]
            }
        })
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "analyze_color_accessibility":
            image_url = arguments.get("image_url")
            wcag_level = arguments.get("wcag_level", "AA")
            
            print(f"🎨 Received request to analyze image")
            print(f"📊 WCAG Level: {wcag_level}")
            print(f"📝 Image URL/data type: {type(image_url)}")
            print(f"📝 Image URL/data preview: {str(image_url)[:100]}...")
            
            # Handle data URL (base64) from ChatGPT
            if image_url and image_url.startswith("data:image"):
                print("📥 Processing data URL (base64 image)")
                try:
                    # Extract base64 data
                    if ',' not in image_url:
                        raise ValueError("Invalid data URL format: no comma found")
                    
                    header, encoded = image_url.split(',', 1)
                    print(f"📝 Data URL header: {header[:50]}...")
                    print(f"📝 Base64 length: {len(encoded)} characters")
                    
                    import base64
                    try:
                        image_data = base64.b64decode(encoded, validate=True)
                        print(f"✅ Decoded {len(image_data)} bytes from base64")
                    except Exception as e:
                        print(f"❌ Base64 decode error: {e}")
                        raise ValueError(f"Invalid base64 data: {e}")
                    
                    # Validate image data
                    if len(image_data) < 100:
                        raise ValueError(f"Image data too small: {len(image_data)} bytes")
                    
                    # Try to open image directly from bytes first (more reliable)
                    try:
                        img = Image.open(BytesIO(image_data))
                        # Force load to validate image
                        img.load()
                        print(f"✅ Image loaded successfully: {img.format}, {img.size}, {img.mode}")
                    except Exception as e:
                        print(f"⚠️ Direct load failed: {e}, trying temp file...")
                        # Fallback to temp file
                        from tempfile import NamedTemporaryFile
                        import os
                        with NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                            tmp_file.write(image_data)
                            tmp_path = tmp_file.name
                        
                        try:
                            img = Image.open(tmp_path)
                            img.load()  # Force load to validate
                            print(f"✅ Image loaded from temp file: {img.format}, {img.size}, {img.mode}")
                        finally:
                            # Clean up temp file
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                    
                    # Convert to RGB
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Use the same analysis function
                    accessibility_data = analyze_image_colors_from_pil(img, wcag_level)
                    
                except Exception as e:
                    print(f"❌ Error processing base64 image: {e}")
                    import traceback
                    traceback.print_exc()
                    # Return error data
                    accessibility_data = {
                        "total_pairs": 0,
                        "passed_pairs": 0,
                        "failed_pairs": 0,
                        "color_pairs": [],
                        "error": f"Error processing image: {str(e)}"
                    }
            else:
                # Analyze from URL
                print(f"📥 Processing image URL")
                accessibility_data = analyze_image_colors(image_url, wcag_level)
            
            print(f"📊 Final data: {accessibility_data['total_pairs']} pairs, {accessibility_data['passed_pairs']} passed, {accessibility_data['failed_pairs']} failed")
            
            # Validate data before sending
            if accessibility_data['total_pairs'] == 0:
                print("⚠️ WARNING: Sending empty data! Check logs above for errors.")
                print(f"   Data structure: {json.dumps(accessibility_data, indent=2)}")
            
            # We need to redefine widget_html here because it's scoped to resources/read above
            # In a real app, this would be a shared constant or template file
            widget_html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Color Accessibility Checker</title>
  <!-- DATA_INJECTION_POINT -->
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: transparent; padding: 20px; min-height: 600px; }
    .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 16px; padding: 32px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07); }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
    .header h1 { font-size: 24px; font-weight: 600; display: flex; align-items: center; gap: 8px; color: #1d1d1f; }
    .share-btn { background: #f0f0f0; border: none; border-radius: 8px; padding: 10px 12px; cursor: pointer; font-size: 18px; }
    .summary-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 32px; }
    .summary-card { background: #f8f8f8; border-radius: 12px; padding: 24px; text-align: center; }
    .summary-icon { font-size: 32px; margin-bottom: 8px; }
    .summary-value { font-size: 32px; font-weight: 700; margin-bottom: 4px; color: #1d1d1f; }
    .summary-label { font-size: 14px; color: #86868b; text-transform: capitalize; }
    .tabs { display: flex; gap: 8px; margin-bottom: 24px; }
    .tab { flex: 1; padding: 12px 24px; border: none; border-radius: 8px; font-size: 16px; font-weight: 500; cursor: pointer; transition: all 0.2s; }
    .tab.active { background: #007AFF; color: white; }
    .tab:not(.active) { background: #f0f0f0; color: #1d1d1f; }
    .tab:not(.active):hover { background: #e5e5e5; }
    .color-pairs-list { display: flex; flex-direction: column; gap: 24px; }
    .color-pair-card { border: 1px solid #e5e5e5; border-radius: 12px; padding: 20px; }
    .pair-header { font-size: 14px; color: #86868b; margin-bottom: 12px; font-weight: 500; }
    .color-preview-section { display: flex; gap: 16px; align-items: center; margin-bottom: 16px; }
    .color-preview { flex: 1; height: 80px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: 600; border: 1px solid rgba(0, 0, 0, 0.1); }
    .ratio-info { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
    .ratio-badge { background: #34C759; color: white; padding: 6px 12px; border-radius: 6px; font-weight: 600; font-size: 14px; }
    .ratio-badge.fail { background: #FF3B30; }
    .ratio-value { font-size: 20px; font-weight: 600; color: #1d1d1f; }
    .color-codes { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
    .color-code { font-family: 'Monaco', 'Courier New', monospace; font-size: 13px; padding: 8px 12px; background: #f5f5f5; border-radius: 6px; color: #1d1d1f; }
    .color-code-label { font-size: 11px; color: #86868b; margin-bottom: 4px; text-transform: uppercase; font-weight: 600; }
    .suggestions-section { border-top: 1px solid #e5e5e5; padding-top: 20px; margin-top: 16px; }
    .suggestions-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
    .suggestions-header h4 { font-size: 14px; font-weight: 600; color: #1d1d1f; }
    .fail-badge { background: #FF3B30; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }
    .suggestions-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
    .suggestion-card { border: 2px solid #34C759; border-radius: 10px; padding: 16px; background: #f9fff9; }
    .suggestion-preview { height: 60px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 600; margin-bottom: 12px; border: 1px solid rgba(0, 0, 0, 0.1); }
    .suggestion-badge { background: #34C759; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; margin-bottom: 8px; }
    .suggestion-type { font-size: 11px; color: #86868b; text-transform: uppercase; margin-bottom: 6px; font-weight: 600; }
    .suggestion-color { font-family: 'Monaco', 'Courier New', monospace; font-size: 11px; background: white; padding: 6px 8px; border-radius: 4px; margin-bottom: 4px; color: #1d1d1f; }
    .suggestion-ratio { font-size: 13px; font-weight: 600; color: #34C759; margin-top: 6px; }
    .wcag-levels { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
    .wcag-badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
    .wcag-badge.pass { background: #d1f4e0; color: #0f6537; }
    .wcag-badge.fail { background: #ffe5e5; color: #c41e3a; }
    .empty-state { text-align: center; padding: 60px 20px; color: #86868b; }
    .empty-state-icon { font-size: 48px; margin-bottom: 16px; }
    #loading { text-align: center; padding: 60px 20px; color: #86868b; }
    #content { display: none; }
    #debug-log { font-family: monospace; font-size: 10px; color: #999; margin-top: 20px; padding: 10px; background: #f5f5f5; border-radius: 4px; white-space: pre-wrap; display: none; }
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <div class="header">
      <h1>Color Accessibility Checker 🎨✅</h1>
      <button class="share-btn">📤</button>
    </div>

    <div id="loading">
        <p>Waiting for analysis data...</p>
    </div>

    <div id="content">
        <!-- Summary Cards -->
        <div class="summary-cards">
        <div class="summary-card">
            <div class="summary-icon">✅</div>
            <div class="summary-value" id="passing-count">0</div>
            <div class="summary-label">Passing</div>
        </div>
        <div class="summary-card">
            <div class="summary-icon">❌</div>
            <div class="summary-value" id="failing-count">0</div>
            <div class="summary-label">Failures</div>
        </div>
        <div class="summary-card">
            <div class="summary-icon">👁️</div>
            <div class="summary-value" id="texts-count">0</div>
            <div class="summary-label">Texts</div>
        </div>
        </div>

        <!-- Tabs -->
        <div class="tabs">
        <button class="tab active" onclick="showTab('colors')">Colors</button>
        <button class="tab" onclick="showTab('vision')">Vision</button>
        </div>

        <!-- Content -->
        <div id="colors-content" class="color-pairs-list">
        <!-- Color pairs will be injected here -->
        </div>

        <div id="vision-content" style="display: none;">
        <div class="empty-state">
            <div class="empty-state-icon">👁️</div>
            <p>Vision simulation coming soon...</p>
        </div>
        </div>
    </div>
    
    <div id="debug-log"></div>
  </div>

  <script>
    function log(msg) {
        const el = document.getElementById('debug-log');
        el.textContent += msg + '\\n';
        console.log(msg);
    }

    // Show debug log if loading takes too long
    setTimeout(() => {
        if (document.getElementById('loading').style.display !== 'none') {
            document.getElementById('debug-log').style.display = 'block';
            log('⚠️ Timeout waiting for data. Showing debug log.');
            log('Current window.__ACCESSIBILITY_DATA__: ' + (window.__ACCESSIBILITY_DATA__ ? 'Present' : 'Missing'));
        }
    }, 3000);

    function showTab(tabName) {
      document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
      });
      event.target.classList.add('active');

      document.getElementById('colors-content').style.display = 
        tabName === 'colors' ? 'flex' : 'none';
      document.getElementById('vision-content').style.display = 
        tabName === 'vision' ? 'block' : 'none';
    }

    function getWCAGBadge(level, passes) {
      return `<span class="wcag-badge ${passes ? 'pass' : 'fail'}">${level}: ${passes ? '✓' : '✗'}</span>`;
    }

    function renderColorPair(pair) {
      const suggestionTypeLabels = {
        lighten_bg: 'Lighten Background',
        darken_bg: 'Darken Background',
        adjust_fg: 'Adjust Foreground'
      };

      // Handle suggestions if they exist (assuming future implementation)
      const suggestions = pair.suggestions || [];
      
      const suggestionsHTML = suggestions.length > 0 ? `
        <div class="suggestions-section">
          <div class="suggestions-header">
            <span class="fail-badge">Fail</span>
            <h4>OKLCH Suggestions</h4>
          </div>
          <div class="suggestions-grid">
            ${suggestions.map(sugg => `
              <div class="suggestion-card">
                <div class="suggestion-preview" style="background: ${sugg.preview_hex_bg}; color: ${sugg.preview_hex_fg};">
                  Aa
                </div>
                <div class="suggestion-badge">✅ Fixed</div>
                <div class="suggestion-type">${suggestionTypeLabels[sugg.type] || sugg.type}</div>
                <div class="suggestion-color">${sugg.background_oklch}</div>
                <div class="suggestion-color">${sugg.foreground_oklch}</div>
                <div class="suggestion-ratio">Ratio: ${sugg.new_contrast_ratio}:1</div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : '';

      // Determine status based on passes_aa_normal (or other logic)
      const isPass = pair.passes_aa_normal;
      const statusLabel = isPass ? 'Pass' : 'Fail';

      return `
        <div class="color-pair-card">
          <div class="pair-header">Original ${pair.text_sample ? `"${pair.text_sample}"` : ''}</div>
          
          <div class="color-preview-section">
            <div class="color-preview" style="background: ${pair.background}; color: ${pair.foreground};">
              Aa
            </div>
            
            <div class="ratio-info">
              <div class="ratio-badge ${isPass ? '' : 'fail'}">
                ${statusLabel}
              </div>
              <div class="ratio-value">Ratio: ${pair.ratio}:1</div>
            </div>
          </div>

          <div class="color-codes">
            <div>
              <div class="color-code-label">Background</div>
              <div class="color-code">${pair.background}</div>
            </div>
            <div>
              <div class="color-code-label">Foreground</div>
              <div class="color-code">${pair.foreground}</div>
            </div>
          </div>

          <div class="wcag-levels">
            ${getWCAGBadge('AA Normal', pair.passes_aa_normal)}
            ${getWCAGBadge('AA Large', pair.passes_aa_large)}
            ${getWCAGBadge('AAA Normal', pair.passes_aaa_normal)}
            ${getWCAGBadge('AAA Large', pair.passes_aaa_large)}
          </div>

          ${suggestionsHTML}
        </div>
      `;
    }

    function renderResults(data) {
      log('Rendering results...');
      log('Data received: ' + JSON.stringify({
        total_pairs: data.total_pairs,
        passed_pairs: data.passed_pairs,
        failed_pairs: data.failed_pairs,
        color_pairs_length: data.color_pairs ? data.color_pairs.length : 0
      }));
      
      if (!data || !data.color_pairs || data.color_pairs.length === 0) {
        log('⚠️ No color pairs to render! Data structure: ' + JSON.stringify(data, null, 2));
        document.getElementById('loading').style.display = 'none';
        document.getElementById('content').style.display = 'block';
        document.getElementById('passing-count').textContent = '0';
        document.getElementById('failing-count').textContent = '0';
        document.getElementById('texts-count').textContent = '0';
        document.getElementById('colors-content').innerHTML = '<div class="empty-state"><p>No color pairs found in the image</p></div>';
        return;
      }
      
      document.getElementById('loading').style.display = 'none';
      document.getElementById('content').style.display = 'block';

      // Update summary
      document.getElementById('passing-count').textContent = data.passed_pairs || 0;
      document.getElementById('failing-count').textContent = data.failed_pairs || 0;
      document.getElementById('texts-count').textContent = data.total_pairs || 0;

      // Render color pairs
      const container = document.getElementById('colors-content');
      container.innerHTML = data.color_pairs.map(pair => renderColorPair(pair)).join('');
      log('Render complete.');
    }

    // Check for server-injected data immediately (Tutorial Pattern)
    log('Checking for injected data...');
    if (window.__ACCESSIBILITY_DATA__) {
        log('✅ Injected data found!');
        renderResults(window.__ACCESSIBILITY_DATA__);
    } else {
        log('⏳ No injected data found. Waiting for toolOutput...');
    }

    // Listen for data from ChatGPT (Standard Pattern)
    window.addEventListener('openai:set_globals', (event) => {
        const globals = event.detail?.globals;
        if (!globals) {
            return;
        }
        
        // Update window.openai with the new globals
        if (!window.openai) {
            window.openai = {};
        }
        Object.assign(window.openai, globals);
        
        // Only process if toolOutput exists and has data
        if (!globals.toolOutput) {
            // This is normal - toolInput arrives first, toolOutput comes later
            return;
        }
        
        log('📩 Received openai:set_globals event with toolOutput');
        log('toolOutput keys: ' + JSON.stringify(Object.keys(globals.toolOutput)));
        
        // Try to find data in different possible locations
        let data = null;
        
        // Check if toolOutput is the data itself
        if (globals.toolOutput.total_pairs !== undefined) {
            data = globals.toolOutput;
            log('✅ Found data directly in toolOutput');
        } 
        // Check toolOutput.accessibility
        else if (globals.toolOutput.accessibility) {
            data = globals.toolOutput.accessibility;
            log('✅ Found globals.toolOutput.accessibility');
        }
        // Check toolOutput.data
        else if (globals.toolOutput.data) {
            data = globals.toolOutput.data;
            log('✅ Found globals.toolOutput.data');
        }
        
        // Check other possible locations
        if (!data && globals.data) {
            data = globals.data;
            log('✅ Found globals.data');
        } else if (!data && globals.accessibility) {
            data = globals.accessibility;
            log('✅ Found globals.accessibility');
        }
        
        if (data) {
            renderResults(data);
        } else {
            log('⚠️ toolOutput exists but no recognizable data structure found');
        }
    });

    // Also check if data is already available on window.openai
    if (window.openai && window.openai.toolOutput) {
        log('Checking window.openai for existing data...');
        const globals = window.openai;
        
        let data = null;
        
        // Check if toolOutput is the data itself
        if (globals.toolOutput.total_pairs !== undefined) {
            data = globals.toolOutput;
            log('✅ Found data directly in window.openai.toolOutput');
        }
        // Check toolOutput.accessibility
        else if (globals.toolOutput.accessibility) {
            data = globals.toolOutput.accessibility;
            log('✅ Found window.openai.toolOutput.accessibility');
        }
        // Check toolOutput.data
        else if (globals.toolOutput.data) {
            data = globals.toolOutput.data;
            log('✅ Found window.openai.toolOutput.data');
        }
        
        if (data) {
            renderResults(data);
        }
    }
  </script>
</body>
</html>
"""
            
            # INJECT DATA DIRECTLY INTO HTML (Tutorial Pattern)
            # FIX: Use explicit placeholder to guarantee injection point
            json_data = json.dumps(accessibility_data)
            injection = f"<script>window.__ACCESSIBILITY_DATA__ = {json_data};</script>"
            
            widget_html_with_data = widget_html.replace("<!-- DATA_INJECTION_POINT -->", injection)
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"🎨 Analyzed image from URL: {image_url[:50]}...\n\n📊 WCAG {wcag_level}: {accessibility_data['total_pairs']} color pairs found. {accessibility_data['passed_pairs']} passed, {accessibility_data['failed_pairs']} failed."
                        },
                        {
                            "type": "resource",
                            "resource": {
                                "uri": "ui://widget/color-accessibility.html",
                                "mimeType": "text/html+skybridge",
                                "text": widget_html_with_data
                            }
                        }
                    ],
                    "isError": False,
                    "structuredContent": {
                        "data": accessibility_data,
                        "_meta": {
                            "openai/outputTemplate": {
                                "type": "resource",
                                "resource": "ui://widget/color-accessibility.html"
                            }
                        }
                    },
                    "toolOutput": {
                        "accessibility": accessibility_data
                    }
                }
            })
        
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Tool not found: {tool_name}"
            }
        })
    
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
    })

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
