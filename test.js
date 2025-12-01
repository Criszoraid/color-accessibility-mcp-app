// test.js - Ejemplos de pruebas para el Color Accessibility Checker

import assert from 'assert';

// ============================================
// TEST 1: Cálculo de Luminancia Relativa
// ============================================

function getRelativeLuminance(r, g, b) {
  const [rs, gs, bs] = [r, g, b].map(val => {
    const v = val / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function testLuminance() {
  console.log('🧪 Test 1: Luminancia Relativa');
  
  // Blanco puro = luminancia máxima
  const whiteLum = getRelativeLuminance(255, 255, 255);
  assert(Math.abs(whiteLum - 1.0) < 0.001, 'Blanco debe tener luminancia ~1.0');
  console.log('  ✅ Blanco:', whiteLum.toFixed(3));
  
  // Negro puro = luminancia mínima
  const blackLum = getRelativeLuminance(0, 0, 0);
  assert(Math.abs(blackLum - 0.0) < 0.001, 'Negro debe tener luminancia ~0.0');
  console.log('  ✅ Negro:', blackLum.toFixed(3));
  
  // Gris medio
  const grayLum = getRelativeLuminance(128, 128, 128);
  console.log('  ✅ Gris medio:', grayLum.toFixed(3));
  
  console.log('  ✅ Test de luminancia pasado\n');
}

// ============================================
// TEST 2: Cálculo de Ratio de Contraste
// ============================================

function calculateContrastRatio(color1, color2) {
  const lum1 = getRelativeLuminance(color1.r, color1.g, color1.b);
  const lum2 = getRelativeLuminance(color2.r, color2.g, color2.b);
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

function testContrastRatio() {
  console.log('🧪 Test 2: Ratio de Contraste');
  
  // Negro sobre blanco = máximo contraste
  const blackOnWhite = calculateContrastRatio(
    { r: 0, g: 0, b: 0 },
    { r: 255, g: 255, b: 255 }
  );
  assert(Math.abs(blackOnWhite - 21) < 0.1, 'Negro/Blanco debe ser ~21:1');
  console.log('  ✅ Negro sobre blanco:', blackOnWhite.toFixed(1) + ':1');
  
  // Mismo color = mínimo contraste
  const sameColor = calculateContrastRatio(
    { r: 128, g: 128, b: 128 },
    { r: 128, g: 128, b: 128 }
  );
  assert(Math.abs(sameColor - 1) < 0.01, 'Mismo color debe ser ~1:1');
  console.log('  ✅ Mismo color:', sameColor.toFixed(1) + ':1');
  
  // Caso real: texto gris oscuro sobre blanco
  const darkGrayOnWhite = calculateContrastRatio(
    { r: 68, g: 68, b: 68 },
    { r: 255, g: 255, b: 255 }
  );
  console.log('  ✅ Gris oscuro sobre blanco:', darkGrayOnWhite.toFixed(1) + ':1');
  
  console.log('  ✅ Test de contraste pasado\n');
}

// ============================================
// TEST 3: Evaluación WCAG
// ============================================

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

function testWCAGEvaluation() {
  console.log('🧪 Test 3: Evaluación WCAG');
  
  // Ratio que pasa AAA
  const excellentRatio = 8.5;
  const evalExcellent = evaluateWCAG(excellentRatio);
  assert(evalExcellent.aaa.normal_text, 'Ratio 8.5 debe pasar AAA normal');
  console.log('  ✅ Ratio 8.5:1 pasa AAA normal y large');
  
  // Ratio que pasa solo AA
  const goodRatio = 5.0;
  const evalGood = evaluateWCAG(goodRatio);
  assert(evalGood.aa.normal_text, 'Ratio 5.0 debe pasar AA normal');
  assert(!evalGood.aaa.normal_text, 'Ratio 5.0 no debe pasar AAA normal');
  console.log('  ✅ Ratio 5.0:1 pasa AA pero no AAA');
  
  // Ratio que falla
  const poorRatio = 2.8;
  const evalPoor = evaluateWCAG(poorRatio);
  assert(!evalPoor.aa.normal_text, 'Ratio 2.8 debe fallar AA normal');
  console.log('  ✅ Ratio 2.8:1 falla accesibilidad');
  
  console.log('  ✅ Test de evaluación WCAG pasado\n');
}

// ============================================
// TEST 4: Casos Reales de Accesibilidad
// ============================================

function testRealWorldCases() {
  console.log('🧪 Test 4: Casos Reales');
  
  const cases = [
    {
      name: 'Texto negro sobre amarillo (advertencia típica)',
      bg: { r: 255, g: 255, b: 0 },   // #FFFF00
      fg: { r: 0, g: 0, b: 0 },       // #000000
      expectedPass: true
    },
    {
      name: 'Texto gris claro sobre blanco (error común)',
      bg: { r: 255, g: 255, b: 255 }, // #FFFFFF
      fg: { r: 200, g: 200, b: 200 }, // #C8C8C8
      expectedPass: false
    },
    {
      name: 'Texto blanco sobre azul (link típico)',
      bg: { r: 0, g: 0, b: 255 },     // #0000FF
      fg: { r: 255, g: 255, b: 255 }, // #FFFFFF
      expectedPass: true
    },
    {
      name: 'Texto verde sobre rojo (problema de daltonismo)',
      bg: { r: 255, g: 0, b: 0 },     // #FF0000
      fg: { r: 0, g: 255, b: 0 },     // #00FF00
      expectedPass: false
    }
  ];
  
  cases.forEach(testCase => {
    const ratio = calculateContrastRatio(testCase.bg, testCase.fg);
    const eval = evaluateWCAG(ratio);
    const passes = eval.aa.normal_text;
    
    console.log(`  ${passes ? '✅' : '❌'} ${testCase.name}`);
    console.log(`     Ratio: ${ratio.toFixed(1)}:1 | AA: ${passes ? 'PASS' : 'FAIL'}`);
  });
  
  console.log('  ✅ Test de casos reales completado\n');
}

// ============================================
// TEST 5: Conversión de Colores Hex
// ============================================

function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

function testHexConversion() {
  console.log('🧪 Test 5: Conversión Hex a RGB');
  
  const tests = [
    { hex: '#FFFFFF', expected: { r: 255, g: 255, b: 255 } },
    { hex: '#000000', expected: { r: 0, g: 0, b: 0 } },
    { hex: '#FF0000', expected: { r: 255, g: 0, b: 0 } },
    { hex: 'A0B0C0', expected: { r: 160, g: 176, b: 192 } }, // Sin #
  ];
  
  tests.forEach(test => {
    const rgb = hexToRgb(test.hex);
    assert(rgb !== null, `Debe convertir ${test.hex}`);
    assert(rgb.r === test.expected.r, `R debe ser ${test.expected.r}`);
    assert(rgb.g === test.expected.g, `G debe ser ${test.expected.g}`);
    assert(rgb.b === test.expected.b, `B debe ser ${test.expected.b}`);
    console.log(`  ✅ ${test.hex} → RGB(${rgb.r}, ${rgb.g}, ${rgb.b})`);
  });
  
  console.log('  ✅ Test de conversión hex pasado\n');
}

// ============================================
// TEST 6: Ejemplos de Prompts Esperados
// ============================================

function testPromptMatching() {
  console.log('🧪 Test 6: Prompts Esperados');
  
  const validPrompts = [
    "Check the accessibility of this image",
    "Analyze WCAG contrast",
    "Does this design pass accessibility standards?",
    "¿Esta imagen es accesible?",
    "Help me fix the colors in this screenshot",
    "Is this text readable?"
  ];
  
  const invalidPrompts = [
    "What are WCAG guidelines?", // Informativo
    "Create an accessible color palette", // Generativo
    "Explain color theory", // Educativo
  ];
  
  console.log('  ✅ Prompts VÁLIDOS (deben activar el tool):');
  validPrompts.forEach(p => console.log(`     ✓ "${p}"`));
  
  console.log('\n  ❌ Prompts INVÁLIDOS (NO deben activar el tool):');
  invalidPrompts.forEach(p => console.log(`     ✗ "${p}"`));
  
  console.log('  ✅ Test de prompts completado\n');
}

// ============================================
// TEST 7: Límites y Edge Cases
// ============================================

function testEdgeCases() {
  console.log('🧪 Test 7: Edge Cases');
  
  // Colores muy similares
  const similar = calculateContrastRatio(
    { r: 128, g: 128, b: 128 },
    { r: 130, g: 130, b: 130 }
  );
  console.log(`  ✅ Colores muy similares: ${similar.toFixed(2)}:1 (debe ser ~1)`);
  
  // Contraste máximo
  const maximum = calculateContrastRatio(
    { r: 0, g: 0, b: 0 },
    { r: 255, g: 255, b: 255 }
  );
  console.log(`  ✅ Contraste máximo: ${maximum.toFixed(1)}:1 (debe ser 21)`);
  
  // Colores invertidos (debe dar mismo resultado)
  const inverted = calculateContrastRatio(
    { r: 255, g: 255, b: 255 },
    { r: 0, g: 0, b: 0 }
  );
  assert(Math.abs(maximum - inverted) < 0.01, 'Orden no debe importar');
  console.log(`  ✅ Colores invertidos: ${inverted.toFixed(1)}:1 (mismo resultado)`);
  
  console.log('  ✅ Test de edge cases pasado\n');
}

// ============================================
// EJECUTAR TODOS LOS TESTS
// ============================================

async function runAllTests() {
  console.log('🚀 Ejecutando suite de tests...\n');
  console.log('='.repeat(50) + '\n');
  
  try {
    testLuminance();
    testContrastRatio();
    testWCAGEvaluation();
    testRealWorldCases();
    testHexConversion();
    testPromptMatching();
    testEdgeCases();
    
    console.log('='.repeat(50));
    console.log('✅ TODOS LOS TESTS PASARON');
    console.log('='.repeat(50));
    
  } catch (error) {
    console.error('\n❌ ERROR EN LOS TESTS:');
    console.error(error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

// Ejecutar si es el archivo principal
if (import.meta.url === `file://${process.argv[1]}`) {
  runAllTests();
}

export {
  getRelativeLuminance,
  calculateContrastRatio,
  evaluateWCAG,
  hexToRgb
};

// ============================================
// CASOS DE USO DOCUMENTADOS
// ============================================

/**
 * CASO 1: Diseñador verifica un mockup
 * 
 * Input: Imagen de diseño con múltiples textos
 * Expected: Lista completa de todos los pares detectados
 * Output: 
 * - Resumen con estadísticas
 * - Cada par con su ratio y evaluación WCAG
 * - Sugerencias OKLCH para los que fallan
 */

/**
 * CASO 2: Desarrollador audita una app
 * 
 * Input: Screenshot de aplicación web
 * Expected: Identificar problemas de accesibilidad
 * Output:
 * - Destacar elementos que fallan
 * - Sugerencias de corrección inmediata
 * - Códigos hex y OKLCH para implementar
 */

/**
 * CASO 3: Cliente pide revisión de brand colors
 * 
 * Input: Paleta de colores corporativa
 * Expected: Validar todas las combinaciones
 * Output:
 * - Matriz de compatibilidad
 * - Alternativas que mantienen la identidad de marca
 */

/**
 * CASO 4: Documento con texto pequeño
 * 
 * Input: PDF o imagen con letra pequeña
 * Expected: Aplicar umbral más estricto (7:1 para AAA)
 * Output:
 * - Evaluación más rigurosa
 * - Advertencia sobre texto pequeño
 */