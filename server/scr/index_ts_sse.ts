import { createServer, IncomingMessage, ServerResponse } from "node:http";
import { URL } from "node:url";
import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { readFileSync } from "node:fs";
import Tesseract from 'tesseract.js';
import sharp from 'sharp';
import { converter, formatHex, formatCss } from 'culori';

// Conversores de color
const oklch = converter('oklch');

// Cargar recursos web (HTML, CSS, JS)
const WEB_HTML = readFileSync("./web/index.html", "utf-8");
const WEB_CSS = readFileSync("./web/app.css", "utf-8");

// Plantilla HTML para el widget de accesibilidad
const HTML_TEMPLATE = `
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Color Accessibility Checker</title>
  <style>${WEB_CSS}</style>
</head>
<body>
  <div id="root"></div>
  <script>
    // Recibir datos del servidor MCP
    window.addEventListener('message', (event) => {
      if (event.data && event.data.type === 'accessibility-results') {
        renderResults(event.data.payload);
      }
    });

    function renderResults(data) {
      // Actualizar resumen
      document.getElementById('passing-count').textContent = data.summary.passing_pairs;
      document.getElementById('failing-count').textContent = data.summary.failing_pairs;
      document.getElementById('texts-count').textContent = data.summary.detected_texts;

      // Renderizar pares de colores
      const container = document.getElementById('colors-content');
      container.innerHTML = data.color_pairs.map(pair => renderColorPair(pair)).join('');
    }

    function renderColorPair(pair) {
      const suggestionTypeLabels = {
        lighten_bg: 'Aclarar Fondo',
        darken_bg: 'Oscurecer Fondo',
        adjust_fg: 'Ajustar Texto'
      };

      const suggestionsHTML = pair.suggestions.length > 0 ? \`
        <div class="suggestions-section">
          <div class="suggestions-header">
            <span class="fail-badge">Fail</span>
            <h4>Sugerencias OKLCH</h4>
          </div>
          <div class="suggestions-grid">
            \${pair.suggestions.map(sugg => \`
              <div class="suggestion-card">
                <div class="suggestion-preview" style="background: \${sugg.preview_hex_bg}; color: \${sugg.preview_hex_fg};">
                  Aa
                </div>
                <div class="suggestion-badge">✅ Corregido</div>
                <div class="suggestion-type">\${suggestionTypeLabels[sugg.type] || sugg.type}</div>
                <div class="suggestion-color">\${sugg.background_oklch}</div>
                <div class="suggestion-color">\${sugg.foreground_oklch}</div>
                <div class="suggestion-ratio">Ratio: \${sugg.new_contrast_ratio}:1</div>
              </div>
            \`).join('')}
          </div>
        </div>
      \` : '';

      const getWCAGBadge = (level, passes) => \`<span class="wcag-badge \${passes ? 'pass' : 'fail'}">\${level}: \${passes ? '✓' : '✗'}</span>\`;

      return \`
        <div class="color-pair-card">
          <div class="pair-header">Original \${pair.text ? \`"\${pair.text}"\` : ''}</div>
          
          <div class="color-preview-section">
            <div class="color-preview" style="background: \${pair.background}; color: \${pair.foreground};">
              Aa
            </div>
            
            <div class="ratio-info">
              <div class="ratio-badge \${pair.status === 'pass' ? '' : 'fail'}">
                \${pair.status === 'pass' ? 'AAA' : 'Fail'}
              </div>
              <div class="ratio-value">Ratio: \${pair.contrast_ratio}:1</div>
            </div>
          </div>

          <div class="color-codes">
            <div>
              <div class="color-code-label">Background</div>
              <div class="color-code">\${pair.background}</div>
            </div>
            <div>
              <div class="color-code-label">Foreground</div>
              <div class="color-code">\${pair.foreground}</div>
            </div>
          </div>

          <div class="wcag-levels">
            \${getWCAGBadge('AA Normal', pair.wcag_aa.normal_text)}
            \${getWCAGBadge('AA Large', pair.wcag_aa.large_text)}
            \${getWCAGBadge('AAA Normal', pair.wcag_aaa.normal_text)}
            \${getWCAGBadge('AAA Large', pair.wcag_aaa.large_text)}
          </div>

          \${suggestionsHTML}
        </div>
      \`;
    }
  </script>
  ${WEB_HTML.replace('<!DOCTYPE html>', '').replace(/<html.*?>/, '').replace('</html>', '').replace(/<head>.*?<\/head>/s, '').replace(/<body.*?>/, '').replace('</body>', '')}
</body>
</html>
`;

// ==========================================
// FUNCIONES DE ANÁLISIS DE ACCESIBILIDAD
// ==========================================

function getRelativeLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map(val => {
    const v = val / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function calculateContrastRatio(color1: { r: number; g: number; b: number }, color2: { r: number; g: number; b: number }): number {
  const lum1 = getRelativeLuminance(color1.r, color1.g, color1.b);
  const lum2 = getRelativeLuminance(color2.r, color2.g, color2.b);
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

function evaluateWCAG(ratio: number) {
  return {
    aa: {
      normal_text: ratio >= 4.5,
      large_text: ratio >= 3.0
    },
    aaa: {
      normal_text: ratio >= 7.0,
      large_text: ratio >= 4.5
    }
  };
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

function adjustLuminance(oklchColor: any, delta: number) {
  return {
    ...oklchColor,
    l: Math.max(0, Math.min(1, oklchColor.l + delta))
  };
}

function generateColorSuggestions(bgHex: string, fgHex: string, targetRatio = 4.5) {
  const suggestions = [];
  
  const bgOKLCH = oklch(bgHex);
  const fgOKLCH = oklch(fgHex);
  
  if (!bgOKLCH || !fgOKLCH) return suggestions;
  
  // Opción 1: Aclarar background
  for (let i = 0.1; i <= 0.5; i += 0.1) {
    const newBg = adjustLuminance(bgOKLCH, i);
    const newBgHex = formatHex(newBg);
    const bgRgb = hexToRgb(newBgHex);
    const fgRgb = hexToRgb(fgHex);
    
    if (bgRgb && fgRgb) {
      const ratio = calculateContrastRatio(bgRgb, fgRgb);
      if (ratio >= targetRatio) {
        suggestions.push({
          type: 'lighten_bg',
          background_oklch: formatCss(newBg),
          foreground_oklch: formatCss(fgOKLCH),
          new_contrast_ratio: Math.round(ratio * 10) / 10,
          preview_hex_bg: newBgHex,
          preview_hex_fg: fgHex
        });
        break;
      }
    }
  }
  
  // Opción 2: Oscurecer background
  for (let i = -0.1; i >= -0.5; i -= 0.1) {
    const newBg = adjustLuminance(bgOKLCH, i);
    const newBgHex = formatHex(newBg);
    const bgRgb = hexToRgb(newBgHex);
    const fgRgb = hexToRgb(fgHex);
    
    if (bgRgb && fgRgb) {
      const ratio = calculateContrastRatio(bgRgb, fgRgb);
      if (ratio >= targetRatio) {
        suggestions.push({
          type: 'darken_bg',
          background_oklch: formatCss(newBg),
          foreground_oklch: formatCss(fgOKLCH),
          new_contrast_ratio: Math.round(ratio * 10) / 10,
          preview_hex_bg: newBgHex,
          preview_hex_fg: fgHex
        });
        break;
      }
    }
  }
  
  // Opción 3: Ajustar foreground
  const fgDelta = fgOKLCH.l > 0.5 ? -0.3 : 0.3;
  const newFg = adjustLuminance(fgOKLCH, fgDelta);
  const newFgHex = formatHex(newFg);
  const bgRgb = hexToRgb(bgHex);
  const fgRgb = hexToRgb(newFgHex);
  
  if (bgRgb && fgRgb) {
    const ratio = calculateContrastRatio(bgRgb, fgRgb);
    if (ratio >= targetRatio) {
      suggestions.push({
        type: 'adjust_fg',
        background_oklch: formatCss(bgOKLCH),
        foreground_oklch: formatCss(newFg),
        new_contrast_ratio: Math.round(ratio * 10) / 10,
        preview_hex_bg: bgHex,
        preview_hex_fg: newFgHex
      });
    }
  }
  
  return suggestions;
}

async function extractDominantColor(imageBuffer: Buffer, x: number, y: number, width: number, height: number) {
  try {
    const region = await sharp(imageBuffer)
      .extract({ left: x, top: y, width, height })
      .resize(1, 1)
      .raw()
      .toBuffer();
    
    return {
      r: region[0],
      g: region[1],
      b: region[2]
    };
  } catch (error) {
    return null;
  }
}

async function analyzeImageAccessibility(imageData: string, wcagLevel = 'both') {
  try {
    let imageBuffer: Buffer;
    
    // Si es un objeto con data
    if (typeof imageData === 'object' && (imageData as any).data) {
      imageBuffer = Buffer.from((imageData as any).data, 'base64');
    }
    // Si es data URL
    else if (imageData.startsWith('data:')) {
      const base64Data = imageData.split(',')[1];
      imageBuffer = Buffer.from(base64Data, 'base64');
    }
    // Si es URL http
    else if (imageData.startsWith('http')) {
      const response = await fetch(imageData);
      imageBuffer = Buffer.from(await response.arrayBuffer());
    }
    // Base64 directo
    else {
      imageBuffer = Buffer.from(imageData, 'base64');
    }
    
    // Convertir a PNG
    imageBuffer = await sharp(imageBuffer).png().toBuffer();
    
    const metadata = await sharp(imageBuffer).metadata();
    
    const { data: { words } } = await Tesseract.recognize(imageBuffer, 'eng+spa', {
      logger: m => console.log(m)
    });
    
    const colorPairs = [];
    
    for (let i = 0; i < words.length && i < 50; i++) {
      const word = words[i];
      if (!word.bbox || word.confidence < 60) continue;
      
      const { x0, y0, x1, y1 } = word.bbox;
      const width = x1 - x0;
      const height = y1 - y0;
      
      const fgColor = await extractDominantColor(
        imageBuffer,
        Math.max(0, Math.floor(x0 + width / 2) - 2),
        Math.max(0, Math.floor(y0 + height / 2) - 2),
        Math.min(4, width),
        Math.min(4, height)
      );
      
      const bgColor = await extractDominantColor(
        imageBuffer,
        Math.max(0, x0 - 10),
        Math.max(0, y0 - 10),
        Math.min(width + 20, metadata.width! - x0),
        Math.min(height + 20, metadata.height! - y0)
      );
      
      if (!fgColor || !bgColor) continue;
      
      const fgHex = `#${fgColor.r.toString(16).padStart(2, '0')}${fgColor.g.toString(16).padStart(2, '0')}${fgColor.b.toString(16).padStart(2, '0')}`;
      const bgHex = `#${bgColor.r.toString(16).padStart(2, '0')}${bgColor.g.toString(16).padStart(2, '0')}${bgColor.b.toString(16).padStart(2, '0')}`;
      
      const ratio = calculateContrastRatio(bgColor, fgColor);
      const wcagEval = evaluateWCAG(ratio);
      
      const passes = wcagLevel === 'AA' 
        ? wcagEval.aa.normal_text 
        : wcagLevel === 'AAA'
        ? wcagEval.aaa.normal_text
        : wcagEval.aa.normal_text;
      
      const suggestions = !passes 
        ? generateColorSuggestions(bgHex, fgHex, wcagLevel === 'AAA' ? 7.0 : 4.5)
        : [];
      
      colorPairs.push({
        id: `pair-${i}`,
        text: word.text,
        background: bgHex,
        foreground: fgHex,
        contrast_ratio: Math.round(ratio * 10) / 10,
        wcag_aa: wcagEval.aa,
        wcag_aaa: wcagEval.aaa,
        status: passes ? 'pass' : 'fail',
        suggestions
      });
    }
    
    const passingPairs = colorPairs.filter(p => p.status === 'pass').length;
    const failingPairs = colorPairs.filter(p => p.status === 'fail').length;
    
    return {
      summary: {
        total_pairs: colorPairs.length,
        passing_pairs: passingPairs,
        failing_pairs: failingPairs,
        detected_texts: words.length
      },
      color_pairs: colorPairs
    };
    
  } catch (error: any) {
    throw new Error(`Error analyzing image: ${error.message}`);
  }
}

// ==========================================
// SERVIDOR MCP
// ==========================================

function createAccessibilityServer() {
  const server = new McpServer(
    {
      name: "color-accessibility",
      version: "1.0.0",
    },
    { capabilities: { resources: {}, tools: {} } }
  );

  // Registrar recurso HTML para el widget
  server.registerResource("html", "ui://widget/accessibility.html", {}, async () => ({
    contents: [
      {
        uri: "ui://widget/accessibility.html",
        mimeType: "text/html",
        text: HTML_TEMPLATE,
        _meta: {
          "openai/widgetDescription":
            "Widget para analizar la accesibilidad de colores en imágenes según estándares WCAG",
        },
      },
    ],
  }));

  // Registrar tool para analizar accesibilidad
  server.registerTool("check_accessibility", {
    title: "Revisar accesibilidad de colores",
    description:
      "Analiza el contraste de colores en una imagen según estándares WCAG AA y AAA, detectando automáticamente texto y proporcionando sugerencias en OKLCH",
    inputSchema: {
      image: z.string().describe("Imagen en formato base64, data URL o URL"),
      wcag_level: z.enum(['AA', 'AAA', 'both']).default('both').describe("Nivel WCAG a evaluar")
    },
    _meta: {
      "openai/outputTemplate": "ui://widget/accessibility.html",
      "openai/widgetAccessible": true,
      "openai/toolInvocation/invoking": "Analizando accesibilidad de colores…",
      "openai/toolInvocation/invoked": "Análisis completado.",
    },
  }, async ({ image, wcag_level }) => {
    console.log("🎨 Analizando accesibilidad de imagen...");
    
    try {
      const results = await analyzeImageAccessibility(image, wcag_level);
      console.log("✅ Análisis completado:", results.summary);
      
      return {
        content: [{ 
          type: "text", 
          text: `Análisis completado: ${results.summary.total_pairs} pares de colores detectados, ${results.summary.passing_pairs} aprobados, ${results.summary.failing_pairs} fallidos.` 
        }],
        structuredContent: { data: results }
      };
    } catch (error: any) {
      console.error("❌ Error en análisis:", error);
      return {
        content: [{ 
          type: "text", 
          text: `Error al analizar la imagen: ${error.message}` 
        }],
        isError: true
      };
    }
  });

  return server;
}

// ==========================================
// SERVIDOR HTTP CON SSE
// ==========================================

type SessionRecord = { server: McpServer; transport: SSEServerTransport };
const sessions = new Map<string, SessionRecord>();

const ssePath = "/mcp";
const postPath = "/mcp/message";

async function handleSseRequest(res: ServerResponse) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  const server = createAccessibilityServer();
  const transport = new SSEServerTransport(postPath, res);
  const sessionId = transport.sessionId;

  sessions.set(sessionId, { server, transport });

  transport.onclose = async () => {
    sessions.delete(sessionId);
    console.log(`🔌 SSE connection closed (${sessionId})`);
  };

  transport.onerror = (err) => console.error("⚠️ SSE transport error:", err);

  try {
    await server.connect(transport);
  } catch (err) {
    sessions.delete(sessionId);
    console.error("❌ Failed to start SSE session:", err);
    if (!res.headersSent)
      res.writeHead(500).end("Failed to establish SSE connection");
  }
}

async function handlePostMessage(
  req: IncomingMessage,
  res: ServerResponse,
  url: URL
) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "content-type");

  const sessionId = url.searchParams.get("sessionId");
  if (!sessionId) return res.writeHead(400).end("Missing sessionId");

  const session = sessions.get(sessionId);
  if (!session) return res.writeHead(404).end("Unknown session");

  try {
    await session.transport.handlePostMessage(req, res);
  } catch (err) {
    console.error("❌ Failed to process message:", err);
    if (!res.headersSent) res.writeHead(500).end("Failed to process message");
  }
}

const PORT = Number(process.env.PORT ?? 8000);

const httpServer = createServer(async (req, res) => {
  if (!req.url) return res.writeHead(400).end("Missing URL");
  const url = new URL(req.url, `http://${req.headers.host ?? "localhost"}`);

  if (
    req.method === "OPTIONS" &&
    (url.pathname === ssePath || url.pathname === postPath)
  ) {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "content-type",
    });
    res.end();
    return;
  }

  if (req.method === "GET" && url.pathname === ssePath) {
    await handleSseRequest(res);
    return;
  }

  if (req.method === "POST" && url.pathname === postPath) {
    await handlePostMessage(req, res, url);
    return;
  }

  res.writeHead(404).end("Not Found");
});

httpServer.listen(PORT, () => {
  console.log(`🎨 Color Accessibility MCP server running at http://localhost:${PORT}`);
  console.log(`📡 SSE stream: GET http://localhost:${PORT}${ssePath}`);
  console.log(`📨 Post:       POST http://localhost:${PORT}${postPath}?sessionId=...`);
  console.log(`\n💡 Para usar con ChatGPT, expón el puerto con ngrok:`);
  console.log(`   ngrok http ${PORT}`);
});