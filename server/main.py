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
if dist_path.exists():
    app.mount("/assets", StaticFiles(directory=str(dist_path / "assets")), name="assets")

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
    
    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "analyze_color_accessibility",
                        "description": "Analyze color accessibility in an image according to WCAG standards. Detects text and background colors, calculates contrast ratios, and provides OKLCH color suggestions for improvements.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "image_data": {
                                    "type": "string",
                                    "description": "Base64 encoded image data"
                                },
                                "image_url": {
                                    "type": "string",
                                    "description": "URL of the image to analyze"
                                }
                            },
                            "oneOf": [
                                {"required": ["image_data"]},
                                {"required": ["image_url"]}
                            ]
                        }
                    }
                ]
            }
        })
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "analyze_color_accessibility":
            # Mock data for demonstration
            # In production, this would call the actual analysis logic
            accessibility_data = {
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
            
            # Read the widget HTML
            widget_html_path = dist_path / "index.html"
            if widget_html_path.exists():
                with open(widget_html_path, "r") as f:
                    widget_html = f.read()
                
                # Replace relative paths with absolute URLs
                widget_html = widget_html.replace('href="/', f'href="{BASE_URL}/')
                widget_html = widget_html.replace('src="/', f'src="{BASE_URL}/')
            else:
                widget_html = "<h1>Widget not built</h1>"
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"🎨 Analyzed {accessibility_data['total_pairs']} color pairs. {accessibility_data['passed_pairs']} passed, {accessibility_data['failed_pairs']} failed WCAG AA standards."
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
                    "_meta": {
                        "openai/outputTemplate": {
                            "type": "resource",
                            "resource": "ui://widget/color-accessibility.html"
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
