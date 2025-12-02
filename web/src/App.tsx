import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './components/Card';

interface ColorPair {
    foreground: string;
    background: string;
    ratio: number;
    passes_aa_normal: boolean;
    passes_aa_large: boolean;
    passes_aaa_normal: boolean;
    passes_aaa_large: boolean;
    text_sample?: string;
    suggestions?: {
        lighten_bg?: Array<{ color: string; ratio: number; oklch: string }>;
        darken_bg?: Array<{ color: string; ratio: number; oklch: string }>;
        adjust_fg?: Array<{ color: string; ratio: number; oklch: string }>;
    };
}

interface AccessibilityData {
    total_pairs: number;
    passed_pairs: number;
    failed_pairs: number;
    color_pairs: ColorPair[];
}

declare global {
    interface Window {
        openai?: {
            toolOutput?: {
                accessibility?: AccessibilityData;
            };
            callTool?: (name: string, args: any) => Promise<any>;
        };
    }
}

export default function App() {
    const [data, setData] = useState<AccessibilityData | null>(() => {
        return window.openai?.toolOutput?.accessibility || null;
    });

    useEffect(() => {
        const handleSetGlobals = (event: any) => {
            if (event.detail?.globals?.toolOutput?.accessibility) {
                setData(event.detail.globals.toolOutput.accessibility);
            }
        };

        window.addEventListener('openai:set_globals', handleSetGlobals);
        return () => window.removeEventListener('openai:set_globals', handleSetGlobals);
    }, []);

    if (!data) {
        return (
            <div className="p-6 text-center">
                <p className="text-gray-500">No accessibility data available</p>
            </div>
        );
    }

    const getStatusIcon = (passes: boolean) => {
        return passes ? '✅' : '❌';
    };

    return (
        <div className="max-w-4xl mx-auto p-6 space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-3 gap-4">
                <Card>
                    <CardContent className="pt-6">
                        <div className="text-center">
                            <div className="text-3xl font-bold text-blue-600">{data.total_pairs}</div>
                            <div className="text-sm text-gray-600 mt-1">Total Pairs</div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="pt-6">
                        <div className="text-center">
                            <div className="text-3xl font-bold text-green-600">{data.passed_pairs}</div>
                            <div className="text-sm text-gray-600 mt-1">Passed</div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="pt-6">
                        <div className="text-center">
                            <div className="text-3xl font-bold text-red-600">{data.failed_pairs}</div>
                            <div className="text-sm text-gray-600 mt-1">Failed</div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Color Pairs */}
            <div className="space-y-4">
                <h2 className="text-2xl font-bold">Color Combinations</h2>

                {data.color_pairs.map((pair, index) => (
                    <Card key={index}>
                        <CardHeader>
                            <CardTitle className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div
                                        className="w-12 h-12 rounded border-2 border-gray-300"
                                        style={{
                                            backgroundColor: pair.background,
                                            color: pair.foreground,
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            fontSize: '20px',
                                            fontWeight: 'bold'
                                        }}
                                    >
                                        Aa
                                    </div>
                                    <div>
                                        <div className="font-mono text-sm">
                                            {pair.foreground} / {pair.background}
                                        </div>
                                        {pair.text_sample && (
                                            <div className="text-xs text-gray-500 mt-1">
                                                "{pair.text_sample}"
                                            </div>
                                        )}
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="text-2xl font-bold">{pair.ratio.toFixed(2)}:1</div>
                                    <div className="text-xs text-gray-500">Contrast Ratio</div>
                                </div>
                            </CardTitle>
                        </CardHeader>

                        <CardContent>
                            {/* WCAG Status */}
                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between text-sm">
                                        <span>AA Normal Text (4.5:1)</span>
                                        <span>{getStatusIcon(pair.passes_aa_normal)}</span>
                                    </div>
                                    <div className="flex items-center justify-between text-sm">
                                        <span>AA Large Text (3.0:1)</span>
                                        <span>{getStatusIcon(pair.passes_aa_large)}</span>
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between text-sm">
                                        <span>AAA Normal Text (7.0:1)</span>
                                        <span>{getStatusIcon(pair.passes_aaa_normal)}</span>
                                    </div>
                                    <div className="flex items-center justify-between text-sm">
                                        <span>AAA Large Text (4.5:1)</span>
                                        <span>{getStatusIcon(pair.passes_aaa_large)}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Suggestions */}
                            {pair.suggestions && (
                                <div className="mt-4 pt-4 border-t">
                                    <h4 className="font-semibold mb-3">💡 Suggested Improvements (OKLCH)</h4>

                                    {pair.suggestions.lighten_bg && pair.suggestions.lighten_bg.length > 0 && (
                                        <div className="mb-3">
                                            <div className="text-sm font-medium text-gray-700 mb-2">Lighten Background:</div>
                                            <div className="flex gap-2 flex-wrap">
                                                {pair.suggestions.lighten_bg.map((suggestion, i) => (
                                                    <div key={i} className="flex items-center gap-2 bg-gray-50 rounded p-2">
                                                        <div
                                                            className="w-8 h-8 rounded border"
                                                            style={{ backgroundColor: suggestion.color }}
                                                        />
                                                        <div className="text-xs">
                                                            <div className="font-mono">{suggestion.color}</div>
                                                            <div className="text-gray-500">{suggestion.ratio.toFixed(2)}:1</div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {pair.suggestions.darken_bg && pair.suggestions.darken_bg.length > 0 && (
                                        <div className="mb-3">
                                            <div className="text-sm font-medium text-gray-700 mb-2">Darken Background:</div>
                                            <div className="flex gap-2 flex-wrap">
                                                {pair.suggestions.darken_bg.map((suggestion, i) => (
                                                    <div key={i} className="flex items-center gap-2 bg-gray-50 rounded p-2">
                                                        <div
                                                            className="w-8 h-8 rounded border"
                                                            style={{ backgroundColor: suggestion.color }}
                                                        />
                                                        <div className="text-xs">
                                                            <div className="font-mono">{suggestion.color}</div>
                                                            <div className="text-gray-500">{suggestion.ratio.toFixed(2)}:1</div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {pair.suggestions.adjust_fg && pair.suggestions.adjust_fg.length > 0 && (
                                        <div>
                                            <div className="text-sm font-medium text-gray-700 mb-2">Adjust Foreground:</div>
                                            <div className="flex gap-2 flex-wrap">
                                                {pair.suggestions.adjust_fg.map((suggestion, i) => (
                                                    <div key={i} className="flex items-center gap-2 bg-gray-50 rounded p-2">
                                                        <div
                                                            className="w-8 h-8 rounded border"
                                                            style={{ backgroundColor: suggestion.color }}
                                                        />
                                                        <div className="text-xs">
                                                            <div className="font-mono">{suggestion.color}</div>
                                                            <div className="text-gray-500">{suggestion.ratio.toFixed(2)}:1</div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
}
