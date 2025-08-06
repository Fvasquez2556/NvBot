"""
RSI optimizado para criptomonedas con umbrales 25/75.
Incluye detección de divergencias y análisis multi-timeframe.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from config.parameters import RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT
from utils.logger import log


class RSIOptimizer:
    """RSI optimizado específicamente para el mercado crypto"""
    
    def __init__(self, period: int = None):
        self.period = period or RSI_PERIOD
        self.oversold_threshold = RSI_OVERSOLD
        self.overbought_threshold = RSI_OVERBOUGHT
        
        # Cache para datos históricos por símbolo
        self.price_history: Dict[str, List[float]] = {}
        self.rsi_history: Dict[str, List[float]] = {}
        
    def calculate_rsi(self, prices: List[float]) -> Optional[float]:
        """Calcula RSI usando método optimizado"""
        try:
            if len(prices) < self.period + 1:
                return None
            
            # Convertir a pandas Series para cálculo eficiente
            price_series = pd.Series(prices)
            
            # Calcular cambios de precio
            delta = price_series.diff()
            
            # Separar ganancias y pérdidas
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            # Calcular promedios móviles exponenciales (método Wilder)
            alpha = 1.0 / self.period
            avg_gains = gains.ewm(alpha=alpha, adjust=False).mean()
            avg_losses = losses.ewm(alpha=alpha, adjust=False).mean()
            
            # Calcular RS y RSI
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1])
            
        except Exception as e:
            log.error(f"Error calculando RSI: {e}")
            return None
    
    def analyze_rsi_momentum(self, symbol: str, prices: List[float]) -> Dict:
        """Análisis completo de momentum basado en RSI"""
        try:
            current_rsi = self.calculate_rsi(prices)
            if current_rsi is None:
                return {'error': 'Insufficient data for RSI calculation'}
            
            # Actualizar historial
            if symbol not in self.rsi_history:
                self.rsi_history[symbol] = []
            self.rsi_history[symbol].append(current_rsi)
            
            # Mantener últimas 100 lecturas
            if len(self.rsi_history[symbol]) > 100:
                self.rsi_history[symbol].pop(0)
            
            # Análisis de momentum
            momentum_analysis = self._analyze_momentum_patterns(symbol, current_rsi)
            
            # Detección de divergencias
            divergence_analysis = self._detect_divergences(symbol, prices)
            
            # Clasificación de zona
            zone_analysis = self._classify_rsi_zone(current_rsi)
            
            # Score de momentum (0-25 puntos según config)
            momentum_score = self._calculate_momentum_score(momentum_analysis, zone_analysis)
            
            return {
                'current_rsi': current_rsi,
                'zone': zone_analysis['zone'],
                'momentum_direction': momentum_analysis['direction'],
                'momentum_strength': momentum_analysis['strength'],
                'divergence': divergence_analysis,
                'score': momentum_score,
                'signals': self._generate_signals(current_rsi, momentum_analysis),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            log.error(f"Error en análisis RSI para {symbol}: {e}")
            return {'error': str(e)}
    
    def _analyze_momentum_patterns(self, symbol: str, current_rsi: float) -> Dict:
        """Analiza patrones de momentum en el RSI"""
        try:
            if symbol not in self.rsi_history or len(self.rsi_history[symbol]) < 5:
                return {'direction': 'NEUTRAL', 'strength': 0}
            
            rsi_history = self.rsi_history[symbol]
            recent_rsi = rsi_history[-5:]  # Últimas 5 lecturas
            
            # Calcular tendencia
            rsi_changes = [recent_rsi[i] - recent_rsi[i-1] for i in range(1, len(recent_rsi))]
            avg_change = np.mean(rsi_changes)
            
            # Determinar dirección
            if avg_change > 2:
                direction = 'ALCISTA'
                strength = min(abs(avg_change) / 5, 1.0)  # Normalizar 0-1
            elif avg_change < -2:
                direction = 'BAJISTA'
                strength = min(abs(avg_change) / 5, 1.0)
            else:
                direction = 'NEUTRAL'
                strength = 0
            
            # Detectar aceleración
            acceleration = 'NONE'
            if len(rsi_changes) >= 3:
                recent_change = np.mean(rsi_changes[-2:])
                older_change = np.mean(rsi_changes[:-2])
                
                if direction == 'ALCISTA' and recent_change > older_change:
                    acceleration = 'ACCELERATING'
                elif direction == 'BAJISTA' and recent_change < older_change:
                    acceleration = 'ACCELERATING'
            
            return {
                'direction': direction,
                'strength': strength,
                'acceleration': acceleration,
                'avg_change': avg_change
            }
            
        except Exception as e:
            log.error(f"Error analizando patrones RSI: {e}")
            return {'direction': 'NEUTRAL', 'strength': 0}
    
    def _detect_divergences(self, symbol: str, prices: List[float]) -> Dict:
        """Detecta divergencias entre precio y RSI"""
        try:
            if (symbol not in self.rsi_history or 
                len(self.rsi_history[symbol]) < 10 or 
                len(prices) < 10):
                return {'type': 'NONE', 'strength': 0}
            
            rsi_values = self.rsi_history[symbol][-10:]
            price_values = prices[-10:]
            
            # Encontrar extremos locales
            price_peaks = self._find_peaks(price_values)
            price_troughs = self._find_troughs(price_values)
            
            rsi_peaks = self._find_peaks(rsi_values)
            rsi_troughs = self._find_troughs(rsi_values)
            
            # Detectar divergencia alcista (precio hace mínimos más bajos, RSI no)
            bullish_divergence = False
            if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
                last_price_trough = price_values[price_troughs[-1]]
                prev_price_trough = price_values[price_troughs[-2]]
                
                last_rsi_trough = rsi_values[rsi_troughs[-1]]
                prev_rsi_trough = rsi_values[rsi_troughs[-2]]
                
                if last_price_trough < prev_price_trough and last_rsi_trough > prev_rsi_trough:
                    bullish_divergence = True
            
            # Detectar divergencia bajista (precio hace máximos más altos, RSI no)
            bearish_divergence = False
            if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
                last_price_peak = price_values[price_peaks[-1]]
                prev_price_peak = price_values[price_peaks[-2]]
                
                last_rsi_peak = rsi_values[rsi_peaks[-1]]
                prev_rsi_peak = rsi_values[rsi_peaks[-2]]
                
                if last_price_peak > prev_price_peak and last_rsi_peak < prev_rsi_peak:
                    bearish_divergence = True
            
            # Determinar tipo y fuerza
            if bullish_divergence:
                return {'type': 'BULLISH', 'strength': 0.8}
            elif bearish_divergence:
                return {'type': 'BEARISH', 'strength': 0.8}
            else:
                return {'type': 'NONE', 'strength': 0}
                
        except Exception as e:
            log.error(f"Error detectando divergencias: {e}")
            return {'type': 'NONE', 'strength': 0}
    
    def _find_peaks(self, values: List[float]) -> List[int]:
        """Encuentra picos locales en una serie"""
        peaks = []
        for i in range(1, len(values) - 1):
            if values[i] > values[i-1] and values[i] > values[i+1]:
                peaks.append(i)
        return peaks
    
    def _find_troughs(self, values: List[float]) -> List[int]:
        """Encuentra valles locales en una serie"""
        troughs = []
        for i in range(1, len(values) - 1):
            if values[i] < values[i-1] and values[i] < values[i+1]:
                troughs.append(i)
        return troughs
    
    def _classify_rsi_zone(self, rsi: float) -> Dict:
        """Clasifica la zona del RSI (optimizada para crypto)"""
        if rsi <= self.oversold_threshold:
            return {
                'zone': 'OVERSOLD_EXTREME',
                'description': 'Sobreventa extrema - Potencial rebote fuerte',
                'momentum_potential': 0.9
            }
        elif rsi <= 35:
            return {
                'zone': 'OVERSOLD',
                'description': 'Sobreventa - Posible rebote',
                'momentum_potential': 0.7
            }
        elif rsi <= 45:
            return {
                'zone': 'ACCUMULATION',
                'description': 'Zona de acumulación - Momentum building',
                'momentum_potential': 0.6
            }
        elif rsi <= 55:
            return {
                'zone': 'NEUTRAL',
                'description': 'Zona neutral',
                'momentum_potential': 0.3
            }
        elif rsi <= 70:
            return {
                'zone': 'BULLISH_MOMENTUM',
                'description': 'Momentum alcista confirmado',
                'momentum_potential': 0.8
            }
        elif rsi <= self.overbought_threshold:
            return {
                'zone': 'OVERBOUGHT',
                'description': 'Sobrecompra - Momentum puede continuar en crypto',
                'momentum_potential': 0.6
            }
        else:
            return {
                'zone': 'OVERBOUGHT_EXTREME',
                'description': 'Sobrecompra extrema - Evaluar continuación',
                'momentum_potential': 0.4
            }
    
    def _calculate_momentum_score(self, momentum_analysis: Dict, zone_analysis: Dict) -> int:
        """Calcula score de momentum (0-25 puntos)"""
        try:
            score = 0
            
            # Puntos por zona favorable (0-10 puntos)
            momentum_potential = zone_analysis.get('momentum_potential', 0)
            score += int(momentum_potential * 10)
            
            # Puntos por dirección del momentum (0-8 puntos)
            direction = momentum_analysis.get('direction', 'NEUTRAL')
            if direction == 'ALCISTA':
                strength = momentum_analysis.get('strength', 0)
                score += int(strength * 8)
            
            # Puntos por aceleración (0-5 puntos)
            acceleration = momentum_analysis.get('acceleration', 'NONE')
            if acceleration == 'ACCELERATING':
                score += 5
            
            # Bonus por momentum extremo (0-2 puntos)
            avg_change = abs(momentum_analysis.get('avg_change', 0))
            if avg_change > 5:  # Cambio muy fuerte
                score += 2
            
            return min(score, 25)  # Cap en 25 puntos máximo
            
        except Exception as e:
            log.error(f"Error calculando score RSI: {e}")
            return 0
    
    def _generate_signals(self, current_rsi: float, momentum_analysis: Dict) -> List[str]:
        """Genera señales específicas basadas en RSI"""
        signals = []
        
        # Señales por zona
        if current_rsi <= self.oversold_threshold:
            signals.append("RSI_OVERSOLD_EXTREME")
        elif current_rsi >= self.overbought_threshold:
            signals.append("RSI_OVERBOUGHT")
        
        # Señales por momentum
        direction = momentum_analysis.get('direction', 'NEUTRAL')
        strength = momentum_analysis.get('strength', 0)
        
        if direction == 'ALCISTA' and strength > 0.7:
            signals.append("RSI_STRONG_BULLISH_MOMENTUM")
        elif direction == 'ALCISTA' and strength > 0.4:
            signals.append("RSI_BULLISH_MOMENTUM")
        
        # Señales por aceleración
        acceleration = momentum_analysis.get('acceleration', 'NONE')
        if acceleration == 'ACCELERATING' and direction == 'ALCISTA':
            signals.append("RSI_MOMENTUM_ACCELERATING")
        
        return signals
    
    def get_multi_timeframe_rsi(self, symbol_data: Dict) -> Dict:
        """Calcula RSI en múltiples timeframes para confluencia"""
        try:
            results = {}
            
            timeframes = ['1m', '5m', '15m']
            for tf in timeframes:
                if 'klines' in symbol_data and tf in symbol_data['klines']:
                    klines = symbol_data['klines'][tf]
                    if len(klines) >= self.period + 1:
                        prices = [float(k['close']) for k in klines]
                        rsi = self.calculate_rsi(prices)
                        if rsi is not None:
                            results[tf] = {
                                'rsi': rsi,
                                'zone': self._classify_rsi_zone(rsi)['zone']
                            }
            
            # Analizar confluencia
            confluence_score = self._analyze_timeframe_confluence(results)
            
            return {
                'timeframes': results,
                'confluence_score': confluence_score,
                'confluence_signal': confluence_score > 0.7
            }
            
        except Exception as e:
            log.error(f"Error en RSI multi-timeframe: {e}")
            return {}
    
    def _analyze_timeframe_confluence(self, timeframe_results: Dict) -> float:
        """Analiza confluencia entre timeframes"""
        try:
            if not timeframe_results:
                return 0
            
            bullish_signals = 0
            total_signals = 0
            
            for tf, data in timeframe_results.items():
                zone = data['zone']
                total_signals += 1
                
                if zone in ['OVERSOLD_EXTREME', 'OVERSOLD', 'ACCUMULATION', 'BULLISH_MOMENTUM']:
                    bullish_signals += 1
            
            return bullish_signals / total_signals if total_signals > 0 else 0
            
        except Exception as e:
            log.error(f"Error analizando confluencia: {e}")
            return 0
