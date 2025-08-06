"""
Configuración de conexiones con exchanges y APIs.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

@dataclass
class BinanceConfig:
    """Configuración específica para Binance"""
    
    api_key: str
    secret_key: str
    testnet: bool = False
    
    # URLs de API
    base_url: str = "https://api.binance.com"
    testnet_url: str = "https://testnet.binance.vision"
    
    # WebSocket URLs
    ws_url: str = "wss://stream.binance.com:9443"
    testnet_ws_url: str = "wss://testnet.binance.vision"
    
    # Rate Limits
    requests_per_second: int = 10
    orders_per_second: int = 5
    orders_per_day: int = 200000
    
    @property
    def effective_base_url(self) -> str:
        return self.testnet_url if self.testnet else self.base_url
    
    @property
    def effective_ws_url(self) -> str:
        return self.testnet_ws_url if self.testnet else self.ws_url

@dataclass
class RedisConfig:
    """Configuración para Redis (cache y datos tiempo real)"""
    
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    
    # TTL por tipo de dato (segundos)
    price_data_ttl: int = 300      # 5 minutos
    analysis_results_ttl: int = 600  # 10 minutos
    market_data_ttl: int = 3600    # 1 hora

def get_binance_config() -> BinanceConfig:
    """Obtiene configuración de Binance desde variables de entorno"""
    
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    
    if not api_key or not secret_key:
        raise ValueError("BINANCE_API_KEY and BINANCE_SECRET_KEY must be set")
    
    return BinanceConfig(
        api_key=api_key,
        secret_key=secret_key,
        testnet=os.getenv('BINANCE_TESTNET', 'False').lower() == 'true'
    )

def get_redis_config() -> RedisConfig:
    """Obtiene configuración de Redis desde variables de entorno"""
    
    return RedisConfig(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        password=os.getenv('REDIS_PASSWORD')
    )
