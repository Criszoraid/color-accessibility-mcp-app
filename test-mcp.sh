#!/bin/bash

# Test script for MCP server
# This script tests the MCP endpoints to verify they work correctly

SERVER_URL="${1:-http://localhost:8000}"

echo "🧪 Testing MCP Server at: $SERVER_URL"
echo "================================================"
echo ""

# Test 1: Initialize
echo "1️⃣ Testing initialize..."
curl -s -X POST "$SERVER_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize"
  }' | jq '.'

echo ""
echo "================================================"
echo ""

# Test 2: List tools
echo "2️⃣ Testing tools/list..."
curl -s -X POST "$SERVER_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
  }' | jq '.'

echo ""
echo "================================================"
echo ""

# Test 3: Call tool with image URL
echo "3️⃣ Testing tools/call with image_url..."
curl -s -X POST "$SERVER_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "analyze_color_accessibility",
      "arguments": {
        "image_url": "https://example.com/test-image.png",
        "wcag_level": "AA"
      }
    }
  }' | jq '.result.content[0].text'

echo ""
echo "================================================"
echo ""

# Test 4: Call tool with only required parameter
echo "4️⃣ Testing tools/call with only image_url (no wcag_level)..."
curl -s -X POST "$SERVER_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "analyze_color_accessibility",
      "arguments": {
        "image_url": "https://example.com/another-test.jpg"
      }
    }
  }' | jq '.result.content[0].text'

echo ""
echo "================================================"
echo ""

echo "✅ All tests completed!"
echo ""
echo "📝 Notes:"
echo "  - If you see JSON responses, the server is working correctly"
echo "  - Check that 'image_url' is in the inputSchema"
echo "  - Verify that 'oneOf' is NOT present in the schema"
echo ""
echo "🚀 To test with production server:"
echo "  ./test-mcp.sh https://app-color-accessibility.onrender.com"
