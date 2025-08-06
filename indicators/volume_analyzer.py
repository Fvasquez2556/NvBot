"""
Análisis avanzado de volumen y detección de spikes para identificar momentum real.
Filtros de volumen optimizados para crypto: 200-500% sobre promedio.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from config.trading_config import config
from utils.logger import log


class VolumeAnalyzer:
    """Analizador avanzado de volumen para detección de momentum"""
    
    def __init__(self):
        self.volume_period = config.technical.volume_average_period
        self.spike_threshold = config.technical.volume_spike_threshold
        self.strong_threshold = config.technical.volume_spike_strong
        self.explosive_threshold = config.technical.volume_spike_explosive
        
        # Cache para historial de volúmenes
        self.volume_history: Dict[str, List[Dict]] = {}
        
    def analyze_volume_momentum(self, symbol: str, volume_data: List[Dict]) -> Dict:
        """Análisis completo de momentum basado en volumen"""
        try:
            if len(volume_data) < self.volume_period:
                return {'error': 'Insufficient volume data'}
            
            # Extraer volúmenes y precios
            volumes = [float(d['volume']) for d in volume_data]
            quote_volumes = [float(d.get('quote_volume', d.get('volume', 0))) for d in volume_data]
            prices = [float(d['close']) for d in volume_data]
            
            current_volume = volumes[-1]
            current_quote_volume = quote_volumes[-1]
            current_price = prices[-1]
            
            # Calcular promedio de volumen
            avg_volume = self._calculate_volume_average(volumes)
            avg_quote_volume = self._calculate_volume_average(quote_volumes)
            
            # Detectar spike de volumen
            spike_analysis = self._detect_volume_spike(current_volume, avg_volume, current_quote_volume, avg_quote_volume)
            
            # Analizar relación volumen-precio
            vpr_analysis = self._analyze_volume_price_relationship(volume_data)
            
            # Analizar distribución de volumen
            distribution_analysis = self._analyze_volume_distribution(volumes)
            
            # Detectar acumulación/distribución
            accumulation_analysis = self._detect_accumulation_distribution(volume_data)
            
            # Calcular score de volumen (0-25 puntos)
            volume_score = self._calculate_volume_score(spike_analysis, vpr_analysis, accumulation_analysis)
            
            # Actualizar historial
            self._update_volume_history(symbol, {
                'volume': current_volume,
                'quote_volume': current_quote_volume,
                'price': current_price,
                'volume_ratio': spike_analysis['volume_ratio'],
                'timestamp': datetime.now()
            })
            
            return {
                'current_volume': current_volume,
                'average_volume': avg_volume,
                'volume_ratio': spike_analysis['volume_ratio'],
                'spike_level': spike_analysis['level'],
                'spike_classification': spike_analysis['classification'],
                'volume_price_relationship': vpr_analysis,
                'distribution': distribution_analysis,
                'accumulation': accumulation_analysis,
                'score': volume_score,
                'signals': self._generate_volume_signals(spike_analysis, vpr_analysis),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            log.error(f"Error en análisis de volumen para {symbol}: {e}")
            return {'error': str(e)}
    
    def _calculate_volume_average(self, volumes: List[float]) -> float:
        """Calcula el promedio de volumen usando EMA para mayor sensibilidad"""
        try:
            if len(volumes) < self.volume_period:
                return np.mean(volumes)
            
            # Usar EMA para promedio más sensible a cambios recientes
            volumes_series = pd.Series(volumes[-self.volume_period:])
            alpha = 2.0 / (self.volume_period + 1)
            ema_volume = volumes_series.ewm(alpha=alpha, adjust=False).mean()
            
            return float(ema_volume.iloc[-1])
            
        except Exception as e:
            log.error(f"Error calculando promedio de volumen: {e}")
            return np.mean(volumes[-self.volume_period:]) if volumes else 0
    
    def _detect_volume_spike(self, current_volume: float, avg_volume: float, 
                           current_quote_volume: float, avg_quote_volume: float) -> Dict:
        """Detecta spikes de volumen y los clasifica"""
        try:
            # Calcular ratios
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            quote_volume_ratio = current_quote_volume / avg_quote_volume if avg_quote_volume > 0 else 1
            
            # Usar el ratio más alto para clasificación
            max_ratio = max(volume_ratio, quote_volume_ratio)
            
            # Clasificar el spike
            if max_ratio >= self.explosive_threshold:
                level = 'EXPLOSIVE'
                classification = 'Volumen explosivo - Movimiento institucional'
            elif max_ratio >= self.strong_threshold:
                level = 'STRONG'
                classification = 'Volumen fuerte - Alta actividad'
            elif max_ratio >= self.spike_threshold:
                level = 'MODERATE'
                classification = 'Volumen moderado - Interés creciente'
            else:
                level = 'NORMAL'
                classification = 'Volumen normal'
            
            return {
                'volume_ratio': volume_ratio,
                'quote_volume_ratio': quote_volume_ratio,
                'max_ratio': max_ratio,
                'level': level,
                'classification': classification
            }
            
        except Exception as e:
            log.error(f"Error detectando spike de volumen: {e}")
            return {'volume_ratio': 1, 'level': 'NORMAL', 'classification': 'Error en cálculo'}
    
    def _analyze_volume_price_relationship(self, volume_data: List[Dict]) -> Dict:
        """Analiza la relación entre volumen y movimiento de precio"""
        try:
            if len(volume_data) < 5:
                return {'strength': 0, 'direction': 'NEUTRAL'}
            
            # Obtener datos recientes
            recent_data = volume_data[-5:]
            
            # Calcular cambios de precio y volumen
            price_changes = []
            volume_changes = []
            
            for i in range(1, len(recent_data)):
                price_change = (float(recent_data[i]['close']) - float(recent_data[i-1]['close'])) / float(recent_data[i-1]['close'])
                volume_change = (float(recent_data[i]['volume']) - float(recent_data[i-1]['volume'])) / float(recent_data[i-1]['volume'])
                
                price_changes.append(price_change)
                volume_changes.append(volume_change)
            
            # Calcular correlación precio-volumen
            if len(price_changes) > 0:
                correlation = np.corrcoef(price_changes, volume_changes)[0, 1]
                if np.isnan(correlation):
                    correlation = 0
            else:
                correlation = 0
            
            # Analizar la última relación
            last_price_change = price_changes[-1] if price_changes else 0
            last_volume_change = volume_changes[-1] if volume_changes else 0
            
            # Determinar confirmación
            if last_price_change > 0.01 and last_volume_change > 0.5:  # Precio sube +1% con volumen +50%
                confirmation = 'STRONG_BULLISH'
                strength = min(abs(correlation), 1.0)
            elif last_price_change > 0.005 and last_volume_change > 0.2:  # Precio sube +0.5% con volumen +20%
                confirmation = 'MODERATE_BULLISH'
                strength = min(abs(correlation) * 0.7, 1.0)
            elif last_price_change < -0.01 and last_volume_change > 0.5:  # Precio baja con alto volumen
                confirmation = 'BEARISH_VOLUME'
                strength = min(abs(correlation) * 0.8, 1.0)
            else:
                confirmation = 'NEUTRAL'
                strength = 0
            
            return {
                'correlation': correlation,
                'confirmation': confirmation,
                'strength': strength,
                'price_change': last_price_change,
                'volume_change': last_volume_change
            }
            
        except Exception as e:
            log.error(f"Error analizando relación volumen-precio: {e}")
            return {'strength': 0, 'direction': 'NEUTRAL'}
    
    def _analyze_volume_distribution(self, volumes: List[float]) -> Dict:
        """Analiza la distribución del volumen para detectar patrones"""
        try:
            if len(volumes) < 10:
                return {'pattern': 'INSUFFICIENT_DATA'}
            
            recent_volumes = volumes[-10:]
            
            # Calcular estadísticas
            mean_volume = np.mean(recent_volumes)
            std_volume = np.std(recent_volumes)
            
            # Detectar tendencias
            first_half = recent_volumes[:5]
            second_half = recent_volumes[5:]
            
            first_avg = np.mean(first_half)
            second_avg = np.mean(second_half)
            
            # Clasificar patrón
            if second_avg > first_avg * 1.5:
                pattern = 'INCREASING'
                description = 'Volumen creciente - Interés aumentando'
            elif second_avg < first_avg * 0.7:
                pattern = 'DECREASING'
                description = 'Volumen decreciente - Interés disminuyendo'
            elif std_volume > mean_volume * 0.5:
                pattern = 'VOLATILE'
                description = 'Volumen volátil - Actividad irregular'
            else:
                pattern = 'STABLE'
                description = 'Volumen estable'
            
            return {
                'pattern': pattern,
                'description': description,
                'mean_volume': mean_volume,
                'std_volume': std_volume,
                'volatility_ratio': std_volume / mean_volume if mean_volume > 0 else 0
            }
            
        except Exception as e:
            log.error(f"Error analizando distribución de volumen: {e}")
            return {'pattern': 'ERROR'}
    
    def _detect_accumulation_distribution(self, volume_data: List[Dict]) -> Dict:
        """Detecta patrones de acumulación o distribución"""
        try:
            if len(volume_data) < 10:
                return {'pattern': 'INSUFFICIENT_DATA', 'strength': 0}
            
            # Analizar últimas 10 velas
            recent_data = volume_data[-10:]
            
            accumulation_score = 0
            distribution_score = 0
            
            for data in recent_data:
                price_high = float(data['high'])
                price_low = float(data['low'])
                price_close = float(data['close'])
                price_open = float(data['open'])
                volume = float(data['volume'])
                
                # Calcular posición del cierre en el rango
                if price_high != price_low:
                    close_position = (price_close - price_low) / (price_high - price_low)
                else:
                    close_position = 0.5
                
                # Normalizar volumen (respecto al promedio)
                avg_volume = np.mean([float(d['volume']) for d in recent_data])
                volume_weight = volume / avg_volume if avg_volume > 0 else 1
                
                # Acumulación: cierre alto + volumen alto
                if close_position > 0.6 and volume_weight > 1.2:
                    accumulation_score += volume_weight * close_position
                
                # Distribución: cierre bajo + volumen alto
                elif close_position < 0.4 and volume_weight > 1.2:
                    distribution_score += volume_weight * (1 - close_position)
            
            # Determinar patrón dominante
            if accumulation_score > distribution_score * 1.5:
                pattern = 'ACCUMULATION'
                strength = min(accumulation_score / 10, 1.0)
                description = 'Patrón de acumulación - Compras institucionales'
            elif distribution_score > accumulation_score * 1.5:
                pattern = 'DISTRIBUTION'
                strength = min(distribution_score / 10, 1.0)
                description = 'Patrón de distribución - Ventas institucionales'
            else:
                pattern = 'NEUTRAL'
                strength = 0
                description = 'Sin patrón claro'
            
            return {
                'pattern': pattern,
                'strength': strength,
                'description': description,
                'accumulation_score': accumulation_score,
                'distribution_score': distribution_score
            }
            
        except Exception as e:
            log.error(f"Error detectando acumulación/distribución: {e}")
            return {'pattern': 'ERROR', 'strength': 0}
    
    def _calculate_volume_score(self, spike_analysis: Dict, vpr_analysis: Dict, accumulation_analysis: Dict) -> int:
        """Calcula score de volumen (0-25 puntos)"""
        try:
            score = 0
            
            # Puntos por spike de volumen (0-15 puntos)
            spike_level = spike_analysis.get('level', 'NORMAL')
            if spike_level == 'EXPLOSIVE':
                score += 15
            elif spike_level == 'STRONG':
                score += 12
            elif spike_level == 'MODERATE':
                score += 8
            
            # Puntos por relación volumen-precio (0-7 puntos)
            vpr_confirmation = vpr_analysis.get('confirmation', 'NEUTRAL')
            if vpr_confirmation == 'STRONG_BULLISH':
                score += 7
            elif vpr_confirmation == 'MODERATE_BULLISH':
                score += 5
            elif vpr_confirmation == 'BEARISH_VOLUME':
                score -= 3  # Penalizar volumen bajista
            
            # Puntos por acumulación (0-3 puntos)
            accumulation_pattern = accumulation_analysis.get('pattern', 'NEUTRAL')
            accumulation_strength = accumulation_analysis.get('strength', 0)
            if accumulation_pattern == 'ACCUMULATION':
                score += int(accumulation_strength * 3)
            elif accumulation_pattern == 'DISTRIBUTION':
                score -= 2  # Penalizar distribución
            
            return max(0, min(score, config.scoring.volume_max_points))  # 0-25
            
        except Exception as e:
            log.error(f"Error calculando score de volumen: {e}")
            return 0
    
    def _generate_volume_signals(self, spike_analysis: Dict, vpr_analysis: Dict) -> List[str]:
        """Genera señales específicas basadas en volumen"""
        signals = []
        
        # Señales por spike
        spike_level = spike_analysis.get('level', 'NORMAL')
        if spike_level == 'EXPLOSIVE':
            signals.append("VOLUME_EXPLOSIVE_SPIKE")
        elif spike_level == 'STRONG':
            signals.append("VOLUME_STRONG_SPIKE")
        elif spike_level == 'MODERATE':
            signals.append("VOLUME_MODERATE_SPIKE")
        
        # Señales por relación volumen-precio
        vpr_confirmation = vpr_analysis.get('confirmation', 'NEUTRAL')
        if vpr_confirmation == 'STRONG_BULLISH':
            signals.append("VOLUME_PRICE_CONFIRMATION_STRONG")
        elif vpr_confirmation == 'MODERATE_BULLISH':
            signals.append("VOLUME_PRICE_CONFIRMATION_MODERATE")
        
        return signals
    
    def _update_volume_history(self, symbol: str, volume_entry: Dict):
        """Actualiza el historial de volumen para un símbolo"""
        try:
            if symbol not in self.volume_history:
                self.volume_history[symbol] = []
            
            self.volume_history[symbol].append(volume_entry)
            
            # Mantener últimas 100 entradas
            if len(self.volume_history[symbol]) > 100:
                self.volume_history[symbol].pop(0)
                
        except Exception as e:
            log.error(f"Error actualizando historial de volumen: {e}")
    
    def get_volume_trend_analysis(self, symbol: str, timeframe_hours: int = 24) -> Dict:
        """Analiza tendencias de volumen en un período específico"""
        try:
            if symbol not in self.volume_history:
                return {'error': 'No volume history available'}
            
            # Filtrar por timeframe
            cutoff_time = datetime.now() - timedelta(hours=timeframe_hours)
            recent_volumes = [
                entry for entry in self.volume_history[symbol]
                if entry['timestamp'] > cutoff_time
            ]
            
            if len(recent_volumes) < 5:
                return {'error': 'Insufficient recent data'}
            
            # Calcular estadísticas de tendencia
            volumes = [entry['volume'] for entry in recent_volumes]
            ratios = [entry['volume_ratio'] for entry in recent_volumes]
            
            avg_volume = np.mean(volumes)
            avg_ratio = np.mean(ratios)
            max_ratio = max(ratios)
            
            # Detectar tendencia
            first_half = volumes[:len(volumes)//2]
            second_half = volumes[len(volumes)//2:]
            
            first_avg = np.mean(first_half)
            second_avg = np.mean(second_half)
            
            trend_change = (second_avg - first_avg) / first_avg * 100 if first_avg > 0 else 0
            
            return {
                'timeframe_hours': timeframe_hours,
                'data_points': len(recent_volumes),
                'average_volume': avg_volume,
                'average_ratio': avg_ratio,
                'max_ratio': max_ratio,
                'trend_change_percent': trend_change,
                'trend_direction': 'INCREASING' if trend_change > 20 else 'DECREASING' if trend_change < -20 else 'STABLE'
            }
            
        except Exception as e:
            log.error(f"Error en análisis de tendencia de volumen: {e}")
            return {'error': str(e)}
