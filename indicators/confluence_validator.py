"""
Validador de Confluencia Multi-Timeframe v2.0
Analiza confluencia en 5m, 15m, 1h, 4h para validar momentum
Score: 0-25 puntos
"""

import asyncio
from typing import Dict, List, Tuple
from datetime import datetime
from config.parameters import TIMEFRAMES, MIN_TIMEFRAMES_BULLISH, CONFLUENCE_MAX_SCORE
from utils.logger import log


class ConfluenceValidator:
    """
    Valida confluencia de momentum entre múltiples timeframes.
    Lógica: 3+ timeframes alcistas = señal fuerte
    """
    
    def __init__(self):
        self.timeframe_weights = {
            '5m': 1.0,   # Timeframe más corto, menor peso
            '15m': 1.2,  # 
            '1h': 1.5,   # Timeframes más largos, mayor peso
            '4h': 2.0    # Máximo peso para 4h
        }
        
    async def validate_multi_timeframe_confluence(self, symbol: str, 
                                                timeframe_data: Dict) -> Dict:
        """
        Valida confluencia entre timeframes para un símbolo.
        
        Args:
            symbol: Símbolo a analizar
            timeframe_data: Dict con datos de cada timeframe
            
        Returns:
            Dict con score de confluencia (0-25) y análisis detallado
        """
        try:
            result = {
                'symbol': symbol,
                'confluence_score': 0,
                'bullish_timeframes': [],
                'bearish_timeframes': [],
                'neutral_timeframes': [],
                'confluence_strength': 'WEAK',
                'dominant_trend': 'NEUTRAL',
                'timeframe_analysis': {},
                'timestamp': datetime.now()
            }
            
            # Analizar cada timeframe individualmente
            timeframe_analysis = {}
            bullish_count = 0
            total_weight = 0
            bullish_weight = 0
            
            for timeframe in TIMEFRAMES:
                if timeframe not in timeframe_data:
                    continue
                
                # Analizar momentum en este timeframe
                tf_result = await self._analyze_timeframe_momentum(
                    timeframe, timeframe_data[timeframe]
                )
                
                timeframe_analysis[timeframe] = tf_result
                weight = self.timeframe_weights.get(timeframe, 1.0)
                total_weight += weight
                
                # Clasificar timeframe
                if tf_result['trend'] == 'BULLISH':
                    result['bullish_timeframes'].append(timeframe)
                    bullish_count += 1
                    bullish_weight += weight
                elif tf_result['trend'] == 'BEARISH':
                    result['bearish_timeframes'].append(timeframe)
                else:
                    result['neutral_timeframes'].append(timeframe)
            
            result['timeframe_analysis'] = timeframe_analysis
            
            # Calcular tendencia dominante
            if bullish_count >= MIN_TIMEFRAMES_BULLISH:
                result['dominant_trend'] = 'BULLISH'
            elif len(result['bearish_timeframes']) > len(result['bullish_timeframes']):
                result['dominant_trend'] = 'BEARISH'
            
            # Calcular fuerza de confluencia
            if total_weight > 0:
                bullish_ratio = bullish_weight / total_weight
                result['confluence_strength'] = self._classify_confluence_strength(
                    bullish_ratio, bullish_count
                )
            
            # Calcular score de confluencia
            confluence_score = self._calculate_confluence_score(
                bullish_count, bullish_ratio if total_weight > 0 else 0, 
                timeframe_analysis
            )
            result['confluence_score'] = confluence_score
            
            log.debug(f"Confluencia {symbol}: {confluence_score}/25 puntos, "
                     f"{bullish_count}/{len(TIMEFRAMES)} timeframes alcistas")
            
            return result
            
        except Exception as e:
            log.error(f"Error en validación de confluencia {symbol}: {e}")
            return {
                'symbol': symbol,
                'confluence_score': 0,
                'error': str(e),
                'timestamp': datetime.now()
            }
    
    async def _analyze_timeframe_momentum(self, timeframe: str, tf_data: Dict) -> Dict:
        """
        Analiza momentum en un timeframe específico.
        
        Returns:
            Dict con análisis de momentum del timeframe
        """
        try:
            result = {
                'timeframe': timeframe,
                'trend': 'NEUTRAL',
                'momentum_strength': 0,
                'price_action_score': 0,
                'volume_score': 0,
                'technical_score': 0,
                'signals': []
            }
            
            # Analizar acción del precio
            price_score = self._analyze_price_action(tf_data)
            result['price_action_score'] = price_score
            
            # Analizar volumen
            volume_score = self._analyze_timeframe_volume(tf_data)
            result['volume_score'] = volume_score
            
            # Analizar indicadores técnicos básicos
            technical_score = self._analyze_timeframe_technicals(tf_data)
            result['technical_score'] = technical_score
            
            # Calcular momentum total del timeframe
            total_momentum = price_score + volume_score + technical_score
            result['momentum_strength'] = total_momentum
            
            # Clasificar tendencia
            if total_momentum >= 7:
                result['trend'] = 'BULLISH'
                result['signals'].append('strong_bullish')
            elif total_momentum >= 4:
                result['trend'] = 'WEAK_BULLISH'
                result['signals'].append('weak_bullish')
            elif total_momentum <= -4:
                result['trend'] = 'BEARISH'
                result['signals'].append('bearish')
            else:
                result['trend'] = 'NEUTRAL'
            
            return result
            
        except Exception as e:
            log.error(f"Error analizando timeframe {timeframe}: {e}")
            return {
                'timeframe': timeframe,
                'trend': 'NEUTRAL',
                'momentum_strength': 0,
                'error': str(e)
            }
    
    def _analyze_price_action(self, tf_data: Dict) -> int:
        """
        Analiza acción del precio en el timeframe.
        Score: -5 a +5
        """
        try:
            score = 0
            candles = tf_data.get('candles', [])
            
            if len(candles) < 3:
                return 0
            
            # Últimas 3 velas para análisis
            recent_candles = candles[-3:]
            
            # Contar velas verdes vs rojas
            green_candles = sum(1 for c in recent_candles if c['close'] > c['open'])
            red_candles = len(recent_candles) - green_candles
            
            # Score por proporción de velas verdes
            if green_candles == 3:
                score += 3  # Todas verdes
            elif green_candles == 2:
                score += 1  # Mayoría verde
            elif red_candles == 3:
                score -= 3  # Todas rojas
            elif red_candles == 2:
                score -= 1  # Mayoría roja
            
            # Análisis de tendencia de cierre
            closes = [c['close'] for c in recent_candles]
            if len(closes) >= 2:
                if closes[-1] > closes[-2] > closes[-3]:
                    score += 2  # Tendencia alcista clara
                elif closes[-1] < closes[-2] < closes[-3]:
                    score -= 2  # Tendencia bajista clara
            
            return max(-5, min(5, score))
            
        except Exception as e:
            log.error(f"Error en análisis de precio: {e}")
            return 0
    
    def _analyze_timeframe_volume(self, tf_data: Dict) -> int:
        """
        Analiza volumen en el timeframe.
        Score: -3 a +3
        """
        try:
            score = 0
            candles = tf_data.get('candles', [])
            
            if len(candles) < 5:
                return 0
            
            # Calcular volumen promedio y actual
            volumes = [c['volume'] for c in candles[-5:]]
            avg_volume = sum(volumes[:-1]) / len(volumes[:-1])
            current_volume = volumes[-1]
            
            # Score por ratio de volumen
            if avg_volume > 0:
                volume_ratio = current_volume / avg_volume
                
                if volume_ratio >= 2.0:
                    score += 3  # Volumen muy alto
                elif volume_ratio >= 1.5:
                    score += 2  # Volumen alto
                elif volume_ratio >= 1.2:
                    score += 1  # Volumen moderado
                elif volume_ratio <= 0.5:
                    score -= 2  # Volumen muy bajo
                elif volume_ratio <= 0.8:
                    score -= 1  # Volumen bajo
            
            return max(-3, min(3, score))
            
        except Exception as e:
            log.error(f"Error en análisis de volumen: {e}")
            return 0
    
    def _analyze_timeframe_technicals(self, tf_data: Dict) -> int:
        """
        Análisis técnico básico del timeframe.
        Score: -3 a +3
        """
        try:
            score = 0
            
            # Análisis de RSI si está disponible
            rsi = tf_data.get('rsi')
            if rsi is not None:
                if rsi > 70:
                    score += 1  # Momentum fuerte (pero cuidado sobrecompra)
                elif rsi > 50:
                    score += 2  # Zona alcista
                elif rsi > 30:
                    score += 1  # Recuperación de sobrevendido
                elif rsi <= 30:
                    score -= 1  # Sobrevendido
            
            # Análisis de MACD si está disponible
            macd = tf_data.get('macd')
            if macd is not None:
                macd_line = macd.get('macd', 0)
                signal_line = macd.get('signal', 0)
                
                if macd_line > signal_line:
                    score += 1  # MACD alcista
                else:
                    score -= 1  # MACD bajista
            
            # Análisis de precio vs SMA
            sma = tf_data.get('sma_20')
            current_price = tf_data.get('current_price')
            if sma and current_price:
                if current_price > sma * 1.02:  # +2% sobre SMA
                    score += 1
                elif current_price < sma * 0.98:  # -2% bajo SMA
                    score -= 1
            
            return max(-3, min(3, score))
            
        except Exception as e:
            log.error(f"Error en análisis técnico de timeframe: {e}")
            return 0
    
    def _classify_confluence_strength(self, bullish_ratio: float, 
                                    bullish_count: int) -> str:
        """Clasifica la fuerza de la confluencia"""
        
        if bullish_count >= 4 and bullish_ratio >= 0.9:
            return 'VERY_STRONG'
        elif bullish_count >= 3 and bullish_ratio >= 0.75:
            return 'STRONG'
        elif bullish_count >= 2 and bullish_ratio >= 0.6:
            return 'MODERATE'
        elif bullish_count >= 1:
            return 'WEAK'
        else:
            return 'VERY_WEAK'
    
    def _calculate_confluence_score(self, bullish_count: int, bullish_ratio: float,
                                  timeframe_analysis: Dict) -> int:
        """
        Calcula score de confluencia (0-25 puntos)
        
        Distribución:
        - Timeframes alcistas: 15 puntos máximo
        - Fuerza promedio: 6 puntos máximo
        - Consistencia: 4 puntos máximo
        """
        try:
            score = 0
            
            # 1. Score por cantidad de timeframes alcistas (15 puntos máximo)
            timeframe_score = 0
            if bullish_count >= 4:
                timeframe_score = 15  # Todos alcistas
            elif bullish_count == 3:
                timeframe_score = 12  # 3/4 alcistas
            elif bullish_count == 2:
                timeframe_score = 8   # 2/4 alcistas
            elif bullish_count == 1:
                timeframe_score = 3   # 1/4 alcista
            
            score += timeframe_score
            
            # 2. Score por fuerza promedio de momentum (6 puntos máximo)
            if timeframe_analysis:
                momentum_strengths = [
                    tf.get('momentum_strength', 0) 
                    for tf in timeframe_analysis.values()
                    if isinstance(tf, dict)
                ]
                
                if momentum_strengths:
                    avg_momentum = sum(momentum_strengths) / len(momentum_strengths)
                    strength_score = min(int(avg_momentum * 0.6), 6)  # Escalar a 6 máximo
                    score += max(0, strength_score)
            
            # 3. Score por consistencia (4 puntos máximo)
            consistency_score = 0
            if bullish_ratio >= 0.9:
                consistency_score = 4  # Muy consistente
            elif bullish_ratio >= 0.75:
                consistency_score = 3  # Consistente
            elif bullish_ratio >= 0.6:
                consistency_score = 2  # Moderadamente consistente
            elif bullish_ratio >= 0.5:
                consistency_score = 1  # Poco consistente
            
            score += consistency_score
            
            return min(score, CONFLUENCE_MAX_SCORE)
            
        except Exception as e:
            log.error(f"Error calculando score de confluencia: {e}")
            return 0
    
    async def get_timeframe_summary(self, symbol: str, timeframe_data: Dict) -> str:
        """Genera resumen textual de la confluencia"""
        try:
            result = await self.validate_multi_timeframe_confluence(symbol, timeframe_data)
            
            bullish_tf = len(result['bullish_timeframes'])
            total_tf = len(TIMEFRAMES)
            strength = result['confluence_strength']
            score = result['confluence_score']
            
            summary = f"Confluencia {symbol}: {bullish_tf}/{total_tf} timeframes alcistas"
            summary += f" | Fuerza: {strength} | Score: {score}/25"
            
            if result['dominant_trend'] == 'BULLISH':
                summary += " ✅ ALCISTA"
            elif result['dominant_trend'] == 'BEARISH':
                summary += " ❌ BAJISTA"
            else:
                summary += " ⚪ NEUTRAL"
            
            return summary
            
        except Exception as e:
            return f"Error en resumen de confluencia: {e}"
