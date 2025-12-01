import express from 'express';
import cors from 'cors';
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import Tesseract from 'tesseract.js';
import sharp from 'sharp';
import { converter, formatHex, formatCss } from 'culori';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Conversores de color
const oklch = converter('oklch');
const rgb = converter('rgb');

// Servidor MCP
const server = new Server(
  {
    name: "color-accessibility-checker",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Función para calcular luminancia relativa según WCAG
function getRelativeLuminance(r, g, b) {
  const [rs, gs, bs] = [r, g, b].map(val => {
    const v = val / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

// Calcular ratio de contraste WCAG
function calculateContrastRatio(color1, color2) {
  const lum1 = getRelativeLuminance(color1.r, color1.g, color1.b);
  const lum2 = getRelativeLuminance(color2.r, color2.g, color2.b);
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

// Evaluar conformidad WCAG
function evaluateWCAG(ratio) {
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

// Convertir hex a RGB
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

// Ajustar luminosidad en OKLCH
function adjustLuminance(oklchColor, delta) {
  return {
    ...oklchColor,
    l: Math.max(0, Math.min(1, oklchColor.l + delta))
  };
}

// Generar sugerencias de color en OKLCH
function generateColorSuggestions(bgHex, fgHex, targetRatio = 4.5) {
  const suggestions = [];

  // Convertir a OKLCH
  const bgOKLCH = oklch(bgHex);
  const fgOKLCH = oklch(fgHex);

  if (!bgOKLCH || !fgOKLCH) return suggestions;

  // Opción 1: Aclarar background
  for (let i = 0.1; i <= 0.5; i += 0.1) {
    const newBg = adjustLuminance(bgOKLCH, i);
    const newBgHex = formatHex(newBg);
    const newFgHex = fgHex;
    const bgRgb = hexToRgb(newBgHex);
    const fgRgb = hexToRgb(newFgHex);

    if (bgRgb && fgRgb) {
      const ratio = calculateContrastRatio(bgRgb, fgRgb);
      if (ratio >= targetRatio) {
        suggestions.push({
          type: 'lighten_bg',
          background_oklch: formatCss(newBg),
          foreground_oklch: formatCss(fgOKLCH),
          new_contrast_ratio: Math.round(ratio * 10) / 10,
          preview_hex_bg: newBgHex,
          preview_hex_fg: newFgHex
        });
        break;
      }
    }
  }

  // Opción 2: Oscurecer background
  for (let i = -0.1; i >= -0.5; i -= 0.1) {
    const newBg = adjustLuminance(bgOKLCH, i);
    const newBgHex = formatHex(newBg);
    const newFgHex = fgHex;
    const bgRgb = hexToRgb(newBgHex);
    const fgRgb = hexToRgb(newFgHex);

    if (bgRgb && fgRgb) {
      const ratio = calculateContrastRatio(bgRgb, fgRgb);
      if (ratio >= targetRatio) {
        suggestions.push({
          type: 'darken_bg',
          background_oklch: formatCss(newBg),
          foreground_oklch: formatCss(fgOKLCH),
          new_contrast_ratio: Math.round(ratio * 10) / 10,
          preview_hex_bg: newBgHex,
          preview_hex_fg: newFgHex
        });
        break;
      }
    }
  }

  // Opción 3: Ajustar foreground
  const fgDelta = fgOKLCH.l > 0.5 ? -0.3 : 0.3;
  const newFg = adjustLuminance(fgOKLCH, fgDelta);
  const newBgHex = bgHex;
  const newFgHex = formatHex(newFg);
  const bgRgb = hexToRgb(newBgHex);
  const fgRgb = hexToRgb(newFgHex);

  if (bgRgb && fgRgb) {
    const ratio = calculateContrastRatio(bgRgb, fgRgb);
    if (ratio >= targetRatio) {
      suggestions.push({
        type: 'adjust_fg',
        background_oklch: formatCss(bgOKLCH),
        foreground_oklch: formatCss(newFg),
        new_contrast_ratio: Math.round(ratio * 10) / 10,
        preview_hex_bg: newBgHex,
        preview_hex_fg: newFgHex
      });
    }
  }

  return suggestions;
}

// Extraer colores dominantes de una región
async function extractDominantColor(imageBuffer, x, y, width, height) {
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

// Procesar imagen y detectar texto con colores
async function analyzeImageAccessibility(imageData, wcagLevel = 'both') {
  try {
    let imageBuffer;

    if (typeof imageData === 'object' && imageData.data) {
      imageBuffer = Buffer.from(imageData.data, 'base64');
    } else if (typeof imageData === 'string' && imageData.startsWith('/')) {
      imageBuffer = await fs.readFile(imageData);
    } else if (typeof imageData === 'string' && imageData.startsWith('data:')) {
      const base64Data = imageData.split(',')[1];
      imageBuffer = Buffer.from(base64Data, 'base64');
    } else if (typeof imageData === 'string' && imageData.startsWith('http')) {
      const response = await fetch(imageData);
      imageBuffer = Buffer.from(await response.arrayBuffer());
    } else {
      imageBuffer = Buffer.from(imageData, 'base64');
    }

    imageBuffer = await sharp(imageBuffer).png().toBuffer();
    const metadata = await sharp(imageBuffer).metadata();
    const { data: { words } } = await Tesseract.recognize(imageBuffer, 'eng+spa');

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
        Math.min(width + 20, metadata.width - x0),
        Math.min(height + 20, metadata.height - y0)
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

  } catch (error) {
    throw new Error(`Error analyzing image: ${error.message}`);
  }
}

// Registrar tool
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "accessibility_check_image_colors",
      description: "Use this when the user wants to check color contrast accessibility in an image. Analyzes all text/background color pairs in the image, calculates WCAG contrast ratios (AA and AAA levels), and suggests OKLCH color alternatives for pairs that fail accessibility standards.",
      inputSchema: {
        type: "object",
        properties: {
          image: {
            type: "string",
            description: "Base64-encoded image, data URL, or image URL to analyze"
          },
          wcag_level: {
            type: "string",
            enum: ["AA", "AAA", "both"],
            default: "both",
            description: "WCAG conformance level to check against"
          }
        },
        required: ["image"]
      },
      annotations: {
        readOnlyHint: true
      },
      _meta: {
        "openai/outputTemplate": "html"
      }
    }
  ]
}));

// Handler para ejecutar tool
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "accessibility_check_image_colors") {
    const { image, wcag_level = "both" } = request.params.arguments;

    try {
      const results = await analyzeImageAccessibility(image, wcag_level);

      // Read and inject template
      const templatePath = path.join(__dirname, '../web/ui-template.html');
      let htmlContent = await fs.readFile(templatePath, 'utf-8');
      
      // Inject data
      htmlContent = htmlContent.replace(
        'const sampleData = {', 
        `const sampleData = ${JSON.stringify(results)}; \n const _ignored = {`
      );

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(results, null, 2)
          },
          {
            type: "resource",
            resource: {
              uri: "ui://widget/color-accessibility.html",
              mimeType: "text/html",
              text: htmlContent
            }
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              error: error.message,
              summary: {
                total_pairs: 0,
                passing_pairs: 0,
                failing_pairs: 0,
                detected_texts: 0
              },
              color_pairs: []
            })
          }
        ],
        isError: true
      };
    }
  }

  throw new Error(`Unknown tool: ${request.params.name}`);
});

// Express App
const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));

// Health check
app.get('/', (req, res) => {
  res.json({ status: 'active', service: 'Color Accessibility MCP' });
});

// SSE Endpoint
let transport;
app.get('/mcp/sse', async (req, res) => {
  console.log('New SSE connection');
  transport = new SSEServerTransport('/mcp/messages', res);
  await server.connect(transport);
});

app.post('/mcp/messages', async (req, res) => {
  if (transport) {
    await transport.handlePostMessage(req, res);
  } else {
    res.status(400).send('No active connection');
  }
});

const PORT = process.env.PORT || 8000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
