"""
MACD optimizado para crypto con configuración 3-10-16.
Más sensible y reactivo que la configuración tradicional 12-26-9.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from config.parameters import MACD_FAST, MACD_SLOW, MACD_SIGNAL
from utils.logger import log


class MACDSensitive:
    """MACD optimizado para el mercado crypto con mayor sensibilidad"""
    
    def __init__(self, fast_period: int = None, slow_period: int = None, signal_period: int = None):
        self.fast_period = fast_period or MACD_FAST
        self.slow_period = slow_period or MACD_SLOW
        self.signal_period = signal_period or MACD_SIGNAL
        
        # Cache para datos históricos
        self.price_history: Dict[str, List[float]] = {}
        self.macd_history: Dict[str, List[Dict]] = {}
        
    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calcula EMA (Exponential Moving Average)"""
        try:
            if len(prices) < period:
                return []
            
            # Convertir a pandas Series
            price_series = pd.Series(prices)
            
            # Calcular EMA usando pandas
            alpha = 2.0 / (period + 1)
            ema = price_series.ewm(alpha=alpha, adjust=False).mean()
            
            return ema.tolist()
            
        except Exception as e:
            log.error(f"Error calculando EMA: {e}")
            return []
    
    def calculate_macd(self, prices: List[float]) -> Optional[Dict]:
        """Calcula MACD Line, Signal Line y Histogram"""
        try:
            if len(prices) < max(self.slow_period, self.signal_period) + 10:
                return None
            
            # Calcular EMAs
            ema_fast = self.calculate_ema(prices, self.fast_period)
            ema_slow = self.calculate_ema(prices, self.slow_period)
            
            if not ema_fast or not ema_slow:
                return None
            
            # Alinear las listas (EMA lenta es más corta)
            min_length = min(len(ema_fast), len(ema_slow))
            ema_fast_aligned = ema_fast[-min_length:]
            ema_slow_aligned = ema_slow[-min_length:]
            
            # Calcular MACD Line
            macd_line = [fast - slow for fast, slow in zip(ema_fast_aligned, ema_slow_aligned)]
            
            # Calcular Signal Line (EMA del MACD Line)
            signal_line = self.calculate_ema(macd_line, self.signal_period)
            
            if not signal_line:
                return None
            
            # Alinear MACD Line y Signal Line
            min_length = min(len(macd_line), len(signal_line))
            macd_aligned = macd_line[-min_length:]
            signal_aligned = signal_line[-min_length:]
            
            # Calcular Histogram
            histogram = [macd - signal for macd, signal in zip(macd_aligned, signal_aligned)]
            
            return {
                'macd_line': macd_aligned[-1],
                'signal_line': signal_aligned[-1],
                'histogram': histogram[-1],
                'macd_history': macd_aligned,
                'signal_history': signal_aligned,
                'histogram_history': histogram
            }
            
        except Exception as e:
            log.error(f"Error calculando MACD: {e}")
            return None
    
    def analyze_macd_momentum(self, symbol: str, prices: List[float]) -> Dict:
        """Análisis completo de momentum basado en MACD"""
        try:
            macd_data = self.calculate_macd(prices)
            if macd_data is None:
                return {'error': 'Insufficient data for MACD calculation'}
            
            # Actualizar historial
            if symbol not in self.macd_history:
                self.macd_history[symbol] = []
            
            current_macd = {
                'macd_line': macd_data['macd_line'],
                'signal_line': macd_data['signal_line'],
                'histogram': macd_data['histogram'],
                'timestamp': datetime.now()
            }
            
            self.macd_history[symbol].append(current_macd)
            
            # Mantener últimas 100 lecturas
            if len(self.macd_history[symbol]) > 100:
                self.macd_history[symbol].pop(0)
            
            # Análisis de señales
            signals_analysis = self._analyze_macd_signals(macd_data)
            
            # Análisis de momentum
            momentum_analysis = self._analyze_momentum_direction(symbol, macd_data)
            
            # Análisis de divergencias
            divergence_analysis = self._detect_macd_divergences(symbol, prices)
            
            # Score de momentum (0-20 puntos según config)
            momentum_score = self._calculate_macd_score(signals_analysis, momentum_analysis)
            
            return {
                'macd_line': macd_data['macd_line'],
                'signal_line': macd_data['signal_line'],
                'histogram': macd_data['histogram'],
                'signals': signals_analysis,
                'momentum': momentum_analysis,
                'divergence': divergence_analysis,
                'score': momentum_score,
                'interpretation': self._interpret_macd_state(macd_data, signals_analysis),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            log.error(f"Error en análisis MACD para {symbol}: {e}")
            return {'error': str(e)}
    
    def _analyze_macd_signals(self, macd_data: Dict) -> Dict:
        """Analiza las señales principales del MACD"""
        try:
            macd_line = macd_data['macd_line']
            signal_line = macd_data['signal_line']
            histogram = macd_data['histogram']
            
            # Detectar cruces
            crossover_signal = 'NONE'
            if len(macd_data['macd_history']) >= 2 and len(macd_data['signal_history']) >= 2:
                prev_macd = macd_data['macd_history'][-2]
                prev_signal = macd_data['signal_history'][-2]
                
                # Cruce alcista
                if prev_macd <= prev_signal and macd_line > signal_line:
                    crossover_signal = 'BULLISH_CROSSOVER'
                # Cruce bajista
                elif prev_macd >= prev_signal and macd_line < signal_line:
                    crossover_signal = 'BEARISH_CROSSOVER'
            
            # Analizar posición relativa al cero
            zero_line_position = 'ABOVE' if macd_line > 0 else 'BELOW'
            
            # Analizar tendencia del histogram
            histogram_trend = 'NEUTRAL'
            if len(macd_data['histogram_history']) >= 3:
                recent_hist = macd_data['histogram_history'][-3:]
                if all(recent_hist[i] > recent_hist[i-1] for i in range(1, len(recent_hist))):
                    histogram_trend = 'INCREASING'
                elif all(recent_hist[i] < recent_hist[i-1] for i in range(1, len(recent_hist))):
                    histogram_trend = 'DECREASING'
            
            # Analizar fuerza de la señal
            signal_strength = self._calculate_signal_strength(macd_data)
            
            return {
                'crossover': crossover_signal,
                'zero_line_position': zero_line_position,
                'histogram_trend': histogram_trend,
                'signal_strength': signal_strength,
                'distance_from_signal': abs(macd_line - signal_line)
            }
            
        except Exception as e:
            log.error(f"Error analizando señales MACD: {e}")
            return {}
    
    def _analyze_momentum_direction(self, symbol: str, macd_data: Dict) -> Dict:
        """Analiza la dirección y fuerza del momentum"""
        try:
            if symbol not in self.macd_history or len(self.macd_history[symbol]) < 5:
                return {'direction': 'NEUTRAL', 'strength': 0, 'acceleration': 'NONE'}
            
            # Obtener historial reciente
            recent_macd = [entry['macd_line'] for entry in self.macd_history[symbol][-5:]]
            recent_histogram = [entry['histogram'] for entry in self.macd_history[symbol][-5:]]
            
            # Calcular tendencia del MACD
            macd_changes = [recent_macd[i] - recent_macd[i-1] for i in range(1, len(recent_macd))]
            avg_macd_change = np.mean(macd_changes)
            
            # Calcular tendencia del histogram
            hist_changes = [recent_histogram[i] - recent_histogram[i-1] for i in range(1, len(recent_histogram))]
            avg_hist_change = np.mean(hist_changes)
            
            # Determinar dirección
            if avg_macd_change > 0 and avg_hist_change > 0:
                direction = 'BULLISH'
                strength = min((abs(avg_macd_change) + abs(avg_hist_change)) / 2, 1.0)
            elif avg_macd_change < 0 and avg_hist_change < 0:
                direction = 'BEARISH'
                strength = min((abs(avg_macd_change) + abs(avg_hist_change)) / 2, 1.0)
            else:
                direction = 'NEUTRAL'
                strength = 0
            
            # Detectar aceleración
            acceleration = 'NONE'
            if len(macd_changes) >= 2:
                recent_change = np.mean(macd_changes[-2:])
                older_change = np.mean(macd_changes[:-2])
                
                if direction == 'BULLISH' and recent_change > older_change * 1.2:
                    acceleration = 'ACCELERATING'
                elif direction == 'BEARISH' and recent_change < older_change * 1.2:
                    acceleration = 'ACCELERATING'
            
            return {
                'direction': direction,
                'strength': strength,
                'acceleration': acceleration,
                'macd_velocity': avg_macd_change,
                'histogram_velocity': avg_hist_change
            }
            
        except Exception as e:
            log.error(f"Error analizando momentum MACD: {e}")
            return {'direction': 'NEUTRAL', 'strength': 0}
    
    def _detect_macd_divergences(self, symbol: str, prices: List[float]) -> Dict:
        """Detecta divergencias entre precio y MACD"""
        try:
            if (symbol not in self.macd_history or 
                len(self.macd_history[symbol]) < 10 or 
                len(prices) < 10):
                return {'type': 'NONE', 'strength': 0}
            
            # Obtener datos recientes
            recent_prices = prices[-10:]
            recent_macd = [entry['macd_line'] for entry in self.macd_history[symbol][-10:]]
            
            # Encontrar extremos
            price_peaks = self._find_peaks(recent_prices)
            price_troughs = self._find_troughs(recent_prices)
            macd_peaks = self._find_peaks(recent_macd)
            macd_troughs = self._find_troughs(recent_macd)
            
            # Detectar divergencia alcista
            bullish_divergence = False
            if len(price_troughs) >= 2 and len(macd_troughs) >= 2:
                last_price_trough = recent_prices[price_troughs[-1]]
                prev_price_trough = recent_prices[price_troughs[-2]]
                last_macd_trough = recent_macd[macd_troughs[-1]]
                prev_macd_trough = recent_macd[macd_troughs[-2]]
                
                if last_price_trough < prev_price_trough and last_macd_trough > prev_macd_trough:
                    bullish_divergence = True
            
            # Detectar divergencia bajista
            bearish_divergence = False
            if len(price_peaks) >= 2 and len(macd_peaks) >= 2:
                last_price_peak = recent_prices[price_peaks[-1]]
                prev_price_peak = recent_prices[price_peaks[-2]]
                last_macd_peak = recent_macd[macd_peaks[-1]]
                prev_macd_peak = recent_macd[macd_peaks[-2]]
                
                if last_price_peak > prev_price_peak and last_macd_peak < prev_macd_peak:
                    bearish_divergence = True
            
            if bullish_divergence:
                return {'type': 'BULLISH', 'strength': 0.8}
            elif bearish_divergence:
                return {'type': 'BEARISH', 'strength': 0.8}
            else:
                return {'type': 'NONE', 'strength': 0}
                
        except Exception as e:
            log.error(f"Error detectando divergencias MACD: {e}")
            return {'type': 'NONE', 'strength': 0}
    
    def _find_peaks(self, values: List[float]) -> List[int]:
        """Encuentra picos locales"""
        peaks = []
        for i in range(1, len(values) - 1):
            if values[i] > values[i-1] and values[i] > values[i+1]:
                peaks.append(i)
        return peaks
    
    def _find_troughs(self, values: List[float]) -> List[int]:
        """Encuentra valles locales"""
        troughs = []
        for i in range(1, len(values) - 1):
            if values[i] < values[i-1] and values[i] < values[i+1]:
                troughs.append(i)
        return troughs
    
    def _calculate_signal_strength(self, macd_data: Dict) -> float:
        """Calcula la fuerza de la señal MACD (0-1)"""
        try:
            macd_line = macd_data['macd_line']
            signal_line = macd_data['signal_line']
            histogram = macd_data['histogram']
            
            # Fuerza basada en separación
            separation = abs(macd_line - signal_line)
            
            # Fuerza basada en histogram
            histogram_strength = abs(histogram)
            
            # Normalizar (valores típicos en crypto)
            normalized_separation = min(separation / 0.01, 1.0)  # 0.01 como referencia
            normalized_histogram = min(histogram_strength / 0.005, 1.0)  # 0.005 como referencia
            
            return (normalized_separation + normalized_histogram) / 2
            
        except Exception as e:
            log.error(f"Error calculando fuerza de señal: {e}")
            return 0
    
    def _calculate_macd_score(self, signals_analysis: Dict, momentum_analysis: Dict) -> int:
        """Calcula score de momentum MACD (0-20 puntos)"""
        try:
            score = 0
            
            # Puntos por crossover alcista (0-8 puntos)
            crossover = signals_analysis.get('crossover', 'NONE')
            if crossover == 'BULLISH_CROSSOVER':
                score += 8
            elif signals_analysis.get('zero_line_position') == 'ABOVE':
                score += 4  # MACD sobre cero es positivo
            
            # Puntos por tendencia del histogram (0-5 puntos)
            histogram_trend = signals_analysis.get('histogram_trend', 'NEUTRAL')
            if histogram_trend == 'INCREASING':
                score += 5
            elif histogram_trend == 'DECREASING':
                score -= 2  # Penalizar histogram decreciente
            
            # Puntos por momentum (0-5 puntos)
            direction = momentum_analysis.get('direction', 'NEUTRAL')
            strength = momentum_analysis.get('strength', 0)
            if direction == 'BULLISH':
                score += int(strength * 5)
            
            # Bonus por aceleración (0-2 puntos)
            acceleration = momentum_analysis.get('acceleration', 'NONE')
            if acceleration == 'ACCELERATING' and direction == 'BULLISH':
                score += 2
            
            return max(0, min(score, 20))  # 0-20 puntos máximo
            
        except Exception as e:
            log.error(f"Error calculando score MACD: {e}")
            return 0
    
    def _interpret_macd_state(self, macd_data: Dict, signals_analysis: Dict) -> str:
        """Interpreta el estado actual del MACD"""
        try:
            crossover = signals_analysis.get('crossover', 'NONE')
            zero_position = signals_analysis.get('zero_line_position', 'BELOW')
            histogram_trend = signals_analysis.get('histogram_trend', 'NEUTRAL')
            
            if crossover == 'BULLISH_CROSSOVER':
                if zero_position == 'ABOVE':
                    return "Fuerte señal alcista - MACD cruzó signal line por encima de cero"
                else:
                    return "Señal alcista emergente - MACD cruzó signal line, esperando confirmación"
            
            elif crossover == 'BEARISH_CROSSOVER':
                return "Señal bajista - MACD cruzó por debajo de signal line"
            
            elif zero_position == 'ABOVE' and histogram_trend == 'INCREASING':
                return "Momentum alcista creciente - MACD sobre cero con histogram expansivo"
            
            elif zero_position == 'ABOVE':
                return "Tendencia alcista establecida - MACD sobre cero"
            
            elif histogram_trend == 'INCREASING':
                return "Momentum building - Histogram incrementando"
            
            else:
                return "Momentum neutral - Sin señales claras"
                
        except Exception as e:
            log.error(f"Error interpretando estado MACD: {e}")
            return "Error en interpretación"
    
    def get_multi_timeframe_macd(self, symbol_data: Dict) -> Dict:
        """Calcula MACD en múltiples timeframes para confluencia"""
        try:
            results = {}
            
            timeframes = ['5m', '15m', '1h']
            for tf in timeframes:
                if 'klines' in symbol_data and tf in symbol_data['klines']:
                    klines = symbol_data['klines'][tf]
                    required_periods = max(self.slow_period, self.signal_period) + 10
                    
                    if len(klines) >= required_periods:
                        prices = [float(k['close']) for k in klines]
                        macd_data = self.calculate_macd(prices)
                        
                        if macd_data is not None:
                            results[tf] = {
                                'macd_line': macd_data['macd_line'],
                                'signal_line': macd_data['signal_line'],
                                'histogram': macd_data['histogram'],
                                'bullish': macd_data['macd_line'] > macd_data['signal_line']
                            }
            
            # Analizar confluencia
            confluence_score = self._analyze_macd_confluence(results)
            
            return {
                'timeframes': results,
                'confluence_score': confluence_score,
                'confluence_signal': confluence_score > 0.6
            }
            
        except Exception as e:
            log.error(f"Error en MACD multi-timeframe: {e}")
            return {}
    
    def _analyze_macd_confluence(self, timeframe_results: Dict) -> float:
        """Analiza confluencia entre timeframes"""
        try:
            if not timeframe_results:
                return 0
            
            bullish_signals = 0
            total_signals = 0
            
            for tf, data in timeframe_results.items():
                total_signals += 1
                if data['bullish']:
                    bullish_signals += 1
            
            return bullish_signals / total_signals if total_signals > 0 else 0
            
        except Exception as e:
            log.error(f"Error analizando confluencia MACD: {e}")
            return 0
