from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from pathlib import Path

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
  </div>

  <script>
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
      document.getElementById('loading').style.display = 'none';
      document.getElementById('content').style.display = 'block';

      // Update summary
      document.getElementById('passing-count').textContent = data.passed_pairs;
      document.getElementById('failing-count').textContent = data.failed_pairs;
      document.getElementById('texts-count').textContent = data.total_pairs;

      // Render color pairs
      const container = document.getElementById('colors-content');
      container.innerHTML = data.color_pairs.map(pair => renderColorPair(pair)).join('');
    }

    // Listen for data from ChatGPT
    window.addEventListener('openai:set_globals', (event) => {
        const globals = event.detail?.globals;
        if (!globals) return;
        
        if (globals.data) {
            renderResults(globals.data);
        } else if (globals.accessibility) {
            renderResults(globals.accessibility);
        } else if (globals.toolOutput && globals.toolOutput.accessibility) {
            renderResults(globals.toolOutput.accessibility);
        }
    });

    // Also check if data is already available on window.openai
    if (window.openai) {
        const globals = window.openai;
        if (globals.data) {
            renderResults(globals.data);
        } else if (globals.accessibility) {
            renderResults(globals.accessibility);
        } else if (globals.toolOutput && globals.toolOutput.accessibility) {
            renderResults(globals.toolOutput.accessibility);
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
            
            # Mock data for demonstration
            accessibility_data = {
                "total_pairs": 12,
                "passed_pairs": 5,
                "failed_pairs": 7,
                "color_pairs": [
                    {
                        "text_sample": "Header Text",
                        "background": "#ffffff",
                        "foreground": "#000000",
                        "ratio": 21.0,
                        "passes_aa_normal": True,
                        "passes_aa_large": True,
                        "passes_aaa_normal": True,
                        "passes_aaa_large": True
                    },
                    {
                        "text_sample": "Button Text",
                        "background": "#3b82f6",
                        "foreground": "#ffffff",
                        "ratio": 3.5,
                        "passes_aa_normal": False,
                        "passes_aa_large": True,
                        "passes_aaa_normal": False,
                        "passes_aaa_large": False
                    },
                    {
                        "text_sample": "Footer Link",
                        "background": "#1f2937",
                        "foreground": "#4b5563",
                        "ratio": 2.8,
                        "passes_aa_normal": False,
                        "passes_aa_large": False,
                        "passes_aaa_normal": False,
                        "passes_aaa_large": False
                    }
                ]
            }
            
            # We need to redefine widget_html here because it's scoped to resources/read above
            # In a real app, this would be a shared constant or template file
            widget_html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Color Accessibility Checker</title>
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
  </div>

  <script>
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
      document.getElementById('loading').style.display = 'none';
      document.getElementById('content').style.display = 'block';

      // Update summary
      document.getElementById('passing-count').textContent = data.passed_pairs;
      document.getElementById('failing-count').textContent = data.failed_pairs;
      document.getElementById('texts-count').textContent = data.total_pairs;

      // Render color pairs
      const container = document.getElementById('colors-content');
      container.innerHTML = data.color_pairs.map(pair => renderColorPair(pair)).join('');
    }

    // Check for server-injected data immediately (Tutorial Pattern)
    if (window.__ACCESSIBILITY_DATA__) {
        renderResults(window.__ACCESSIBILITY_DATA__);
    }

    // Listen for data from ChatGPT (Standard Pattern)
    window.addEventListener('openai:set_globals', (event) => {
        const globals = event.detail?.globals;
        if (!globals) return;
        
        if (globals.data) {
            renderResults(globals.data);
        } else if (globals.accessibility) {
            renderResults(globals.accessibility);
        } else if (globals.toolOutput && globals.toolOutput.accessibility) {
            renderResults(globals.toolOutput.accessibility);
        }
    });

    // Also check if data is already available on window.openai
    if (window.openai) {
        const globals = window.openai;
        if (globals.data) {
            renderResults(globals.data);
        } else if (globals.accessibility) {
            renderResults(globals.accessibility);
        } else if (globals.toolOutput && globals.toolOutput.accessibility) {
            renderResults(globals.toolOutput.accessibility);
        }
    }
  </script>
</body>
</html>
"""
            
            # INJECT DATA DIRECTLY INTO HTML (Tutorial Pattern)
            # FIX: Inject BEFORE the main script so it's available when the script runs
            json_data = json.dumps(accessibility_data)
            injection = f"<script>window.__ACCESSIBILITY_DATA__ = {json_data};</script>"
            
            # Replace the opening <script> tag with the data injection + the script tag
            # This ensures data is defined before the logic runs
            widget_html_with_data = widget_html.replace("<script>", f"{injection}\n  <script>")
            
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
