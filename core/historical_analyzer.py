"""
Analizador Histórico v2.0
Sección 1: Análisis histórico del precio y detección de patrones
Score: 0-25 puntos
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from config.parameters import HISTORICAL_PERIODS, HISTORICAL_MAX_SCORE
from utils.logger import log


class HistoricalAnalyzer:
    """
    Realiza análisis histórico del precio de las monedas en Binance.
    Calcula promedios, detecta picos y patrones de subida.
    """
    
    def __init__(self):
        self.price_averages_cache: Dict[str, Dict] = {}
        self.patterns_cache: Dict[str, Dict] = {}
        
    def analyze_symbol_history(self, symbol: str, historical_data: Dict) -> Dict:
        """
        Análisis histórico completo para un símbolo.
        
        Returns:
            Dict con score histórico (0-25) y detalles del análisis
        """
        try:
            result = {
                'symbol': symbol,
                'historical_score': 0,
                'price_averages': {},
                'peak_patterns': {},
                'momentum_patterns': [],
                'timestamp': datetime.now()
            }
            
            # 1. Calcular promedios de precio (1d, 1w, 1m)
            price_averages = self._calculate_price_averages(historical_data)
            result['price_averages'] = price_averages
            
            # 2. Detectar picos históricos
            peak_patterns = self._detect_historical_peaks(historical_data)
            result['peak_patterns'] = peak_patterns
            
            # 3. Identificar patrones de momentum
            momentum_patterns = self._identify_momentum_patterns(historical_data)
            result['momentum_patterns'] = momentum_patterns
            
            # 4. Calcular score histórico
            historical_score = self._calculate_historical_score(
                price_averages, peak_patterns, momentum_patterns
            )
            result['historical_score'] = historical_score
            
            log.debug(f"Análisis histórico {symbol}: {historical_score}/25 puntos")
            return result
            
        except Exception as e:
            log.error(f"Error en análisis histórico {symbol}: {e}")
            return {
                'symbol': symbol,
                'historical_score': 0,
                'error': str(e),
                'timestamp': datetime.now()
            }
    
    def _calculate_price_averages(self, historical_data: Dict) -> Dict:
        """Calcula promedios de precio para 1d, 1w, 1m"""
        try:
            averages = {}
            current_price = historical_data.get('current_price', 0)
            
            for period in HISTORICAL_PERIODS['price_average']:
                period_data = historical_data.get(f'data_{period}', [])
                if period_data:
                    prices = [candle['close'] for candle in period_data]
                    avg_price = np.mean(prices)
                    
                    # Calcular % de cambio vs promedio
                    price_change_pct = ((current_price - avg_price) / avg_price) * 100
                    
                    averages[period] = {
                        'average_price': avg_price,
                        'current_vs_average': price_change_pct,
                        'samples': len(prices)
                    }
            
            return averages
            
        except Exception as e:
            log.error(f"Error calculando promedios: {e}")
            return {}
    
    def _detect_historical_peaks(self, historical_data: Dict) -> Dict:
        """Detecta picos de subida en 1h, 4h, 12h, 1d"""
        try:
            peaks = {}
            
            for period in HISTORICAL_PERIODS['peak_detection']:
                period_data = historical_data.get(f'data_{period}', [])
                if len(period_data) < 10:  # Mínimo datos necesarios
                    continue
                
                # Convertir a DataFrame para análisis
                df = pd.DataFrame(period_data)
                prices = df['close'].values
                
                # Detectar picos usando scipy.signal-like logic
                peak_indices = self._find_peaks(prices)
                
                if peak_indices:
                    peak_analysis = self._analyze_peaks(prices, peak_indices, period)
                    peaks[period] = peak_analysis
            
            return peaks
            
        except Exception as e:
            log.error(f"Error detectando picos: {e}")
            return {}
    
    def _find_peaks(self, prices: np.ndarray, min_prominence: float = 0.02) -> List[int]:
        """Encuentra índices de picos en los precios"""
        peaks = []
        if len(prices) < 3:
            return peaks
        
        for i in range(1, len(prices) - 1):
            # Un pico debe ser mayor que sus vecinos
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                # Verificar prominencia mínima (2% por defecto)
                prominence = min(
                    prices[i] - prices[i-1], 
                    prices[i] - prices[i+1]
                ) / prices[i]
                
                if prominence >= min_prominence:
                    peaks.append(i)
        
        return peaks
    
    def _analyze_peaks(self, prices: np.ndarray, peak_indices: List[int], period: str) -> Dict:
        """Analiza las características de los picos encontrados"""
        try:
            if not peak_indices:
                return {'peak_count': 0}
            
            peak_analysis = {
                'peak_count': len(peak_indices),
                'avg_peak_height': 0,
                'max_peak_height': 0,
                'peak_frequency': 0,
                'recent_peaks': 0  # Picos en último 25% del período
            }
            
            peak_heights = []
            recent_threshold = len(prices) * 0.75  # Últimos 25%
            
            for idx in peak_indices:
                # Calcular altura del pico vs precio base
                base_price = min(prices[max(0, idx-2):idx+3])
                peak_height = ((prices[idx] - base_price) / base_price) * 100
                peak_heights.append(peak_height)
                
                # Contar picos recientes
                if idx >= recent_threshold:
                    peak_analysis['recent_peaks'] += 1
            
            if peak_heights:
                peak_analysis['avg_peak_height'] = np.mean(peak_heights)
                peak_analysis['max_peak_height'] = np.max(peak_heights)
                peak_analysis['peak_frequency'] = len(peak_indices) / len(prices)
            
            return peak_analysis
            
        except Exception as e:
            log.error(f"Error analizando picos: {e}")
            return {'peak_count': 0}
    
    def _identify_momentum_patterns(self, historical_data: Dict) -> List[Dict]:
        """Identifica patrones de momentum en datos históricos"""
        try:
            patterns = []
            
            # Analizar cada timeframe para patrones
            for period in ['1h', '4h', '1d']:
                period_data = historical_data.get(f'data_{period}', [])
                if len(period_data) < 20:
                    continue
                
                df = pd.DataFrame(period_data)
                
                # Patrón 1: Subidas sostenidas (3+ velas verdes consecutivas)
                sustained_rises = self._find_sustained_rises(df)
                
                # Patrón 2: Breakouts con volumen
                volume_breakouts = self._find_volume_breakouts(df)
                
                # Patrón 3: Reversiones desde sobrevendido
                oversold_reversals = self._find_oversold_reversals(df)
                
                patterns.extend([
                    {'type': 'sustained_rise', 'period': period, 'count': sustained_rises},
                    {'type': 'volume_breakout', 'period': period, 'count': volume_breakouts},
                    {'type': 'oversold_reversal', 'period': period, 'count': oversold_reversals}
                ])
            
            return patterns
            
        except Exception as e:
            log.error(f"Error identificando patrones: {e}")
            return []
    
    def _find_sustained_rises(self, df: pd.DataFrame) -> int:
        """Encuentra secuencias de 3+ velas verdes consecutivas"""
        count = 0
        consecutive = 0
        
        for _, row in df.iterrows():
            if row['close'] > row['open']:  # Vela verde
                consecutive += 1
            else:
                if consecutive >= 3:
                    count += 1
                consecutive = 0
        
        # Verificar última secuencia
        if consecutive >= 3:
            count += 1
        
        return count
    
    def _find_volume_breakouts(self, df: pd.DataFrame) -> int:
        """Encuentra breakouts acompañados de volumen alto"""
        if 'volume' not in df.columns or len(df) < 10:
            return 0
        
        # Calcular promedio de volumen
        avg_volume = df['volume'].rolling(10).mean()
        
        # Encontrar breakouts (precio + volumen)
        breakouts = 0
        for i in range(10, len(df)):
            price_breakout = df.iloc[i]['close'] > df.iloc[i-1]['high']
            volume_spike = df.iloc[i]['volume'] > avg_volume.iloc[i] * 2
            
            if price_breakout and volume_spike:
                breakouts += 1
        
        return breakouts
    
    def _find_oversold_reversals(self, df: pd.DataFrame) -> int:
        """Encuentra reversiones desde condiciones de sobrevendido"""
        if len(df) < 14:
            return 0
        
        # Calcular RSI simple
        rsi = self._calculate_simple_rsi(df['close'], period=14)
        
        reversals = 0
        for i in range(1, len(rsi)):
            # RSI estaba bajo (<30) y ahora está subiendo
            if rsi.iloc[i-1] < 30 and rsi.iloc[i] > rsi.iloc[i-1]:
                # Verificar que el precio también subió
                if df.iloc[i]['close'] > df.iloc[i-1]['close']:
                    reversals += 1
        
        return reversals
    
    def _calculate_simple_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI simple para análisis de patrones"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_historical_score(self, averages: Dict, peaks: Dict, patterns: List) -> int:
        """
        Calcula score histórico final (0-25 puntos)
        
        Distribución:
        - Promedios de precio vs actual: 8 puntos
        - Análisis de picos: 10 puntos  
        - Patrones de momentum: 7 puntos
        """
        score = 0
        
        try:
            # 1. Score por promedios de precio (8 puntos máximo)
            price_score = self._score_price_averages(averages)
            score += min(price_score, 8)
            
            # 2. Score por análisis de picos (10 puntos máximo)
            peaks_score = self._score_peaks_analysis(peaks)
            score += min(peaks_score, 10)
            
            # 3. Score por patrones de momentum (7 puntos máximo)
            patterns_score = self._score_momentum_patterns(patterns)
            score += min(patterns_score, 7)
            
            return min(score, HISTORICAL_MAX_SCORE)
            
        except Exception as e:
            log.error(f"Error calculando score histórico: {e}")
            return 0
    
    def _score_price_averages(self, averages: Dict) -> int:
        """Score basado en posición vs promedios históricos"""
        score = 0
        
        for period, data in averages.items():
            change_pct = data.get('current_vs_average', 0)
            
            # Puntos por estar arriba de promedios
            if change_pct > 5:      # +5% sobre promedio
                score += 3
            elif change_pct > 2:    # +2% sobre promedio
                score += 2
            elif change_pct > 0:    # Sobre promedio
                score += 1
        
        return score
    
    def _score_peaks_analysis(self, peaks: Dict) -> int:
        """Score basado en análisis de picos históricos"""
        score = 0
        
        for period, peak_data in peaks.items():
            peak_count = peak_data.get('peak_count', 0)
            recent_peaks = peak_data.get('recent_peaks', 0)
            avg_height = peak_data.get('avg_peak_height', 0)
            
            # Puntos por picos recientes
            score += min(recent_peaks * 2, 4)
            
            # Puntos por altura promedio de picos
            if avg_height > 10:     # Picos > 10%
                score += 3
            elif avg_height > 5:    # Picos > 5%
                score += 2
            elif avg_height > 2:    # Picos > 2%
                score += 1
        
        return score
    
    def _score_momentum_patterns(self, patterns: List) -> int:
        """Score basado en patrones de momentum identificados"""
        score = 0
        
        for pattern in patterns:
            pattern_count = pattern.get('count', 0)
            pattern_type = pattern.get('type', '')
            
            # Puntaje por tipo de patrón
            if pattern_type == 'sustained_rise':
                score += min(pattern_count, 3)
            elif pattern_type == 'volume_breakout':
                score += min(pattern_count * 2, 4)
            elif pattern_type == 'oversold_reversal':
                score += min(pattern_count, 2)
        
        return score
