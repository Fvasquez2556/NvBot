"""
Parámetros optimizados para Bot Crypto Momentum v2.0
Sistema simplificado enfocado en momentum ALCISTA únicamente
"""

# Indicadores Técnicos Optimizados
RSI_OVERSOLD = 25
RSI_OVERBOUGHT = 75
RSI_PERIOD = 14

MACD_FAST = 3
MACD_SLOW = 10
MACD_SIGNAL = 16

# Volume Analysis
VOLUME_SPIKE_THRESHOLD = 3.0  # 300%+ del promedio
MIN_VOLUME_24H = 1_000_000    # $1M mínimo

# Multi-Timeframe Analysis
TIMEFRAMES = ['5m', '15m', '1h', '4h']
MIN_TIMEFRAMES_BULLISH = 3  # Mínimo 3 timeframes alcistas para señal fuerte

# Sistema de Scoring (0-100 puntos)
HISTORICAL_MAX_SCORE = 25
TECHNICAL_MAX_SCORE = 50
CONFLUENCE_MAX_SCORE = 25

# Niveles de Confianza
CONFIDENCE_LEVELS = {
    'FUERTE': (85, 100),
    'ALTO': (70, 84),
    'MEDIO': (50, 69),
    'DÉBIL': (30, 49)
}

# Configuraciones Operativas
UPDATE_INTERVAL = 30  # segundos
TARGET_DAILY_SIGNALS = 3  # MÍNIMO de señales fuertes por día (no límite)
TARGET_MOVEMENT = 7.5  # +7.5% objetivo

# Períodos para análisis histórico
HISTORICAL_PERIODS = {
    'price_average': ['1d', '1w', '1m'],
    'peak_detection': ['1h', '4h', '12h', '1d']
}

# Filtros de mercado
MIN_PRICE = 0.01
MAX_PRICE = 1000
MIN_MARKET_CAP = 10_000_000

# WebSocket configuración
MAX_STREAMS_PER_CONNECTION = 20
PING_INTERVAL = 20
CONNECTION_TIMEOUT = 30
