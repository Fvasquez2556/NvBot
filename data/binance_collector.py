"""
Binance Data Collector v2.0
Adaptador del data_fetcher existente para la nueva arquitectura
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from data.data_fetcher import MassiveDataCollector as OriginalCollector
from config.parameters import TIMEFRAMES, MIN_VOLUME_24H
from utils.logger import log


class BinanceCollector:
    """
    Adaptador del data collector existente para la nueva arquitectura v2.0.
    Organiza los datos en el formato requerido por los nuevos analizadores.
    """
    
    def __init__(self):
        # Usar el collector existente como base
        self.original_collector = OriginalCollector()
        self.initialized = False
        
    async def initialize(self):
        """Inicializa el collector adaptado"""
        try:
            await self.original_collector.initialize()
            self.initialized = True
            log.info("✅ BinanceCollector v2.0 inicializado")
        except Exception as e:
            log.error(f"Error inicializando BinanceCollector: {e}")
            raise
    
    async def start(self):
        """Inicia la recolección de datos"""
        if not self.initialized:
            await self.initialize()
        await self.original_collector.start()
    
    async def stop(self):
        """Detiene la recolección de datos"""
        await self.original_collector.stop()
    
    def register_callback(self, callback):
        """Registra callback para nuevos datos"""
        self.original_collector.register_callback(callback)
    
    def get_all_symbols_data(self) -> Dict[str, Dict]:
        """
        Obtiene datos de todos los símbolos organizados para v2.0
        
        Returns:
            Dict con estructura:
            {
                'BTCUSDT': {
                    'historical_data': {...},
                    'current_data': {...},
                    'timeframe_data': {...}
                }
            }
        """
        try:
            # Obtener datos del collector original
            raw_data = self.original_collector.get_all_symbols_data()
            
            # Adaptar al nuevo formato
            adapted_data = {}
            for symbol, symbol_data in raw_data.items():
                if self._should_include_symbol(symbol, symbol_data):
                    adapted_data[symbol] = self._adapt_symbol_data(symbol, symbol_data)
            
            log.debug(f"📊 Datos adaptados para {len(adapted_data)} símbolos")
            return adapted_data
            
        except Exception as e:
            log.error(f"Error obteniendo datos adaptados: {e}")
            return {}
    
    def _should_include_symbol(self, symbol: str, symbol_data: Dict) -> bool:
        """Determina si incluir un símbolo según filtros v2.0"""
        try:
            # Solo pares USDT
            if not symbol.endswith('USDT'):
                return False
            
            # Verificar volumen mínimo
            ticker = symbol_data.get('ticker', {})
            volume_24h = float(ticker.get('quoteVolume', 0))
            if volume_24h < MIN_VOLUME_24H:
                return False
            
            # Verificar que tengamos datos de klines
            klines = symbol_data.get('klines', {})
            if not klines:
                return False
            
            # Verificar timeframes mínimos
            required_timeframes = ['1m', '5m', '15m', '1h']
            for tf in required_timeframes:
                if tf not in klines or len(klines[tf]) < 20:
                    return False
            
            return True
            
        except Exception as e:
            log.error(f"Error filtrando símbolo {symbol}: {e}")
            return False
    
    def _adapt_symbol_data(self, symbol: str, raw_data: Dict) -> Dict:
        """
        Adapta datos de un símbolo al formato v2.0
        
        Returns:
            Dict con estructura para v2.0:
            {
                'historical_data': {...},    # Para HistoricalAnalyzer
                'current_data': {...},       # Para TechnicalAnalyzer  
                'timeframe_data': {...}      # Para ConfluenceValidator
            }
        """
        try:
            adapted = {
                'historical_data': self._extract_historical_data(raw_data),
                'current_data': self._extract_current_data(raw_data),
                'timeframe_data': self._extract_timeframe_data(raw_data)
            }
            
            return adapted
            
        except Exception as e:
            log.error(f"Error adaptando datos para {symbol}: {e}")
            return {}
    
    def _extract_historical_data(self, raw_data: Dict) -> Dict:
        """
        Extrae datos históricos para HistoricalAnalyzer
        
        Estructura esperada:
        {
            'current_price': float,
            'data_1d': [candles],
            'data_1w': [candles],  
            'data_1m': [candles],
            'data_1h': [candles],
            'data_4h': [candles],
            'data_12h': [candles]
        }
        """
        try:
            historical_data = {}
            
            # Precio actual
            ticker = raw_data.get('ticker', {})
            historical_data['current_price'] = float(ticker.get('price', 0))
            
            # Datos de klines por período
            klines = raw_data.get('klines', {})
            
            # Mapear timeframes disponibles a períodos históricos
            timeframe_mapping = {
                '1h': 'data_1h',
                '4h': 'data_4h', 
                '12h': 'data_12h',
                '1d': 'data_1d'
            }
            
            for tf, period_key in timeframe_mapping.items():
                if tf in klines:
                    candles = klines[tf]
                    # Convertir formato si es necesario
                    formatted_candles = []
                    for candle in candles:
                        if isinstance(candle, list) and len(candle) >= 6:
                            formatted_candles.append({
                                'open': float(candle[1]),
                                'high': float(candle[2]),
                                'low': float(candle[3]),
                                'close': float(candle[4]),
                                'volume': float(candle[5]),
                                'timestamp': candle[0]
                            })
                    historical_data[period_key] = formatted_candles
            
            # Para períodos más largos (1w, 1m), usar agregación de datos diarios
            if 'data_1d' in historical_data:
                daily_data = historical_data['data_1d']
                
                # Simular datos semanales (últimos 7 días)
                if len(daily_data) >= 7:
                    historical_data['data_1w'] = daily_data[-7:]
                
                # Simular datos mensuales (últimos 30 días)
                if len(daily_data) >= 30:
                    historical_data['data_1m'] = daily_data[-30:]
            
            return historical_data
            
        except Exception as e:
            log.error(f"Error extrayendo datos históricos: {e}")
            return {}
    
    def _extract_current_data(self, raw_data: Dict) -> Dict:
        """
        Extrae datos actuales para TechnicalAnalyzer
        
        Estructura esperada:
        {
            'price_data': [closes],
            'volume_data': [volumes],
            'ticker_data': {...}
        }
        """
        try:
            current_data = {}
            
            # Datos del ticker
            ticker = raw_data.get('ticker', {})
            current_data['ticker_data'] = ticker
            
            # Extraer datos de precio y volumen de klines de 1m
            klines = raw_data.get('klines', {})
            if '1m' in klines:
                candles_1m = klines['1m']
                
                # Precios de cierre
                price_data = []
                volume_data = []
                
                for candle in candles_1m:
                    if isinstance(candle, list) and len(candle) >= 6:
                        price_data.append(float(candle[4]))  # Close price
                        volume_data.append(float(candle[5]))  # Volume
                
                current_data['price_data'] = price_data
                current_data['volume_data'] = volume_data
            
            # Si no hay datos de 1m, usar 5m
            elif '5m' in klines:
                candles_5m = klines['5m']
                price_data = []
                volume_data = []
                
                for candle in candles_5m:
                    if isinstance(candle, list) and len(candle) >= 6:
                        price_data.append(float(candle[4]))
                        volume_data.append(float(candle[5]))
                
                current_data['price_data'] = price_data
                current_data['volume_data'] = volume_data
            
            return current_data
            
        except Exception as e:
            log.error(f"Error extrayendo datos actuales: {e}")
            return {}
    
    def _extract_timeframe_data(self, raw_data: Dict) -> Dict:
        """
        Extrae datos por timeframe para ConfluenceValidator
        
        Estructura esperada:
        {
            '5m': {'candles': [...], 'rsi': float, 'macd': {...}, 'sma_20': float},
            '15m': {...},
            '1h': {...},
            '4h': {...}
        }
        """
        try:
            timeframe_data = {}
            
            klines = raw_data.get('klines', {})
            
            for timeframe in TIMEFRAMES:
                if timeframe in klines:
                    candles = klines[timeframe]
                    
                    # Formatear velas
                    formatted_candles = []
                    closes = []
                    
                    for candle in candles:
                        if isinstance(candle, list) and len(candle) >= 6:
                            formatted_candle = {
                                'open': float(candle[1]),
                                'high': float(candle[2]),
                                'low': float(candle[3]),
                                'close': float(candle[4]),
                                'volume': float(candle[5]),
                                'timestamp': candle[0]
                            }
                            formatted_candles.append(formatted_candle)
                            closes.append(float(candle[4]))
                    
                    tf_data = {
                        'candles': formatted_candles,
                        'current_price': closes[-1] if closes else 0
                    }
                    
                    # Calcular indicadores básicos si tenemos suficientes datos
                    if len(closes) >= 20:
                        # RSI simple
                        tf_data['rsi'] = self._calculate_simple_rsi(closes)
                        
                        # SMA 20
                        tf_data['sma_20'] = sum(closes[-20:]) / 20
                        
                        # MACD básico
                        tf_data['macd'] = self._calculate_simple_macd(closes)
                    
                    timeframe_data[timeframe] = tf_data
            
            return timeframe_data
            
        except Exception as e:
            log.error(f"Error extrayendo datos de timeframes: {e}")
            return {}
    
    def _calculate_simple_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calcula RSI simple"""
        try:
            if len(prices) < period + 1:
                return None
            
            deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                return 100
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception:
            return None
    
    def _calculate_simple_macd(self, prices: List[float]) -> Dict:
        """Calcula MACD simple"""
        try:
            if len(prices) < 26:
                return {}
            
            # EMAs simples
            ema_12 = self._calculate_ema(prices, 12)
            ema_26 = self._calculate_ema(prices, 26)
            
            if ema_12 is None or ema_26 is None:
                return {}
            
            macd_line = ema_12 - ema_26
            
            return {
                'macd': macd_line,
                'signal': 0,  # Simplificado
                'histogram': macd_line
            }
            
        except Exception:
            return {}
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calcula EMA simple"""
        try:
            if len(prices) < period:
                return None
            
            multiplier = 2 / (period + 1)
            ema = prices[0]
            
            for price in prices[1:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))
            
            return ema
            
        except Exception:
            return None
    
    def get_market_overview(self) -> Dict:
        """Obtiene overview del mercado"""
        try:
            return self.original_collector.get_market_overview()
        except Exception as e:
            log.error(f"Error obteniendo overview de mercado: {e}")
            return {}
    
    def get_symbol_data(self, symbol: str) -> Optional[Dict]:
        """Obtiene datos de un símbolo específico adaptados a v2.0"""
        try:
            raw_data = self.original_collector.get_all_symbols_data()
            if symbol in raw_data:
                return self._adapt_symbol_data(symbol, raw_data[symbol])
            return None
            
        except Exception as e:
            log.error(f"Error obteniendo datos de {symbol}: {e}")
            return None
