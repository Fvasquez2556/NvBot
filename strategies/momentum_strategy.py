"""
Motor principal de análisis de momentum que combina todos los indicadores.
Sistema de scoring 0-100 puntos con clasificación de confianza.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from indicators.rsi_optimizer import RSIOptimizer
from indicators.macd_sensitive import MACDSensitive
from indicators.volume_analyzer import VolumeAnalyzer
from utils.signal_averaging import SignalAveraging
from config.trading_config import config
from utils.logger import log


class MomentumAnalyzer:
    """Analizador principal de momentum que integra todos los indicadores"""
    
    def __init__(self):
        # Inicializar indicadores
        self.rsi_analyzer = RSIOptimizer()
        self.macd_analyzer = MACDSensitive()
        self.volume_analyzer = VolumeAnalyzer()
        
        # Sistema de promedios históricos
        self.signal_averaging = SignalAveraging(window_size=10)
        
        # Cache de análisis
        self.analysis_cache: Dict[str, Dict] = {}
        
        # Configuración de scoring
        self.scoring_config = config.scoring
        
    async def analyze_symbol_momentum(self, symbol: str, symbol_data: Dict) -> Dict:
        """Análisis completo de momentum para un símbolo"""
        try:
            log.debug(f"Iniciando análisis de momentum para {symbol}")
            
            # Verificar datos suficientes
            if not self._validate_data_sufficiency(symbol_data):
                return {
                    'symbol': symbol,
                    'error': 'Insufficient data for analysis',
                    'timestamp': datetime.now()
                }
            
            # Preparar datos para análisis
            price_data = self._prepare_price_data(symbol_data)
            volume_data = self._prepare_volume_data(symbol_data)
            
            # Análisis paralelo de indicadores
            analysis_tasks = [
                self._analyze_rsi_component(symbol, price_data),
                self._analyze_macd_component(symbol, price_data),
                self._analyze_volume_component(symbol, volume_data),
                self._analyze_velocity_component(symbol, price_data),
                self._analyze_breakout_component(symbol, symbol_data)
            ]
            
            results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # Procesar resultados
            rsi_analysis = results[0] if not isinstance(results[0], Exception) else {}
            macd_analysis = results[1] if not isinstance(results[1], Exception) else {}
            volume_analysis = results[2] if not isinstance(results[2], Exception) else {}
            velocity_analysis = results[3] if not isinstance(results[3], Exception) else {}
            breakout_analysis = results[4] if not isinstance(results[4], Exception) else {}
            
            # Calcular score total y componentes
            momentum_score = self._calculate_total_momentum_score(
                rsi_analysis, macd_analysis, volume_analysis, 
                velocity_analysis, breakout_analysis
            )
            
            # Análisis de confluencia
            confluence_analysis = self._analyze_indicator_confluence(
                rsi_analysis, macd_analysis, volume_analysis
            )
            
            # Clasificar momentum
            momentum_classification = config.get_momentum_classification(momentum_score['total_score'])
            
            # Calcular probabilidad +7.5%
            probability_analysis = await self._calculate_movement_probability(
                symbol, symbol_data, momentum_score, confluence_analysis
            )
            
            # Generar señales consolidadas
            consolidated_signals = self._generate_consolidated_signals(
                rsi_analysis, macd_analysis, volume_analysis, momentum_classification
            )
            
            # Resultado final
            analysis_result = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'momentum_score': momentum_score,
                'classification': momentum_classification,
                'confidence_level': self._calculate_confidence_level(momentum_score, confluence_analysis),
                'probability_7_5': probability_analysis,
                'components': {
                    'rsi': rsi_analysis,
                    'macd': macd_analysis,
                    'volume': volume_analysis,
                    'velocity': velocity_analysis,
                    'breakout': breakout_analysis
                },
                'confluence': confluence_analysis,
                'signals': consolidated_signals,
                'recommendation': self._generate_recommendation(momentum_classification, probability_analysis)
            }
            
            # Añadir análisis al sistema de promedios históricos
            averaged_result = self.signal_averaging.add_signal(symbol, analysis_result)
            
            # El resultado incluye tanto la señal actual como la promediada
            final_result = {
                'current_analysis': analysis_result,  # Análisis actual
                'averaged_analysis': averaged_result['averaged_signal'],  # Análisis promediado
                'trend': averaged_result['trend'],  # Tendencia de fuerza
                'history_count': averaged_result['history_count'],
                'display_signal': averaged_result['averaged_signal'],  # Esta es la señal que se muestra
                'signal_strength_trend': averaged_result['trend']['direction'],
                'momentum_change': averaged_result['trend']['momentum_change'],
                'last_updated': averaged_result['last_updated']
            }
            
            # Actualizar cache con el resultado completo
            self.analysis_cache[symbol] = final_result
            
            log.debug(f"Análisis completado para {symbol}: {momentum_classification} ({momentum_score['total_score']}/100) - Tendencia: {final_result['signal_strength_trend']}")
            
            return final_result
            
        except Exception as e:
            log.error(f"Error en análisis de momentum para {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': f'Analysis failed: {str(e)}',
                'timestamp': datetime.now()
            }
    
    def _validate_data_sufficiency(self, symbol_data: Dict) -> bool:
        """Valida que los datos sean suficientes para análisis"""
        try:
            # Verificar ticker data
            if 'ticker' not in symbol_data:
                return False
            
            # Verificar klines data
            if 'klines' not in symbol_data:
                return False
            
            # Verificar timeframes necesarios
            required_timeframes = ['1m', '5m', '15m']
            for tf in required_timeframes:
                if tf not in symbol_data['klines']:
                    return False
                if len(symbol_data['klines'][tf]) < 50:  # Mínimo 50 velas
                    return False
            
            return True
            
        except Exception as e:
            log.error(f"Error validando datos: {e}")
            return False
    
    def _prepare_price_data(self, symbol_data: Dict) -> List[float]:
        """Prepara datos de precio para análisis"""
        try:
            # Usar datos de 5 minutos como principal
            klines_5m = symbol_data['klines']['5m']
            return [float(k['close']) for k in klines_5m]
            
        except Exception as e:
            log.error(f"Error preparando datos de precio: {e}")
            return []
    
    def _prepare_volume_data(self, symbol_data: Dict) -> List[Dict]:
        """Prepara datos de volumen para análisis"""
        try:
            # Usar datos de 5 minutos
            klines_5m = symbol_data['klines']['5m']
            return [{
                'volume': k['volume'],
                'quote_volume': k['quote_volume'],
                'close': k['close'],
                'high': k['high'],
                'low': k['low'],
                'open': k['open']
            } for k in klines_5m]
            
        except Exception as e:
            log.error(f"Error preparando datos de volumen: {e}")
            return []
    
    async def _analyze_rsi_component(self, symbol: str, price_data: List[float]) -> Dict:
        """Análisis del componente RSI"""
        try:
            return self.rsi_analyzer.analyze_rsi_momentum(symbol, price_data)
        except Exception as e:
            log.error(f"Error en análisis RSI: {e}")
            return {'error': str(e), 'score': 0}
    
    async def _analyze_macd_component(self, symbol: str, price_data: List[float]) -> Dict:
        """Análisis del componente MACD"""
        try:
            return self.macd_analyzer.analyze_macd_momentum(symbol, price_data)
        except Exception as e:
            log.error(f"Error en análisis MACD: {e}")
            return {'error': str(e), 'score': 0}
    
    async def _analyze_volume_component(self, symbol: str, volume_data: List[Dict]) -> Dict:
        """Análisis del componente Volumen"""
        try:
            return self.volume_analyzer.analyze_volume_momentum(symbol, volume_data)
        except Exception as e:
            log.error(f"Error en análisis Volumen: {e}")
            return {'error': str(e), 'score': 0}
    
    async def _analyze_velocity_component(self, symbol: str, price_data: List[float]) -> Dict:
        """Análisis de velocidad de precio"""
        try:
            if len(price_data) < 60:
                return {'error': 'Insufficient data', 'score': 0}
            
            # Calcular velocidades en diferentes timeframes (en datos de 5m)
            velocity_5m = self._calculate_price_velocity(price_data, 1)    # 5 minutos
            velocity_15m = self._calculate_price_velocity(price_data, 3)   # 15 minutos  
            velocity_1h = self._calculate_price_velocity(price_data, 12)   # 1 hora
            
            # Detectar aceleración
            acceleration_pattern = 'NONE'
            if velocity_5m > velocity_15m > velocity_1h > 0:
                acceleration_pattern = 'ACCELERATING_UPTREND'
            elif velocity_1h > 3:  # 3% en 1 hora sugiere potencial +7.5%
                acceleration_pattern = 'STRONG_MOMENTUM'
            
            # Calcular score (0-15 puntos)
            velocity_score = 0
            if acceleration_pattern == 'ACCELERATING_UPTREND':
                velocity_score = 15
            elif acceleration_pattern == 'STRONG_MOMENTUM':
                velocity_score = 12
            elif velocity_1h > 1.5:  # 1.5% en 1 hora
                velocity_score = 8
            elif velocity_15m > 1:   # 1% en 15 minutos
                velocity_score = 5
            
            return {
                'velocity_5m': velocity_5m,
                'velocity_15m': velocity_15m,
                'velocity_1h': velocity_1h,
                'pattern': acceleration_pattern,
                'score': min(velocity_score, config.scoring.velocity_max_points)
            }
            
        except Exception as e:
            log.error(f"Error en análisis de velocidad: {e}")
            return {'error': str(e), 'score': 0}
    
    def _calculate_price_velocity(self, prices: List[float], periods: int) -> float:
        """Calcula velocidad de cambio de precio"""
        try:
            if len(prices) < periods + 1:
                return 0
            
            current_price = prices[-1]
            past_price = prices[-(periods + 1)]
            
            return (current_price - past_price) / past_price * 100
            
        except Exception as e:
            log.error(f"Error calculando velocidad: {e}")
            return 0
    
    async def _analyze_breakout_component(self, symbol: str, symbol_data: Dict) -> Dict:
        """Análisis de patrones de breakout"""
        try:
            # Usar datos de 15 minutos para detectar breakouts
            klines_15m = symbol_data['klines']['15m']
            if len(klines_15m) < 20:
                return {'error': 'Insufficient data', 'score': 0}
            
            # Extraer precios
            highs = [float(k['high']) for k in klines_15m[-20:]]
            lows = [float(k['low']) for k in klines_15m[-20:]]
            closes = [float(k['close']) for k in klines_15m[-20:]]
            volumes = [float(k['volume']) for k in klines_15m[-20:]]
            
            current_price = closes[-1]
            current_volume = volumes[-1]
            avg_volume = sum(volumes[-10:-1]) / 9  # Promedio de 9 períodos anteriores
            
            # Calcular niveles de resistencia
            resistance_level = max(highs[:-1])  # Máximo excluyendo período actual
            support_level = min(lows[:-1])      # Mínimo excluyendo período actual
            
            # Detectar breakout
            breakout_type = 'NONE'
            breakout_strength = 0
            
            # Breakout alcista
            if current_price > resistance_level:
                price_above_resistance = (current_price - resistance_level) / resistance_level * 100
                volume_confirmation = current_volume / avg_volume if avg_volume > 0 else 1
                
                if price_above_resistance > 0.5 and volume_confirmation > 1.5:
                    breakout_type = 'BULLISH_BREAKOUT'
                    breakout_strength = min(price_above_resistance * volume_confirmation, 15)
            
            # Breakdown bajista
            elif current_price < support_level:
                breakout_type = 'BEARISH_BREAKDOWN'
                breakout_strength = 0  # No puntos por breakdowns bajistas
            
            # Calcular score (0-15 puntos)
            breakout_score = int(breakout_strength) if breakout_type == 'BULLISH_BREAKOUT' else 0
            
            return {
                'breakout_type': breakout_type,
                'resistance_level': resistance_level,
                'support_level': support_level,
                'current_price': current_price,
                'breakout_strength': breakout_strength,
                'volume_confirmation': current_volume / avg_volume if avg_volume > 0 else 1,
                'score': min(breakout_score, config.scoring.breakout_max_points)
            }
            
        except Exception as e:
            log.error(f"Error en análisis de breakout: {e}")
            return {'error': str(e), 'score': 0}
    
    def _calculate_total_momentum_score(self, rsi_analysis: Dict, macd_analysis: Dict, 
                                      volume_analysis: Dict, velocity_analysis: Dict, 
                                      breakout_analysis: Dict) -> Dict:
        """Calcula el score total de momentum"""
        try:
            # Extraer scores individuales
            rsi_score = rsi_analysis.get('score', 0)
            macd_score = macd_analysis.get('score', 0)
            volume_score = volume_analysis.get('score', 0)
            velocity_score = velocity_analysis.get('score', 0)
            breakout_score = breakout_analysis.get('score', 0)
            
            # Score total
            total_score = rsi_score + macd_score + volume_score + velocity_score + breakout_score
            
            # Aplicar bonificaciones por confluencia
            confluence_bonus = self._calculate_confluence_bonus(
                rsi_analysis, macd_analysis, volume_analysis
            )
            
            total_score += confluence_bonus
            
            # Limitar a 100
            total_score = min(total_score, 100)
            
            return {
                'total_score': total_score,
                'component_scores': {
                    'rsi': rsi_score,
                    'macd': macd_score,
                    'volume': volume_score,
                    'velocity': velocity_score,
                    'breakout': breakout_score
                },
                'confluence_bonus': confluence_bonus,
                'max_possible': 100
            }
            
        except Exception as e:
            log.error(f"Error calculando score total: {e}")
            return {'total_score': 0, 'component_scores': {}}
    
    def _calculate_confluence_bonus(self, rsi_analysis: Dict, macd_analysis: Dict, volume_analysis: Dict) -> int:
        """Calcula bonus por confluencia de indicadores"""
        try:
            bullish_indicators = 0
            
            # RSI bullish
            if rsi_analysis.get('score', 0) >= 15:
                bullish_indicators += 1
            
            # MACD bullish
            if macd_analysis.get('score', 0) >= 12:
                bullish_indicators += 1
            
            # Volume bullish
            if volume_analysis.get('score', 0) >= 15:
                bullish_indicators += 1
            
            # Bonus por confluencia
            if bullish_indicators >= 3:
                return 5  # Todos los indicadores principales en acuerdo
            elif bullish_indicators >= 2:
                return 3  # Dos indicadores en acuerdo
            else:
                return 0
                
        except Exception as e:
            log.error(f"Error calculando bonus de confluencia: {e}")
            return 0
    
    def _analyze_indicator_confluence(self, rsi_analysis: Dict, macd_analysis: Dict, volume_analysis: Dict) -> Dict:
        """Analiza la confluencia entre indicadores"""
        try:
            # Recopilar señales bullish
            bullish_signals = []
            
            # RSI señales
            rsi_signals = rsi_analysis.get('signals', [])
            if any('BULLISH' in signal or 'OVERSOLD' in signal for signal in rsi_signals):
                bullish_signals.append('RSI')
            
            # MACD señales  
            macd_signals = macd_analysis.get('signals', {})
            if macd_signals.get('crossover') == 'BULLISH_CROSSOVER':
                bullish_signals.append('MACD')
            
            # Volume señales
            volume_signals = volume_analysis.get('signals', [])
            if any('SPIKE' in signal or 'CONFIRMATION' in signal for signal in volume_signals):
                bullish_signals.append('VOLUME')
            
            # Calcular score de confluencia
            confluence_score = len(bullish_signals) / 3  # Normalizado 0-1
            
            return {
                'bullish_indicators': bullish_signals,
                'confluence_score': confluence_score,
                'agreement_level': 'HIGH' if confluence_score >= 0.67 else 'MEDIUM' if confluence_score >= 0.33 else 'LOW',
                'indicators_count': len(bullish_signals)
            }
            
        except Exception as e:
            log.error(f"Error analizando confluencia: {e}")
            return {'confluence_score': 0, 'agreement_level': 'LOW'}
    
    def _calculate_confidence_level(self, momentum_score: Dict, confluence_analysis: Dict) -> Dict:
        """Calcula el nivel de confianza del análisis"""
        try:
            total_score = momentum_score.get('total_score', 0)
            confluence_score = confluence_analysis.get('confluence_score', 0)
            
            # Base confidence from score
            if total_score >= config.scoring.strong_threshold:
                base_confidence = 'FUERTE'
                confidence_percentage = 85 + (total_score - 85) * 0.3
            elif total_score >= config.scoring.high_threshold:
                base_confidence = 'ALTO'
                confidence_percentage = 70 + (total_score - 70) * 0.5
            elif total_score >= config.scoring.medium_threshold:
                base_confidence = 'MEDIO'
                confidence_percentage = 50 + (total_score - 50) * 0.6
            else:
                base_confidence = 'DÉBIL'
                confidence_percentage = total_score * 0.8
            
            # Adjust by confluence
            confidence_percentage += confluence_score * 10
            confidence_percentage = min(confidence_percentage, 95)  # Cap at 95%
            
            return {
                'level': base_confidence,
                'percentage': confidence_percentage,
                'confluence_boost': confluence_score * 10
            }
            
        except Exception as e:
            log.error(f"Error calculando confianza: {e}")
            return {'level': 'DÉBIL', 'percentage': 0}
    
    async def _calculate_movement_probability(self, symbol: str, symbol_data: Dict, 
                                           momentum_score: Dict, confluence_analysis: Dict) -> Dict:
        """Calcula probabilidad de movimiento +7.5%"""
        try:
            # Factores base
            score_factor = momentum_score.get('total_score', 0) / 100
            confluence_factor = confluence_analysis.get('confluence_score', 0)
            
            # Análisis de volatilidad histórica
            volatility_factor = await self._calculate_volatility_factor(symbol_data)
            
            # Factor de volumen
            volume_score = momentum_score.get('component_scores', {}).get('volume', 0)
            volume_factor = volume_score / config.scoring.volume_max_points
            
            # Probabilidad base
            base_probability = (score_factor * 0.4 + confluence_factor * 0.3 + 
                              volatility_factor * 0.2 + volume_factor * 0.1)
            
            # Ajustar por timeframe
            timeframe_probabilities = {
                '2h': base_probability * 0.7,
                '4h': base_probability * 0.85,
                '8h': base_probability * 0.95,
                '24h': base_probability * 1.0
            }
            
            # Limitar probabilidades
            for tf in timeframe_probabilities:
                timeframe_probabilities[tf] = min(timeframe_probabilities[tf] * 100, 85)  # Max 85%
            
            return {
                'base_probability': base_probability * 100,
                'timeframe_probabilities': timeframe_probabilities,
                'factors': {
                    'momentum_score': score_factor,
                    'confluence': confluence_factor,
                    'volatility': volatility_factor,
                    'volume': volume_factor
                }
            }
            
        except Exception as e:
            log.error(f"Error calculando probabilidad: {e}")
            return {'base_probability': 0, 'timeframe_probabilities': {}}
    
    async def _calculate_volatility_factor(self, symbol_data: Dict) -> float:
        """Calcula factor de volatilidad para probabilidad"""
        try:
            # Usar datos de 1 hora para volatilidad
            if '1h' not in symbol_data.get('klines', {}):
                return 0.5  # Valor neutral
            
            klines_1h = symbol_data['klines']['1h'][-24:]  # Últimas 24 horas
            
            if len(klines_1h) < 10:
                return 0.5
            
            # Calcular rangos horarios
            hourly_ranges = []
            for kline in klines_1h:
                high = float(kline['high'])
                low = float(kline['low'])
                close = float(kline['close'])
                hourly_range = (high - low) / close * 100
                hourly_ranges.append(hourly_range)
            
            # Volatilidad promedio
            avg_volatility = sum(hourly_ranges) / len(hourly_ranges)
            
            # Factor: si volatilidad > 7.5%, factor alto
            if avg_volatility >= 7.5:
                return min(avg_volatility / 15, 1.0)  # Normalizar
            else:
                return avg_volatility / 15  # Menor factor si volatilidad insuficiente
                
        except Exception as e:
            log.error(f"Error calculando factor de volatilidad: {e}")
            return 0.5
    
    def _generate_consolidated_signals(self, rsi_analysis: Dict, macd_analysis: Dict, 
                                     volume_analysis: Dict, momentum_classification: str) -> List[str]:
        """Genera señales consolidadas"""
        signals = []
        
        # Señales por clasificación
        if momentum_classification == 'FUERTE':
            signals.append(f"MOMENTUM_FUERTE_ALTA_CONFIANZA")
        elif momentum_classification == 'ALTO':
            signals.append(f"MOMENTUM_ALTO")
        elif momentum_classification == 'MEDIO':
            signals.append(f"MOMENTUM_MEDIO")
        elif momentum_classification == 'DÉBIL':
            signals.append(f"MOMENTUM_DÉBIL")
        
        # Señales específicas de componentes
        if rsi_analysis.get('score', 0) >= 20:
            signals.append("RSI_BULLISH_STRONG")
        
        if macd_analysis.get('score', 0) >= 15:
            signals.append("MACD_BULLISH_MOMENTUM")
        
        if volume_analysis.get('score', 0) >= 20:
            signals.append("VOLUME_EXPLOSIVE_ACTIVITY")
        
        return signals
    
    def _generate_recommendation(self, momentum_classification: str, probability_analysis: Dict) -> Dict:
        """Genera recomendación basada en análisis"""
        try:
            prob_4h = probability_analysis.get('timeframe_probabilities', {}).get('4h', 0)
            
            if momentum_classification == 'FUERTE' and prob_4h >= 70:
                return {
                    'action': 'STRONG_BUY_SIGNAL',
                    'urgency': 'IMMEDIATE',
                    'description': f'Momentum fuerte con {prob_4h:.1f}% probabilidad +7.5% en 4h',
                    'timeframe': '2-4 horas'
                }
            elif momentum_classification == 'ALTO' and prob_4h >= 60:
                return {
                    'action': 'BUY_SIGNAL',
                    'urgency': 'HIGH',
                    'description': f'Momentum alto, revisar en 30 minutos',
                    'timeframe': '4-8 horas'
                }
            elif momentum_classification == 'MEDIO':
                return {
                    'action': 'WATCH_CLOSELY',
                    'urgency': 'MEDIUM',
                    'description': 'Momentum building, monitorear evolución',
                    'timeframe': '8-24 horas'
                }
            else:
                return {
                    'action': 'MONITOR',
                    'urgency': 'LOW',
                    'description': 'Momentum débil, confirmar con otros indicadores',
                    'timeframe': '24+ horas'
                }
                
        except Exception as e:
            log.error(f"Error generando recomendación: {e}")
            return {'action': 'ERROR', 'description': 'Error en análisis'}
    
    def get_cached_analysis(self, symbol: str) -> Optional[Dict]:
        """Obtiene análisis en cache"""
        return self.analysis_cache.get(symbol)
    
    def get_market_momentum_summary(self) -> Dict:
        """Obtiene resumen de momentum del mercado"""
        try:
            if not self.analysis_cache:
                return {'error': 'No analysis data available'}
            
            # Clasificar por niveles
            summary = {
                'FUERTE': [],
                'ALTO': [],
                'MEDIO': [],
                'DÉBIL': []
            }
            
            total_analyzed = 0
            avg_score = 0
            
            for symbol, analysis in self.analysis_cache.items():
                if 'error' not in analysis:
                    classification = analysis.get('classification', 'DÉBIL')
                    score = analysis.get('momentum_score', {}).get('total_score', 0)
                    
                    summary[classification].append({
                        'symbol': symbol,
                        'score': score,
                        'probability_4h': analysis.get('probability_7_5', {}).get('timeframe_probabilities', {}).get('4h', 0)
                    })
                    
                    total_analyzed += 1
                    avg_score += score
            
            # Ordenar por score dentro de cada categoría
            for level in summary:
                summary[level].sort(key=lambda x: x['score'], reverse=True)
            
            return {
                'summary_by_level': summary,
                'total_analyzed': total_analyzed,
                'average_score': avg_score / total_analyzed if total_analyzed > 0 else 0,
                'strong_opportunities': len(summary['FUERTE']),
                'high_opportunities': len(summary['ALTO']),
                'trend_summary': self.get_market_trend_summary(),  # Nuevo resumen de tendencias
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            log.error(f"Error generando resumen de mercado: {e}")
            return {'error': str(e)}

    def get_market_trend_summary(self) -> Dict:
        """Obtiene un resumen de las tendencias del mercado"""
        return self.signal_averaging.get_trend_summary()
    
    def cleanup_old_signals(self, max_age_hours: int = 24):
        """Limpia señales antiguas del historial"""
        self.signal_averaging.cleanup_old_signals(max_age_hours)
    
    def get_averaged_signals(self) -> Dict[str, Dict]:
        """Obtiene todas las señales promediadas"""
        return self.signal_averaging.get_all_averaged_signals()
