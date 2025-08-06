"""
Configuración principal del sistema de trading crypto.
Parámetros optimizados basados en investigación para detección de momentum +7.5%.
"""

from dataclasses import dataclass
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class TechnicalConfig:
    """Configuración de indicadores técnicos optimizados para crypto"""
    
    # RSI Optimizado para Crypto (25/75 vs 30/70 tradicional)
    rsi_period: int = 14
    rsi_oversold: float = 25.0      # Más sensible para crypto
    rsi_overbought: float = 75.0    # Permite momentum extendido
    
    # MACD Crypto-Optimizado (3-10-16 vs 12-26-9 tradicional)
    macd_fast: int = 3              # Captura movimientos rápidos
    macd_slow: int = 10             # Reduce ruido manteniendo sensibilidad
    macd_signal: int = 16           # Suaviza señales pero permite reactividad
    
    # Bollinger Bands para Crypto
    bb_period: int = 20
    bb_std_dev: float = 2.0
    
    # Volume Analysis
    volume_spike_threshold: float = 2.0     # 200% del promedio mínimo
    volume_spike_strong: float = 3.0        # 300% del promedio
    volume_spike_explosive: float = 5.0     # 500% del promedio
    volume_average_period: int = 20
    
    # Price Velocity Analysis
    velocity_timeframes: List[int] = None
    
    def __post_init__(self):
        if self.velocity_timeframes is None:
            self.velocity_timeframes = [5, 15, 60]  # 5min, 15min, 1h

@dataclass
class MomentumScoringConfig:
    """Sistema de scoring de momentum (0-100 puntos)"""
    
    # Distribución de puntos por componente
    rsi_max_points: int = 25
    macd_max_points: int = 20
    volume_max_points: int = 25
    velocity_max_points: int = 15
    breakout_max_points: int = 15
    
    # Umbrales de clasificación
    weak_threshold: int = 30        # Momentum Débil
    medium_threshold: int = 50      # Momentum Medio  
    high_threshold: int = 70        # Momentum Alto
    strong_threshold: int = 85      # Momentum Fuerte Alta Confianza
    
    # Factores de confluencia
    min_indicators_agreement: int = 3  # Mínimo 3 indicadores en acuerdo

@dataclass
class MarketFiltersConfig:
    """Filtros de mercado para seleccionar pares operables"""
    
    min_volume_24h: float = float(os.getenv('MIN_VOLUME_24H', 1000000))  # $1M
    min_price: float = float(os.getenv('MIN_PRICE', 0.01))
    max_price: float = float(os.getenv('MAX_PRICE', 1000))
    min_market_cap: float = 10000000  # $10M mínimo
    
    # Filtros de liquidez
    min_bid_ask_spread: float = 0.005  # 0.5% máximo spread
    min_order_book_depth: float = 100000  # $100K en order book

@dataclass
class MovementPredictionConfig:
    """Configuración para predicción de movimientos +7.5%"""
    
    target_movement: float = 7.5        # Objetivo +7.5%
    prediction_timeframes: List[int] = None  # Horas para alcanzar objetivo
    
    # Factores de predicción
    volatility_weight: float = 0.25
    momentum_weight: float = 0.35
    resistance_weight: float = 0.20
    correlation_weight: float = 0.10
    liquidity_weight: float = 0.10
    
    def __post_init__(self):
        if self.prediction_timeframes is None:
            self.prediction_timeframes = [2, 4, 8, 24]  # 2h, 4h, 8h, 24h

@dataclass
class WebSocketConfig:
    """Configuración de conexiones WebSocket"""
    
    max_streams_per_connection: int = 190  # Margen de seguridad (límite 200)
    reconnect_interval: int = 24 * 3600    # Reconectar cada 24h
    ping_interval: int = 30                # Ping cada 30 segundos
    connection_timeout: int = 10
    
    # Rate Limiting
    requests_per_minute: int = 4800        # Límite Binance: 6000, usamos 4800
    weight_limit: int = 1000               # Límite de peso por minuto

@dataclass
class DashboardConfig:
    """Configuración del dashboard web"""
    
    host: str = os.getenv('DASHBOARD_HOST', '0.0.0.0')
    port: int = int(os.getenv('DASHBOARD_PORT', 8050))
    debug: bool = os.getenv('DASHBOARD_DEBUG', 'False').lower() == 'true'
    
    update_interval: int = 30              # Actualizar cada 30 segundos
    max_opportunities_display: int = 50    # Máximo oportunidades a mostrar
    chart_timeframe: str = '1h'           # Timeframe para gráficas

@dataclass
class AlertConfig:
    """Configuración del sistema de alertas"""
    
    telegram_enabled: bool = bool(os.getenv('TELEGRAM_BOT_TOKEN'))
    telegram_bot_token: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat_id: str = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Cooldowns para evitar spam
    alert_cooldown_minutes: Dict[str, int] = None
    
    def __post_init__(self):
        if self.alert_cooldown_minutes is None:
            self.alert_cooldown_minutes = {
                'STRONG': 2,    # Fuerte: cada 2 minutos máximo
                'HIGH': 5,      # Alto: cada 5 minutos
                'MEDIUM': 10,   # Medio: cada 10 minutos
                'WEAK': 30      # Débil: cada 30 minutos
            }

class Config:
    """Configuración central del sistema"""
    
    def __init__(self):
        self.technical = TechnicalConfig()
        self.scoring = MomentumScoringConfig()
        self.filters = MarketFiltersConfig()
        self.prediction = MovementPredictionConfig()
        self.websocket = WebSocketConfig()
        self.dashboard = DashboardConfig()
        self.alerts = AlertConfig()
        
        # Binance API
        self.binance_api_key = os.getenv('BINANCE_API_KEY')
        self.binance_secret_key = os.getenv('BINANCE_SECRET_KEY')
        
        # Redis
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis_db = int(os.getenv('REDIS_DB', 0))
        
        # Intervalos de actualización
        self.update_interval = int(os.getenv('UPDATE_INTERVAL', 30))
    
    def validate(self):
        """Valida la configuración"""
        if not self.binance_api_key or not self.binance_secret_key:
            raise ValueError("Binance API keys are required")
        
        if self.scoring.weak_threshold >= self.scoring.medium_threshold:
            raise ValueError("Invalid scoring thresholds")
            
        if self.prediction.target_movement <= 0:
            raise ValueError("Target movement must be positive")
    
    def get_momentum_classification(self, score: float) -> str:
        """Clasifica el momentum basado en el score"""
        if score >= self.scoring.strong_threshold:
            return "FUERTE"
        elif score >= self.scoring.high_threshold:
            return "ALTO"
        elif score >= self.scoring.medium_threshold:
            return "MEDIO"
        elif score >= self.scoring.weak_threshold:
            return "DÉBIL"
        else:
            return "DESCARTADO"

# Instancia global de configuración
config = Config()
