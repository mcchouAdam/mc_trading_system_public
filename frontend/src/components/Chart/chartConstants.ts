export const CHART_COLORS = {
    background: '#131722',
    text: '#d1d4dc',
    grid: '#2B2B43',
    up: '#26a69a',
    down: '#ef5350',
    primary: '#2962FF',
    orange: '#ff9800'
};

export const RESOLUTION_MAP: Record<string, number> = {
    'MINUTE': 60,
    'MINUTE_5': 300,
    'MINUTE_15': 900,
    'HOUR': 3600,
    'HOUR_4': 14400,
    'DAY': 86400
};

export const CHART_OPTIONS = {
    autoSize: true,
    layout: {
        background: { type: 'solid' as const, color: CHART_COLORS.background },
        textColor: CHART_COLORS.text,
    },
    grid: {
        vertLines: { color: CHART_COLORS.grid },
        horzLines: { color: CHART_COLORS.grid },
    },
    rightPriceScale: { borderColor: CHART_COLORS.grid },
    crosshair: { mode: 0 },
    timeScale: {
        borderColor: CHART_COLORS.grid,
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 15,
    },
    localization: {
        locale: 'zh-TW',
    }
};
