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

# Serve static files from dist directory
dist_path = Path(__file__).parent.parent / "web" / "dist"
assets_path = dist_path / "assets"

if assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
else:
    print(f"⚠️ Warning: Assets directory not found at {assets_path}. Widget may not display correctly.")

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
        if uri == "ui://widget/color-accessibility.html":
            # Return a placeholder HTML for the resource
            # The actual HTML with data will be returned in tools/call
            placeholder_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Color Accessibility Widget</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; text-align: center; }
        .placeholder { color: #6b7280; }
    </style>
</head>
<body>
    <div class="placeholder">
        <h2>🎨 Color Accessibility Checker</h2>
        <p>Upload an image to analyze color accessibility</p>
    </div>
</body>
</html>
"""
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "text/html+skybridge",
                            "text": placeholder_html
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
            # Get the image URL from arguments
            image_url = arguments.get("image_url", "")
            wcag_level = arguments.get("wcag_level", "AA")
            
            # Log for debugging
            print(f"🎨 Analyzing image: {image_url}")
            print(f"📊 WCAG Level: {wcag_level}")
            
            # Mock data for demonstration
            # TODO: In production, download the image from image_url and analyze it
            # You can use libraries like: Pillow, opencv-python, pytesseract
            accessibility_data = {
                "image_url": image_url,
                "wcag_level": wcag_level,
                "total_pairs": 3,
                "passed_pairs": 1,
                "failed_pairs": 2,
                "color_pairs": [
                    {
                        "foreground": "#000000",
                        "background": "#FFFFFF",
                        "ratio": 21.0,
                        "passes_aa_normal": True,
                        "passes_aa_large": True,
                        "passes_aaa_normal": True,
                        "passes_aaa_large": True,
                        "text_sample": "Example text"
                    },
                    {
                        "foreground": "#777777",
                        "background": "#FFFFFF",
                        "ratio": 4.47,
                        "passes_aa_normal": False,
                        "passes_aa_large": True,
                        "passes_aaa_normal": False,
                        "passes_aaa_large": False,
                        "text_sample": "Low contrast text",
                        "suggestions": {
                            "darken_bg": [
                                {"color": "#555555", "ratio": 5.2, "oklch": "oklch(0.45 0.02 264)"}
                            ],
                            "adjust_fg": [
                                {"color": "#333333", "ratio": 7.1, "oklch": "oklch(0.35 0.01 264)"}
                            ]
                        }
                    },
                    {
                        "foreground": "#FF0000",
                        "background": "#FFFF00",
                        "ratio": 2.3,
                        "passes_aa_normal": False,
                        "passes_aa_large": False,
                        "passes_aaa_normal": False,
                        "passes_aaa_large": False,
                        "text_sample": "Very low contrast",
                        "suggestions": {
                            "lighten_bg": [
                                {"color": "#FFFFCC", "ratio": 3.5, "oklch": "oklch(0.95 0.05 110)"}
                            ],
                            "darken_bg": [
                                {"color": "#CC9900", "ratio": 4.8, "oklch": "oklch(0.65 0.15 85)"}
                            ]
                        }
                    }
                ]
            }
            
            # Create self-contained widget HTML
            widget_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Color Accessibility Results</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
            padding: 16px; 
            background: transparent;
            max-height: 600px;
            overflow-y: auto;
        }}
        .container {{ 
            max-width: 100%; 
            margin: 0 auto; 
            background: white; 
            border-radius: 8px; 
            padding: 20px; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
        }}
        h1 {{ color: #1a1a1a; margin-bottom: 16px; font-size: 20px; }}
        .summary {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px; }}
        .stat-card {{ background: #f8f9fa; padding: 12px; border-radius: 6px; text-align: center; }}
        .stat-value {{ font-size: 28px; font-weight: bold; color: #2563eb; }}
        .stat-label {{ font-size: 12px; color: #6b7280; margin-top: 4px; }}
        .color-pair {{ background: #f8f9fa; padding: 14px; border-radius: 6px; margin-bottom: 12px; }}
        .pair-header {{ font-weight: 600; margin-bottom: 12px; color: #374151; }}
        .color-preview {{ display: flex; align-items: center; gap: 16px; margin-bottom: 12px; }}
        .color-swatch {{ width: 80px; height: 80px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; border: 2px solid #e5e7eb; }}
        .ratio-badge {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 14px; font-weight: 600; }}
        .ratio-badge.pass {{ background: #dcfce7; color: #166534; }}
        .ratio-badge.fail {{ background: #fee2e2; color: #991b1b; }}
        .wcag-levels {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .wcag-badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
        .wcag-badge.pass {{ background: #dcfce7; color: #166534; }}
        .wcag-badge.fail {{ background: #fee2e2; color: #991b1b; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 Color Accessibility Analysis</h1>
        
        <div class="summary">
            <div class="stat-card">
                <div class="stat-value">{accessibility_data['total_pairs']}</div>
                <div class="stat-label">Total Pairs</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #16a34a;">{accessibility_data['passed_pairs']}</div>
                <div class="stat-label">Passed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #dc2626;">{accessibility_data['failed_pairs']}</div>
                <div class="stat-label">Failed</div>
            </div>
        </div>
        
        <div class="color-pairs">
            {''.join([f'''
            <div class="color-pair">
                <div class="pair-header">{pair.get('text_sample', 'Color Pair')}</div>
                <div class="color-preview">
                    <div class="color-swatch" style="background: {pair['background']}; color: {pair['foreground']};">Aa</div>
                    <div>
                        <div><strong>Contrast Ratio:</strong> {pair['ratio']}:1</div>
                        <div class="ratio-badge {'pass' if pair['passes_aa_normal'] else 'fail'}">
                            {'✓ WCAG AA' if pair['passes_aa_normal'] else '✗ WCAG AA'}
                        </div>
                    </div>
                </div>
                <div class="wcag-levels">
                    <span class="wcag-badge {'pass' if pair['passes_aa_normal'] else 'fail'}">AA Normal: {'✓' if pair['passes_aa_normal'] else '✗'}</span>
                    <span class="wcag-badge {'pass' if pair['passes_aa_large'] else 'fail'}">AA Large: {'✓' if pair['passes_aa_large'] else '✗'}</span>
                    <span class="wcag-badge {'pass' if pair['passes_aaa_normal'] else 'fail'}">AAA Normal: {'✓' if pair['passes_aaa_normal'] else '✗'}</span>
                    <span class="wcag-badge {'pass' if pair['passes_aaa_large'] else 'fail'}">AAA Large: {'✓' if pair['passes_aaa_large'] else '✗'}</span>
                </div>
            </div>
            ''' for pair in accessibility_data['color_pairs']])}
        </div>
    </div>
</body>
</html>
"""
            
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
                                "text": widget_html
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
