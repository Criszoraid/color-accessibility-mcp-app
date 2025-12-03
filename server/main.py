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

# Serve static files from dist directory if they exist
dist_path = Path(__file__).parent.parent / "web" / "dist"
assets_path = dist_path / "assets"

if assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

# ============================================================================
# COLOR ACCESSIBILITY FUNCTIONS
# ============================================================================

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

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    # Handle 3-digit hex
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def evaluate_wcag(ratio):
    """Evaluate WCAG compliance for a contrast ratio"""
    return {
        "passes_aa_normal": ratio >= 4.5,
        "passes_aa_large": ratio >= 3.0,
        "passes_aaa_normal": ratio >= 7.0,
        "passes_aaa_large": ratio >= 4.5
    }

def generate_oklch_suggestions(bg_hex, fg_hex, target_ratio=4.5):
    """Generate OKLCH color suggestions to improve contrast"""
    suggestions = []
    
    # Normalize hex colors
    bg_hex = bg_hex.strip().upper()
    fg_hex = fg_hex.strip().upper()
    if not bg_hex.startswith('#'):
        bg_hex = '#' + bg_hex
    if not fg_hex.startswith('#'):
        fg_hex = '#' + fg_hex
    
    try:
        from coloraide import Color
        
        print(f"    📐 Converting colors to OKLCH: bg={bg_hex}, fg={fg_hex}")
        bg_color = Color(bg_hex)
        fg_color = Color(fg_hex)
        
        bg_oklch = bg_color.convert('oklch')
        fg_oklch = fg_color.convert('oklch')
        
        # Get lightness values using coords() - returns (L, C, H)
        bg_coords = bg_oklch.coords()
        fg_coords = fg_oklch.coords()
        bg_lightness = bg_coords[0]
        fg_lightness = fg_coords[0]
        
        print(f"    ✅ OKLCH conversion successful (bg L={bg_lightness:.2f}, fg L={fg_lightness:.2f})")
        
        # Option 1: Lighten background (if background is dark)
        if bg_lightness < 0.7:  # Only if background is relatively dark
            for delta in [0.15, 0.25, 0.35, 0.45, 0.55]:
                try:
                    new_bg_oklch = bg_oklch.clone()
                    new_lightness = min(0.95, bg_lightness + delta)
                    new_bg_oklch.set('lightness', new_lightness)
                    new_bg_hex = new_bg_oklch.convert('srgb').to_string(hex=True, fit=True)
                    new_bg_rgb = hex_to_rgb(new_bg_hex)
                    fg_rgb = hex_to_rgb(fg_hex)
                    
                    ratio = calculate_contrast_ratio(new_bg_rgb, fg_rgb)
                    if ratio >= target_ratio:
                        suggestion = {
                            "type": "lighten_bg",
                            "background_oklch": new_bg_oklch.to_string(),
                            "foreground_oklch": fg_oklch.to_string(),
                            "new_contrast_ratio": round(ratio, 1),
                            "preview_hex_bg": new_bg_hex,
                            "preview_hex_fg": fg_hex
                        }
                        suggestions.append(suggestion)
                        print(f"    ✅ Found lighten_bg suggestion: {new_bg_hex} → {ratio:.2f}:1")
                        break
                except Exception as e:
                    print(f"    ⚠️ Error in lighten_bg delta {delta}: {e}")
                    continue
        
        # Option 2: Darken background (if background is light)
        if bg_lightness > 0.3:  # Only if background is relatively light
            for delta in [-0.15, -0.25, -0.35, -0.45, -0.55]:
                try:
                    new_bg_oklch = bg_oklch.clone()
                    new_lightness = max(0.05, bg_lightness + delta)
                    new_bg_oklch.set('lightness', new_lightness)
                    new_bg_hex = new_bg_oklch.convert('srgb').to_string(hex=True, fit=True)
                    new_bg_rgb = hex_to_rgb(new_bg_hex)
                    fg_rgb = hex_to_rgb(fg_hex)
                    
                    ratio = calculate_contrast_ratio(new_bg_rgb, fg_rgb)
                    if ratio >= target_ratio:
                        suggestion = {
                            "type": "darken_bg",
                            "background_oklch": new_bg_oklch.to_string(),
                            "foreground_oklch": fg_oklch.to_string(),
                            "new_contrast_ratio": round(ratio, 1),
                            "preview_hex_bg": new_bg_hex,
                            "preview_hex_fg": fg_hex
                        }
                        suggestions.append(suggestion)
                        print(f"    ✅ Found darken_bg suggestion: {new_bg_hex} → {ratio:.2f}:1")
                        break
                except Exception as e:
                    print(f"    ⚠️ Error in darken_bg delta {delta}: {e}")
                    continue
        
        # Option 3: Adjust foreground (make it more contrasting)
        # If foreground is light, make it darker; if dark, make it lighter
        fg_delta = -0.4 if fg_lightness > 0.5 else 0.4
        try:
            new_fg_oklch = fg_oklch.clone()
            new_lightness = max(0.05, min(0.95, fg_lightness + fg_delta))
            new_fg_oklch.set('lightness', new_lightness)
            new_fg_hex = new_fg_oklch.convert('srgb').to_string(hex=True, fit=True)
            new_fg_rgb = hex_to_rgb(new_fg_hex)
            bg_rgb = hex_to_rgb(bg_hex)
            
            ratio = calculate_contrast_ratio(bg_rgb, new_fg_rgb)
            if ratio >= target_ratio:
                suggestion = {
                    "type": "adjust_fg",
                    "background_oklch": bg_oklch.to_string(),
                    "foreground_oklch": new_fg_oklch.to_string(),
                    "new_contrast_ratio": round(ratio, 1),
                    "preview_hex_bg": bg_hex,
                    "preview_hex_fg": new_fg_hex
                }
                suggestions.append(suggestion)
                print(f"    ✅ Found adjust_fg suggestion: {new_fg_hex} → {ratio:.2f}:1")
        except Exception as e:
            print(f"    ⚠️ Error in adjust_fg: {e}")
    
    except ImportError as e:
        print(f"❌ ERROR: coloraide not installed or import failed: {e}")
        print(f"   Install with: pip install coloraide")
    except Exception as e:
        print(f"⚠️ Error generating OKLCH suggestions: {e}")
        import traceback
        traceback.print_exc()
    
    if len(suggestions) == 0:
        print(f"    ⚠️ No suggestions found - may need more aggressive adjustments")
    
    return suggestions

# ============================================================================
# WIDGET HTML TEMPLATE (similar to gastos example)
# ============================================================================

WIDGET_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Color Accessibility Checker</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f7; padding: 20px; }
    .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 16px; padding: 24px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07); }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #e5e5e5; }
    .header h1 { font-size: 20px; font-weight: 600; color: #1d1d1f; }
    .summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px; }
    .summary-card { background: #f8f8f8; border-radius: 12px; padding: 16px; text-align: center; }
    .summary-card.pass { background: #d1f4e0; }
    .summary-card.fail { background: #ffe5e5; }
    .summary-value { font-size: 28px; font-weight: 700; color: #1d1d1f; }
    .summary-label { font-size: 12px; color: #86868b; margin-top: 4px; }
    .color-pair { border: 1px solid #e5e5e5; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
    .color-pair.fail { border-color: #FF3B30; background: #fff5f5; }
    .pair-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .pair-context { font-size: 14px; font-weight: 500; color: #1d1d1f; }
    .pair-ratio { font-size: 14px; font-weight: 600; }
    .pair-ratio.pass { color: #34C759; }
    .pair-ratio.fail { color: #FF3B30; }
    .preview { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
    .preview-box { width: 60px; height: 60px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 600; border: 1px solid rgba(0,0,0,0.1); }
    .color-info { display: flex; gap: 16px; }
    .color-hex { font-family: monospace; font-size: 12px; background: #f0f0f0; padding: 4px 8px; border-radius: 4px; }
    .wcag-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
    .wcag-badge { font-size: 10px; padding: 3px 6px; border-radius: 4px; font-weight: 600; }
    .wcag-badge.pass { background: #d1f4e0; color: #0f6537; }
    .wcag-badge.fail { background: #ffe5e5; color: #c41e3a; }
    .suggestions { margin-top: 12px; padding-top: 12px; border-top: 1px dashed #e5e5e5; }
    .suggestions-title { font-size: 12px; font-weight: 600; color: #86868b; margin-bottom: 8px; }
    .suggestion { display: inline-flex; align-items: center; gap: 6px; background: #f0fff0; border: 1px solid #34C759; border-radius: 6px; padding: 6px 10px; margin-right: 8px; margin-bottom: 8px; }
    .suggestion-preview { width: 24px; height: 24px; border-radius: 4px; font-size: 10px; display: flex; align-items: center; justify-content: center; }
    .suggestion-info { font-size: 11px; }
    .empty { text-align: center; padding: 40px; color: #86868b; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🎨 Color Accessibility Check</h1>
    </div>
    
    <div class="summary">
      <div class="summary-card">
        <div class="summary-value" id="total">0</div>
        <div class="summary-label">Total Pairs</div>
      </div>
      <div class="summary-card pass">
        <div class="summary-value" id="passed">0</div>
        <div class="summary-label">✅ Passed</div>
      </div>
      <div class="summary-card fail">
        <div class="summary-value" id="failed">0</div>
        <div class="summary-label">❌ Failed</div>
      </div>
    </div>
    
    <div id="results"></div>
  </div>

  <script>
    function render(data) {
      if (!data || !data.color_pairs) {
        document.getElementById('results').innerHTML = '<div class="empty">No color pairs to analyze</div>';
        return;
      }
      
      document.getElementById('total').textContent = data.total_pairs || 0;
      document.getElementById('passed').textContent = data.passed_pairs || 0;
      document.getElementById('failed').textContent = data.failed_pairs || 0;
      
      const html = data.color_pairs.map(pair => {
        const isPass = pair.passes_aa_normal;
        const suggestionsHtml = pair.suggestions && pair.suggestions.length > 0 ? `
          <div class="suggestions">
            <div class="suggestions-title">💡 OKLCH Suggestions:</div>
            ${pair.suggestions.map(s => `
              <div class="suggestion">
                <div class="suggestion-preview" style="background:${s.preview_hex_bg};color:${s.preview_hex_fg}">Aa</div>
                <div class="suggestion-info">${s.type.replace('_', ' ')} → ${s.new_contrast_ratio}:1</div>
              </div>
            `).join('')}
          </div>
        ` : '';
        
        return `
          <div class="color-pair ${isPass ? '' : 'fail'}">
            <div class="pair-header">
              <span class="pair-context">${pair.text_sample || 'Color Pair'}</span>
              <span class="pair-ratio ${isPass ? 'pass' : 'fail'}">${pair.ratio}:1 ${isPass ? '✅' : '❌'}</span>
            </div>
            <div class="preview">
              <div class="preview-box" style="background:${pair.background};color:${pair.foreground}">Aa</div>
              <div class="color-info">
                <div><small>Text:</small> <span class="color-hex">${pair.foreground}</span></div>
                <div><small>Background:</small> <span class="color-hex">${pair.background}</span></div>
              </div>
            </div>
            <div class="wcag-badges">
              <span class="wcag-badge ${pair.passes_aa_normal ? 'pass' : 'fail'}">AA Normal ${pair.passes_aa_normal ? '✓' : '✗'}</span>
              <span class="wcag-badge ${pair.passes_aa_large ? 'pass' : 'fail'}">AA Large ${pair.passes_aa_large ? '✓' : '✗'}</span>
              <span class="wcag-badge ${pair.passes_aaa_normal ? 'pass' : 'fail'}">AAA Normal ${pair.passes_aaa_normal ? '✓' : '✗'}</span>
              <span class="wcag-badge ${pair.passes_aaa_large ? 'pass' : 'fail'}">AAA Large ${pair.passes_aaa_large ? '✓' : '✗'}</span>
            </div>
            ${suggestionsHtml}
          </div>
        `;
      }).join('');
      
      document.getElementById('results').innerHTML = html;
    }
    
    // Listen for data from ChatGPT (same pattern as gastos example)
    window.addEventListener('openai:set_globals', (event) => {
      const globals = event.detail?.globals;
      if (globals?.toolOutput?.data) {
        render(globals.toolOutput.data);
      }
    });
    
    // Check if data already available
    if (window.openai?.toolOutput?.data) {
      render(window.openai.toolOutput.data);
    }
  </script>
</body>
</html>
"""

# ============================================================================
# ROUTES
# ============================================================================

@app.get("/")
async def root():
    return {"message": "Color Accessibility Checker MCP Server", "status": "running"}

@app.get("/widget")
async def widget():
    """Serve the widget HTML with static demo data for preview"""
    # Complete HTML with embedded demo data - no external file dependencies
    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Color Accessibility Checker - Demo</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f7; padding: 20px; }
    .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 16px; padding: 32px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07); }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
    .header h1 { font-size: 24px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
    .summary-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 32px; }
    .summary-card { background: #f8f8f8; border-radius: 12px; padding: 24px; text-align: center; }
    .summary-icon { font-size: 32px; margin-bottom: 8px; }
    .summary-value { font-size: 32px; font-weight: 700; margin-bottom: 4px; }
    .summary-label { font-size: 14px; color: #86868b; text-transform: capitalize; }
    .tabs { display: flex; gap: 8px; margin-bottom: 24px; }
    .tab { flex: 1; padding: 12px 24px; border: none; border-radius: 8px; font-size: 16px; font-weight: 500; cursor: pointer; transition: all 0.2s; }
    .tab.active { background: #007AFF; color: white; }
    .tab:not(.active) { background: #f0f0f0; color: #1d1d1f; }
    .color-pairs-list { display: flex; flex-direction: column; gap: 24px; }
    .color-pair-card { border: 1px solid #e5e5e5; border-radius: 12px; padding: 20px; }
    .pair-header { font-size: 14px; color: #86868b; margin-bottom: 12px; font-weight: 500; }
    .color-preview-section { display: flex; gap: 16px; align-items: center; margin-bottom: 16px; }
    .color-preview { flex: 1; height: 80px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: 600; border: 1px solid rgba(0,0,0,0.1); }
    .ratio-info { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
    .ratio-badge { background: #34C759; color: white; padding: 6px 12px; border-radius: 6px; font-weight: 600; font-size: 14px; }
    .ratio-badge.fail { background: #FF3B30; }
    .ratio-value { font-size: 20px; font-weight: 600; color: #1d1d1f; }
    .color-codes { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
    .color-code { font-family: 'Monaco', 'Courier New', monospace; font-size: 13px; padding: 8px 12px; background: #f5f5f5; border-radius: 6px; }
    .color-code-label { font-size: 11px; color: #86868b; margin-bottom: 4px; text-transform: uppercase; font-weight: 600; }
    .suggestions-section { border-top: 1px solid #e5e5e5; padding-top: 20px; margin-top: 16px; }
    .suggestions-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
    .suggestions-header h4 { font-size: 14px; font-weight: 600; color: #1d1d1f; }
    .fail-badge { background: #FF3B30; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }
    .suggestions-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
    .suggestion-card { border: 2px solid #34C759; border-radius: 10px; padding: 16px; background: #f9fff9; }
    .suggestion-preview { height: 60px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 600; margin-bottom: 12px; border: 1px solid rgba(0,0,0,0.1); }
    .suggestion-badge { background: #34C759; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; margin-bottom: 8px; }
    .suggestion-type { font-size: 11px; color: #86868b; text-transform: uppercase; margin-bottom: 6px; font-weight: 600; }
    .suggestion-color { font-family: 'Monaco', 'Courier New', monospace; font-size: 11px; background: white; padding: 6px 8px; border-radius: 4px; margin-bottom: 4px; color: #1d1d1f; }
    .suggestion-ratio { font-size: 13px; font-weight: 600; color: #34C759; margin-top: 6px; }
    .wcag-levels { display: flex; gap: 8px; margin-top: 8px; }
    .wcag-badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
    .wcag-badge.pass { background: #d1f4e0; color: #0f6537; }
    .wcag-badge.fail { background: #ffe5e5; color: #c41e3a; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🎨 Color Accessibility Checker</h1>
    </div>
    <div class="summary-cards">
      <div class="summary-card">
        <div class="summary-icon">✅</div>
        <div class="summary-value" id="passing-count">2</div>
        <div class="summary-label">Passing</div>
      </div>
      <div class="summary-card">
        <div class="summary-icon">❌</div>
        <div class="summary-value" id="failing-count">2</div>
        <div class="summary-label">Failures</div>
      </div>
      <div class="summary-card">
        <div class="summary-icon">👁️</div>
        <div class="summary-value" id="texts-count">4</div>
        <div class="summary-label">Texts</div>
      </div>
    </div>
    <div class="tabs">
      <button class="tab active" onclick="showTab('colors', event)">Colors</button>
      <button class="tab" onclick="showTab('vision', event)">Vision</button>
    </div>
    <div id="colors-content" class="color-pairs-list"></div>
    <div id="vision-content" style="display: none;">
      <div style="text-align: center; padding: 60px 20px; color: #86868b;">
        <div style="font-size: 48px; margin-bottom: 16px;">👁️</div>
        <p>Vision simulation coming soon...</p>
      </div>
    </div>
  </div>
  <script>
    const sampleData = {
      summary: { total_pairs: 4, passing_pairs: 2, failing_pairs: 2, detected_texts: 4 },
      color_pairs: [
        {
          id: "pair-0", text: "Título Principal", background: "#FFFFFF", foreground: "#333333",
          contrast_ratio: 12.63, wcag_aa: { normal_text: true, large_text: true },
          wcag_aaa: { normal_text: true, large_text: true }, status: "pass", suggestions: []
        },
        {
          id: "pair-1", text: "Botón de Acción", background: "#0066CC", foreground: "#FFFFFF",
          contrast_ratio: 7.12, wcag_aa: { normal_text: true, large_text: true },
          wcag_aaa: { normal_text: true, large_text: true }, status: "pass", suggestions: []
        },
        {
          id: "pair-2", text: "Texto Secundario", background: "#F5F5F5", foreground: "#999999",
          contrast_ratio: 2.85, wcag_aa: { normal_text: false, large_text: false },
          wcag_aaa: { normal_text: false, large_text: false }, status: "fail",
          suggestions: [
            {
              type: "darken_bg", background_oklch: "oklch(0.75 0.01 264)", foreground_oklch: "oklch(0.45 0.01 264)",
              new_contrast_ratio: 4.6, preview_hex_bg: "#D0D0D0", preview_hex_fg: "#999999"
            },
            {
              type: "adjust_fg", background_oklch: "oklch(0.93 0.01 264)", foreground_oklch: "oklch(0.35 0.01 264)",
              new_contrast_ratio: 7.8, preview_hex_bg: "#F5F5F5", preview_hex_fg: "#4A4A4A"
            }
          ]
        },
        {
          id: "pair-3", text: "Enlace de Navegación", background: "#E8E8E8", foreground: "#0066CC",
          contrast_ratio: 3.2, wcag_aa: { normal_text: false, large_text: true },
          wcag_aaa: { normal_text: false, large_text: false }, status: "fail",
          suggestions: [
            {
              type: "darken_bg", background_oklch: "oklch(0.65 0.01 264)", foreground_oklch: "oklch(0.45 0.15 264)",
              new_contrast_ratio: 5.2, preview_hex_bg: "#B0B0B0", preview_hex_fg: "#0066CC"
            }
          ]
        }
      ]
    };
    function showTab(tabName, event) {
      document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
      if (event && event.target) {
        event.target.classList.add('active');
      } else {
        document.querySelectorAll('.tab').forEach(tab => {
          if ((tabName === 'colors' && tab.textContent.includes('Colors')) || 
              (tabName === 'vision' && tab.textContent.includes('Vision'))) {
            tab.classList.add('active');
          }
        });
      }
      document.getElementById('colors-content').style.display = tabName === 'colors' ? 'flex' : 'none';
      document.getElementById('vision-content').style.display = tabName === 'vision' ? 'block' : 'none';
    }
    function getWCAGBadge(level, passes) {
      return `<span class="wcag-badge ${passes ? 'pass' : 'fail'}">${level}: ${passes ? '✓' : '✗'}</span>`;
    }
    function renderColorPair(pair) {
      const suggestionTypeLabels = { lighten_bg: 'Lighten Background', darken_bg: 'Darken Background', adjust_fg: 'Adjust Foreground' };
      const suggestionsHTML = pair.suggestions.length > 0 ? `
        <div class="suggestions-section">
          <div class="suggestions-header">
            <span class="fail-badge">Fail</span>
            <h4>OKLCH Suggestions</h4>
          </div>
          <div class="suggestions-grid">
            ${pair.suggestions.map(sugg => `
              <div class="suggestion-card">
                <div class="suggestion-preview" style="background: ${sugg.preview_hex_bg}; color: ${sugg.preview_hex_fg};">Aa</div>
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
      return `
        <div class="color-pair-card">
          <div class="pair-header">Original "${pair.text}"</div>
          <div class="color-preview-section">
            <div class="color-preview" style="background: ${pair.background}; color: ${pair.foreground};">Aa</div>
            <div class="ratio-info">
              <div class="ratio-badge ${pair.status === 'pass' ? '' : 'fail'}">${pair.status === 'pass' ? 'AAA' : 'Fail'}</div>
              <div class="ratio-value">Ratio: ${pair.contrast_ratio}:1</div>
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
            ${getWCAGBadge('AA Normal', pair.wcag_aa.normal_text)}
            ${getWCAGBadge('AA Large', pair.wcag_aa.large_text)}
            ${getWCAGBadge('AAA Normal', pair.wcag_aaa.normal_text)}
            ${getWCAGBadge('AAA Large', pair.wcag_aaa.large_text)}
          </div>
          ${suggestionsHTML}
        </div>
      `;
    }
    function renderResults(data) {
      document.getElementById('passing-count').textContent = data.summary.passing_pairs;
      document.getElementById('failing-count').textContent = data.summary.failing_pairs;
      document.getElementById('texts-count').textContent = data.summary.detected_texts;
      document.getElementById('colors-content').innerHTML = data.color_pairs.map(pair => renderColorPair(pair)).join('');
    }
    renderResults(sampleData);
  </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

# ============================================================================
# MCP ENDPOINT (following gastos example pattern EXACTLY)
# ============================================================================

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
                        "description": "Widget for displaying color accessibility analysis results",
                        "mimeType": "text/html+skybridge"
                    }
                ]
            }
        })
    
    elif method == "resources/read":
        uri = params.get("uri")
        if uri == "ui://widget/color-accessibility.html":
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "text/html+skybridge",
                            "text": WIDGET_HTML
                        }
                    ]
                }
            })
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32602, "message": f"Resource not found: {uri}"}
        })
    
    # ========================================================================
    # TOOLS LIST - Following gastos example pattern
    # ========================================================================
    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "check_color_accessibility",
                        "description": "Analizar la accesibilidad de colores según WCAG. Cuando el usuario suba una imagen (captura de pantalla, diseño, web), mira la imagen y extrae todos los pares de colores de texto/fondo que veas. Luego llama a esta herramienta con los colores en formato hexadecimal.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "color_pairs": {
                                    "type": "array",
                                    "description": "Array de pares de colores extraídos de la imagen",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "foreground": {
                                                "type": "string",
                                                "description": "Color del texto en hexadecimal (#RRGGBB)"
                                            },
                                            "background": {
                                                "type": "string",
                                                "description": "Color del fondo en hexadecimal (#RRGGBB)"
                                            },
                                            "element": {
                                                "type": "string",
                                                "description": "Descripción del elemento (ej: 'título principal', 'botón', 'enlace de navegación')"
                                            }
                                        },
                                        "required": ["foreground", "background"]
                                    }
                                }
                            },
                            "required": ["color_pairs"]
                        },
                        "_meta": {
                            "openai/outputTemplate": "ui://widget/color-accessibility.html",
                            "openai/widgetAccessible": True,
                            "openai/toolInvocation/invoking": "Analizando accesibilidad de colores...",
                            "openai/toolInvocation/invoked": "Análisis completado."
                        }
                    }
                ]
            }
        })
    
    # ========================================================================
    # TOOLS CALL - Following gastos example pattern EXACTLY
    # ========================================================================
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "check_color_accessibility":
            color_pairs_input = arguments.get("color_pairs", [])
            
            print(f"🎨 Received {len(color_pairs_input)} color pairs from ChatGPT")
            
            # Process each color pair
            analyzed_pairs = []
            
            for pair in color_pairs_input:
                fg_hex = pair.get("foreground", "").strip()
                bg_hex = pair.get("background", "").strip()
                element = pair.get("element", "Elemento")
                
                # Normalize hex colors
                if not fg_hex.startswith("#"):
                    fg_hex = f"#{fg_hex}"
                if not bg_hex.startswith("#"):
                    bg_hex = f"#{bg_hex}"
                
                try:
                    fg_rgb = hex_to_rgb(fg_hex)
                    bg_rgb = hex_to_rgb(bg_hex)
                    
                    ratio = calculate_contrast_ratio(fg_rgb, bg_rgb)
                    wcag = evaluate_wcag(ratio)
                    
                    # Generate suggestions if fails
                    suggestions = []
                    if not wcag["passes_aa_normal"]:
                        print(f"  🔍 Generating OKLCH suggestions for failing pair: {fg_hex} on {bg_hex}")
                        suggestions = generate_oklch_suggestions(bg_hex, fg_hex, 4.5)
                        print(f"  💡 Generated {len(suggestions)} suggestions")
                        if len(suggestions) == 0:
                            print(f"  ⚠️ No suggestions generated - coloraide may not be working correctly")
                    
                    analyzed_pairs.append({
                        "text_sample": element,
                        "foreground": fg_hex.upper(),
                        "background": bg_hex.upper(),
                        "ratio": round(ratio, 2),
                        "passes_aa_normal": wcag["passes_aa_normal"],
                        "passes_aa_large": wcag["passes_aa_large"],
                        "passes_aaa_normal": wcag["passes_aaa_normal"],
                        "passes_aaa_large": wcag["passes_aaa_large"],
                        "suggestions": suggestions
                    })
                    
                    status = "✅" if wcag["passes_aa_normal"] else "❌"
                    print(f"  {status} {element}: {fg_hex} on {bg_hex} = {ratio:.2f}:1")
                    
                except Exception as e:
                    print(f"  ⚠️ Error: {e}")
            
            # Calculate summary
            passed = sum(1 for p in analyzed_pairs if p.get("passes_aa_normal", False))
            failed = len(analyzed_pairs) - passed
            
            result_data = {
                "total_pairs": len(analyzed_pairs),
                "passed_pairs": passed,
                "failed_pairs": failed,
                "color_pairs": analyzed_pairs
            }
            
            print(f"📊 Results: {passed} passed, {failed} failed")
            
            # Return in EXACT same format as gastos example
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Análisis completado: {len(analyzed_pairs)} pares de colores. {passed} pasan WCAG AA, {failed} fallan."
                        }
                    ],
                    "structuredContent": {
                        "data": result_data,
                        "_meta": {
                            "openai/outputTemplate": {
                                "type": "resource",
                                "resource": "ui://widget/color-accessibility.html"
                            }
                        }
                    },
                    "toolOutput": {
                        "data": result_data
                    }
                }
            })
        
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
        })
    
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    })

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
