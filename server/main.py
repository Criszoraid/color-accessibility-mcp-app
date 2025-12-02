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

def analyze_image_colors(image_url: str, wcag_level: str = "AA"):
    """Analyze color accessibility in an image"""
    try:
        print(f"📥 Downloading image from: {image_url}")
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        print(f"✅ Image downloaded, size: {len(response.content)} bytes")
        img = Image.open(BytesIO(response.content))
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
        
        # Sample regions to find text-like areas (darker regions on lighter backgrounds)
        # This is a simplified approach - in production you'd use OCR
        color_pairs = []
        sample_regions = min(20, (width * height) // 10000)  # Sample up to 20 regions
        
        for i in range(sample_regions):
            # Sample random regions
            x = np.random.randint(0, max(1, width - 50))
            y = np.random.randint(0, max(1, height - 50))
            region_w = min(50, width - x)
            region_h = min(50, height - y)
            
            region = img_array[y:y+region_h, x:x+region_w]
            
            # Get dominant colors in region
            pixels = region.reshape(-1, 3)
            
            # Simple clustering: find two most distinct colors
            # Center pixel as foreground estimate
            center_y, center_x = region_h // 2, region_w // 2
            fg_color = tuple(pixels[center_y * region_w + center_x])
            
            # Average of edge pixels as background estimate
            edge_pixels = np.concatenate([
                region[0, :].reshape(-1, 3),  # top edge
                region[-1, :].reshape(-1, 3),  # bottom edge
                region[:, 0].reshape(-1, 3),  # left edge
                region[:, -1].reshape(-1, 3)   # right edge
            ])
            bg_color = tuple(np.mean(edge_pixels, axis=0).astype(int))
            
            # Calculate contrast
            ratio = calculate_contrast_ratio(fg_color, bg_color)
            wcag = evaluate_wcag(ratio)
            
            # Determine which is actually foreground (darker) and background (lighter)
            fg_lum = calculate_luminance(*fg_color)
            bg_lum = calculate_luminance(*bg_color)
            
            if fg_lum > bg_lum:
                # Swap if we got it backwards
                fg_color, bg_color = bg_color, fg_color
                ratio = calculate_contrast_ratio(fg_color, bg_color)
                wcag = evaluate_wcag(ratio)
            
            color_pairs.append({
                "text_sample": f"Sample {i+1}",
                "background": rgb_to_hex(*bg_color),
                "foreground": rgb_to_hex(*fg_color),
                "ratio": round(ratio, 1),
                "passes_aa_normal": wcag["passes_aa_normal"],
                "passes_aa_large": wcag["passes_aa_large"],
                "passes_aaa_normal": wcag["passes_aaa_normal"],
                "passes_aaa_large": wcag["passes_aaa_large"]
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
      document.getElementById('loading').style.display = 'none';
      document.getElementById('content').style.display = 'block';

      // Update summary
      document.getElementById('passing-count').textContent = data.passed_pairs;
      document.getElementById('failing-count').textContent = data.failed_pairs;
      document.getElementById('texts-count').textContent = data.total_pairs;

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
        log('❌ No injected data found. Waiting for event...');
    }

    // Listen for data from ChatGPT (Standard Pattern)
    window.addEventListener('openai:set_globals', (event) => {
        log('📩 Received openai:set_globals event');
        const globals = event.detail?.globals;
        if (!globals) {
            log('❌ Event has no globals');
            return;
        }
        
        // Update window.openai with the new globals
        if (!window.openai) {
            window.openai = {};
        }
        Object.assign(window.openai, globals);
        log('✅ Updated window.openai with globals');
        log('Available keys in globals: ' + JSON.stringify(Object.keys(globals)));
        
        // Try to find data in different possible locations
        let data = null;
        
        // Check globals.toolOutput directly (could be the full object)
        if (globals.toolOutput) {
            log('✅ Found globals.toolOutput');
            log('toolOutput keys: ' + JSON.stringify(Object.keys(globals.toolOutput)));
            
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
            log('❌ Could not find data in globals. Keys: ' + JSON.stringify(Object.keys(globals)));
            log('Full globals object: ' + JSON.stringify(globals, null, 2));
        }
    });

    // Also check if data is already available on window.openai
    if (window.openai) {
        log('Checking window.openai...');
        const globals = window.openai;
        log('window.openai keys: ' + JSON.stringify(Object.keys(globals)));
        
        let data = null;
        
        // Check toolOutput first
        if (globals.toolOutput) {
            log('✅ Found window.openai.toolOutput');
            log('toolOutput keys: ' + JSON.stringify(Object.keys(globals.toolOutput)));
            
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
        }
        
        // Check other locations
        if (!data && globals.data) {
            data = globals.data;
            log('✅ Found window.openai.data');
        } else if (!data && globals.accessibility) {
            data = globals.accessibility;
            log('✅ Found window.openai.accessibility');
        }
        
        if (data) {
            renderResults(data);
        } else {
            log('❌ Could not find data in window.openai');
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
            
            print(f"🎨 Received request to analyze image: {image_url[:50]}...")
            print(f"📊 WCAG Level: {wcag_level}")
            
            # Analyze the actual image
            accessibility_data = analyze_image_colors(image_url, wcag_level)
            
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
      document.getElementById('loading').style.display = 'none';
      document.getElementById('content').style.display = 'block';

      // Update summary
      document.getElementById('passing-count').textContent = data.passed_pairs;
      document.getElementById('failing-count').textContent = data.failed_pairs;
      document.getElementById('texts-count').textContent = data.total_pairs;

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
        log('❌ No injected data found. Waiting for event...');
    }

    // Listen for data from ChatGPT (Standard Pattern)
    window.addEventListener('openai:set_globals', (event) => {
        log('📩 Received openai:set_globals event');
        const globals = event.detail?.globals;
        if (!globals) {
            log('❌ Event has no globals');
            return;
        }
        
        // Update window.openai with the new globals
        if (!window.openai) {
            window.openai = {};
        }
        Object.assign(window.openai, globals);
        log('✅ Updated window.openai with globals');
        log('Available keys in globals: ' + JSON.stringify(Object.keys(globals)));
        
        // Try to find data in different possible locations
        let data = null;
        
        // Check globals.toolOutput directly (could be the full object)
        if (globals.toolOutput) {
            log('✅ Found globals.toolOutput');
            log('toolOutput keys: ' + JSON.stringify(Object.keys(globals.toolOutput)));
            
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
            log('❌ Could not find data in globals. Keys: ' + JSON.stringify(Object.keys(globals)));
            log('Full globals object: ' + JSON.stringify(globals, null, 2));
        }
    });

    // Also check if data is already available on window.openai
    if (window.openai) {
        log('Checking window.openai...');
        const globals = window.openai;
        log('window.openai keys: ' + JSON.stringify(Object.keys(globals)));
        
        let data = null;
        
        // Check toolOutput first
        if (globals.toolOutput) {
            log('✅ Found window.openai.toolOutput');
            log('toolOutput keys: ' + JSON.stringify(Object.keys(globals.toolOutput)));
            
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
        }
        
        // Check other locations
        if (!data && globals.data) {
            data = globals.data;
            log('✅ Found window.openai.data');
        } else if (!data && globals.accessibility) {
            data = globals.accessibility;
            log('✅ Found window.openai.accessibility');
        }
        
        if (data) {
            renderResults(data);
        } else {
            log('❌ Could not find data in window.openai');
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
