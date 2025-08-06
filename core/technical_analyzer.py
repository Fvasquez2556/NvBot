"""
Analizador Técnico v2.0
Sección 2: Análisis de indicadores técnicos para detección de momentum
Score: 0-50 puntos
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime

from indicators.rsi_optimizer import RSIOptimizer
from indicators.macd_sensitive import MACDSensitive
from indicators.volume_analyzer import VolumeAnalyzer
from config.parameters import (
    RSI_OVERSOLD, RSI_OVERBOUGHT, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    VOLUME_SPIKE_THRESHOLD, TECHNICAL_MAX_SCORE
)
from utils.logger import log


class TechnicalAnalyzer:
    """
    Análisis de indicadores técnicos optimizados para momentum alcista.
    Combina RSI, MACD y análisis de volumen para generar score 0-50.
    """
    
    def __init__(self):
        # Reutilizar indicadores existentes optimizados
        self.rsi_analyzer = RSIOptimizer()
        self.macd_analyzer = MACDSensitive()
        self.volume_analyzer = VolumeAnalyzer()
        
    async def analyze_symbol_technicals(self, symbol: str, symbol_data: Dict) -> Dict:
        """
        Análisis técnico completo para un símbolo.
        
        Returns:
            Dict con score técnico (0-50) y detalles de cada indicador
        """
        try:
            result = {
                'symbol': symbol,
                'technical_score': 0,
                'rsi_analysis': {},
                'macd_analysis': {},
                'volume_analysis': {},
                'confluence_factors': [],
                'timestamp': datetime.now()
            }
            
            # Verificar datos suficientes
            if not self._validate_technical_data(symbol_data):
                result['error'] = 'Insufficient data for technical analysis'
                return result
            
            # 1. Análisis RSI (25/75 umbrales)
            rsi_result = await self._analyze_rsi_momentum(symbol_data)
            result['rsi_analysis'] = rsi_result
            
            # 2. Análisis MACD (3-10-16 configuración)
            macd_result = await self._analyze_macd_momentum(symbol_data)
            result['macd_analysis'] = macd_result
            
            # 3. Análisis de Volumen (spike 300%+)
            volume_result = await self._analyze_volume_momentum(symbol_data)
            result['volume_analysis'] = volume_result
            
            # 4. Factores de confluencia
            confluence_factors = self._identify_confluence_factors(
                rsi_result, macd_result, volume_result
            )
            result['confluence_factors'] = confluence_factors
            
            # 5. Calcular score técnico total
            technical_score = self._calculate_technical_score(
                rsi_result, macd_result, volume_result, confluence_factors
            )
            result['technical_score'] = technical_score
            
            log.debug(f"Análisis técnico {symbol}: {technical_score}/50 puntos")
            return result
            
        except Exception as e:
            log.error(f"Error en análisis técnico {symbol}: {e}")
            return {
                'symbol': symbol,
                'technical_score': 0,
                'error': str(e),
                'timestamp': datetime.now()
            }
    
    def _validate_technical_data(self, symbol_data: Dict) -> bool:
        """Valida que tengamos datos suficientes para análisis técnico"""
        required_fields = ['price_data', 'volume_data']
        
        for field in required_fields:
            if field not in symbol_data or not symbol_data[field]:
                return False
        
        # Verificar longitud mínima
        price_data = symbol_data['price_data']
        if len(price_data) < 50:  # Mínimo para MACD y RSI
            return False
        
        return True
    
    async def _analyze_rsi_momentum(self, symbol_data: Dict) -> Dict:
        """
        Análisis RSI optimizado para crypto (25/75 umbrales)
        Score máximo: 15 puntos
        """
        try:
            # Usar el RSI optimizer existente pero adaptado
            rsi_data = await self.rsi_analyzer.calculate_rsi(
                symbol_data['price_data']
            )
            
            current_rsi = rsi_data.get('current_value', 50)
            rsi_trend = rsi_data.get('trend', 'neutral')
            rsi_momentum = rsi_data.get('momentum_strength', 0)
            
            result = {
                'current_rsi': current_rsi,
                'trend': rsi_trend,
                'momentum_strength': rsi_momentum,
                'score': 0,
                'signals': []
            }
            
            # Scoring RSI para momentum alcista
            score = 0
            
            # Condiciones alcistas RSI
            if current_rsi > RSI_OVERSOLD and current_rsi < 50:
                # Zona de recuperación desde sobrevendido
                score += 8
                result['signals'].append('oversold_recovery')
                
            elif current_rsi >= 50 and current_rsi < RSI_OVERBOUGHT:
                # Zona alcista saludable
                score += 12
                result['signals'].append('bullish_zone')
                
            elif current_rsi >= RSI_OVERBOUGHT:
                # Zona de momentum fuerte (pero cuidado)
                score += 6
                result['signals'].append('strong_momentum')
            
            # Bonus por tendencia alcista
            if rsi_trend == 'bullish':
                score += 3
                result['signals'].append('bullish_trend')
            
            result['score'] = min(score, 15)
            return result
            
        except Exception as e:
            log.error(f"Error en análisis RSI: {e}")
            return {'score': 0, 'error': str(e)}
    
    async def _analyze_macd_momentum(self, symbol_data: Dict) -> Dict:
        """
        Análisis MACD optimizado (3-10-16 configuración)
        Score máximo: 20 puntos
        """
        try:
            # Usar el MACD sensitive existente
            macd_data = await self.macd_analyzer.calculate_advanced_macd(
                symbol_data['price_data']
            )
            
            macd_line = macd_data.get('macd_line', 0)
            signal_line = macd_data.get('signal_line', 0)
            histogram = macd_data.get('histogram', 0)
            trend = macd_data.get('trend', 'neutral')
            
            result = {
                'macd_line': macd_line,
                'signal_line': signal_line,
                'histogram': histogram,
                'trend': trend,
                'score': 0,
                'signals': []
            }
            
            score = 0
            
            # Condiciones alcistas MACD
            if macd_line > signal_line:
                # MACD por encima de señal
                score += 8
                result['signals'].append('macd_above_signal')
                
                # Bonus si histograma creciente
                if histogram > 0:
                    score += 4
                    result['signals'].append('histogram_positive')
            
            # Crossover alcista reciente
            if macd_data.get('recent_bullish_crossover', False):
                score += 8
                result['signals'].append('bullish_crossover')
            
            # MACD en territorio positivo
            if macd_line > 0:
                score += 3
                result['signals'].append('macd_positive')
            
            # Momentum creciente
            if trend == 'bullish':
                score += 5
                result['signals'].append('bullish_momentum')
            
            result['score'] = min(score, 20)
            return result
            
        except Exception as e:
            log.error(f"Error en análisis MACD: {e}")
            return {'score': 0, 'error': str(e)}
    
    async def _analyze_volume_momentum(self, symbol_data: Dict) -> Dict:
        """
        Análisis de volumen con threshold 300%+
        Score máximo: 15 puntos
        """
        try:
            # Usar el volume analyzer existente
            volume_data = await self.volume_analyzer.analyze_volume_patterns(
                symbol_data['volume_data'], symbol_data['price_data']
            )
            
            current_volume = volume_data.get('current_volume', 0)
            avg_volume = volume_data.get('average_volume', 1)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            volume_trend = volume_data.get('trend', 'neutral')
            
            result = {
                'current_volume': current_volume,
                'average_volume': avg_volume,
                'volume_ratio': volume_ratio,
                'trend': volume_trend,
                'score': 0,
                'signals': []
            }
            
            score = 0
            
            # Scoring por ratio de volumen
            if volume_ratio >= 5.0:  # 500%+ del promedio
                score += 15
                result['signals'].append('explosive_volume')
                
            elif volume_ratio >= VOLUME_SPIKE_THRESHOLD:  # 300%+ del promedio
                score += 12
                result['signals'].append('high_volume_spike')
                
            elif volume_ratio >= 2.0:  # 200%+ del promedio
                score += 8
                result['signals'].append('moderate_volume_spike')
                
            elif volume_ratio >= 1.5:  # 150%+ del promedio
                score += 4
                result['signals'].append('increased_volume')
            
            # Bonus por volumen creciente sostenido
            if volume_trend == 'increasing':
                score += 3
                result['signals'].append('volume_trend_up')
            
            result['score'] = min(score, 15)
            return result
            
        except Exception as e:
            log.error(f"Error en análisis de volumen: {e}")
            return {'score': 0, 'error': str(e)}
    
    def _identify_confluence_factors(self, rsi_result: Dict, macd_result: Dict, 
                                   volume_result: Dict) -> List[str]:
        """Identifica factores de confluencia entre indicadores"""
        confluence_factors = []
        
        try:
            # Confluencia RSI + MACD
            rsi_signals = rsi_result.get('signals', [])
            macd_signals = macd_result.get('signals', [])
            volume_signals = volume_result.get('signals', [])
            
            # Todos los indicadores alcistas
            if ('bullish_zone' in rsi_signals and 
                'macd_above_signal' in macd_signals):
                confluence_factors.append('rsi_macd_bullish')
            
            # Volume spike + momentum técnico
            if (any('volume' in sig for sig in volume_signals) and
                ('bullish_crossover' in macd_signals or 'bullish_zone' in rsi_signals)):
                confluence_factors.append('volume_momentum_confluence')
            
            # Triple confluencia (todos alcistas)
            if (rsi_result.get('score', 0) > 8 and
                macd_result.get('score', 0) > 10 and
                volume_result.get('score', 0) > 8):
                confluence_factors.append('triple_bullish_confluence')
            
            # Momentum breakout (técnicos + volumen alto)
            if ('bullish_crossover' in macd_signals and
                'explosive_volume' in volume_signals):
                confluence_factors.append('momentum_breakout')
            
            return confluence_factors
            
        except Exception as e:
            log.error(f"Error identificando confluencia: {e}")
            return []
    
    def _calculate_technical_score(self, rsi_result: Dict, macd_result: Dict,
                                 volume_result: Dict, confluence_factors: List) -> int:
        """
        Calcula score técnico total (0-50 puntos)
        
        Distribución:
        - RSI: 15 puntos máximo
        - MACD: 20 puntos máximo  
        - Volume: 15 puntos máximo
        - Confluencia: bonus hasta 10 puntos (máximo total 50)
        """
        try:
            score = 0
            
            # Sumar scores individuales
            score += rsi_result.get('score', 0)      # 0-15
            score += macd_result.get('score', 0)     # 0-20
            score += volume_result.get('score', 0)   # 0-15
            
            # Bonus por confluencia
            confluence_bonus = 0
            for factor in confluence_factors:
                if factor == 'triple_bullish_confluence':
                    confluence_bonus += 5
                elif factor == 'momentum_breakout':
                    confluence_bonus += 4
                elif factor in ['rsi_macd_bullish', 'volume_momentum_confluence']:
                    confluence_bonus += 2
            
            score += min(confluence_bonus, 10)  # Máximo 10 puntos bonus
            
            return min(score, TECHNICAL_MAX_SCORE)
            
        except Exception as e:
            log.error(f"Error calculando score técnico: {e}")
            return 0
