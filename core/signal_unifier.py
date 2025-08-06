"""
Unificador de Señales v2.0
Une las 3 secciones: Histórico + Técnico + Confluencia = Señal Final
Sistema de scoring 0-100 puntos con clasificación Débil/Medio/Alto/Fuerte
"""

from typing import Dict, List, Tuple
from datetime import datetime
from config.parameters import CONFIDENCE_LEVELS, TARGET_MOVEMENT
from utils.logger import log


class SignalUnifier:
    """
    Unifica los análisis histórico, técnico y de confluencia para generar 
    la señal final de momentum alcista con clasificación de confianza.
    """
    
    def __init__(self):
        self.signal_history: List[Dict] = []
        self.max_history = 100  # Mantener últimas 100 señales
        
    def unify_signals(self, symbol: str, historical_result: Dict, 
                     technical_result: Dict, confluence_result: Dict) -> Dict:
        """
        Unifica las 3 secciones para generar señal final.
        
        Args:
            symbol: Símbolo analizado
            historical_result: Resultado del análisis histórico (0-25 puntos)
            technical_result: Resultado del análisis técnico (0-50 puntos)  
            confluence_result: Resultado de confluencia multi-timeframe (0-25 puntos)
            
        Returns:
            Dict con señal unificada y clasificación de confianza
        """
        try:
            # Inicializar resultado
            unified_signal = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'total_score': 0,
                'confidence_level': 'DÉBIL',
                'signal_strength': 'WEAK',
                'recommendation': 'HOLD',
                'target_probability': 0,
                'components': {
                    'historical': historical_result,
                    'technical': technical_result,
                    'confluence': confluence_result
                },
                'analysis_summary': {},
                'risk_factors': [],
                'confirmation_signals': []
            }
            
            # 1. Calcular score total (0-100)
            total_score = self._calculate_total_score(
                historical_result, technical_result, confluence_result
            )
            unified_signal['total_score'] = total_score
            
            # 2. Clasificar nivel de confianza
            confidence_level = self._classify_confidence_level(total_score)
            unified_signal['confidence_level'] = confidence_level
            
            # 3. Determinar fuerza de señal
            signal_strength = self._determine_signal_strength(
                total_score, historical_result, technical_result, confluence_result
            )
            unified_signal['signal_strength'] = signal_strength
            
            # 4. Generar recomendación
            recommendation = self._generate_recommendation(
                confidence_level, signal_strength, total_score
            )
            unified_signal['recommendation'] = recommendation
            
            # 5. Calcular probabilidad de alcanzar objetivo +7.5%
            target_probability = self._calculate_target_probability(
                total_score, historical_result, technical_result, confluence_result
            )
            unified_signal['target_probability'] = target_probability
            
            # 6. Generar resumen de análisis
            analysis_summary = self._generate_analysis_summary(
                historical_result, technical_result, confluence_result
            )
            unified_signal['analysis_summary'] = analysis_summary
            
            # 7. Identificar factores de riesgo
            risk_factors = self._identify_risk_factors(
                historical_result, technical_result, confluence_result
            )
            unified_signal['risk_factors'] = risk_factors
            
            # 8. Identificar señales de confirmación
            confirmation_signals = self._identify_confirmation_signals(
                historical_result, technical_result, confluence_result
            )
            unified_signal['confirmation_signals'] = confirmation_signals
            
            # Guardar en historial
            self._save_to_history(unified_signal)
            
            log.info(f"Señal unificada {symbol}: {total_score}/100 - {confidence_level} - {recommendation}")
            
            return unified_signal
            
        except Exception as e:
            log.error(f"Error unificando señales para {symbol}: {e}")
            return {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'total_score': 0,
                'confidence_level': 'DÉBIL',
                'error': str(e)
            }
    
    def _calculate_total_score(self, historical: Dict, technical: Dict, 
                             confluence: Dict) -> int:
        """
        Calcula score total sumando las 3 secciones.
        Máximo: 25 + 50 + 25 = 100 puntos
        """
        try:
            historical_score = historical.get('historical_score', 0)
            technical_score = technical.get('technical_score', 0)
            confluence_score = confluence.get('confluence_score', 0)
            
            total = historical_score + technical_score + confluence_score
            return min(max(total, 0), 100)  # Asegurar rango 0-100
            
        except Exception as e:
            log.error(f"Error calculando score total: {e}")
            return 0
    
    def _classify_confidence_level(self, total_score: int) -> str:
        """Clasifica el nivel de confianza según score total"""
        for level, (min_score, max_score) in CONFIDENCE_LEVELS.items():
            if min_score <= total_score <= max_score:
                return level
        return 'DÉBIL'  # Por defecto
    
    def _determine_signal_strength(self, total_score: int, historical: Dict,
                                 technical: Dict, confluence: Dict) -> str:
        """Determina la fuerza de la señal basada en distribución de scores"""
        try:
            # Verificar balance entre componentes
            hist_score = historical.get('historical_score', 0)
            tech_score = technical.get('technical_score', 0)
            conf_score = confluence.get('confluence_score', 0)
            
            # Señal fuerte requiere buenos scores en todos los componentes
            if total_score >= 85:
                if hist_score >= 15 and tech_score >= 35 and conf_score >= 18:
                    return 'VERY_STRONG'
                else:
                    return 'STRONG'
            elif total_score >= 70:
                if tech_score >= 25 and conf_score >= 15:
                    return 'STRONG'
                else:
                    return 'MODERATE'
            elif total_score >= 50:
                return 'MODERATE'
            elif total_score >= 30:
                return 'WEAK'
            else:
                return 'VERY_WEAK'
                
        except Exception as e:
            log.error(f"Error determinando fuerza de señal: {e}")
            return 'WEAK'
    
    def _generate_recommendation(self, confidence_level: str, signal_strength: str,
                               total_score: int) -> str:
        """Genera recomendación basada en confianza y fuerza"""
        
        if confidence_level == 'FUERTE' and signal_strength in ['VERY_STRONG', 'STRONG']:
            return 'STRONG_BUY'
        elif confidence_level in ['FUERTE', 'ALTO'] and signal_strength in ['STRONG', 'MODERATE']:
            return 'BUY'
        elif confidence_level in ['ALTO', 'MEDIO'] and total_score >= 60:
            return 'WEAK_BUY'
        elif confidence_level == 'MEDIO' and total_score >= 50:
            return 'WATCH'
        else:
            return 'HOLD'
    
    def _calculate_target_probability(self, total_score: int, historical: Dict,
                                    technical: Dict, confluence: Dict) -> float:
        """
        Calcula probabilidad de alcanzar objetivo +7.5%
        Basado en score total y factores específicos
        """
        try:
            # Probabilidad base según score total
            base_probability = min(total_score / 100.0, 0.95)  # Máximo 95%
            
            # Ajustes por factores específicos
            adjustments = 0
            
            # Bonus por confluencia multi-timeframe fuerte
            confluence_score = confluence.get('confluence_score', 0)
            if confluence_score >= 20:
                adjustments += 0.10
            elif confluence_score >= 15:
                adjustments += 0.05
            
            # Bonus por momentum técnico fuerte
            tech_score = technical.get('technical_score', 0)
            if tech_score >= 40:
                adjustments += 0.08
            elif tech_score >= 30:
                adjustments += 0.04
            
            # Bonus por patrones históricos sólidos
            hist_score = historical.get('historical_score', 0)
            if hist_score >= 20:
                adjustments += 0.05
            
            # Penalty por desequilibrios
            max_component = max(hist_score/25, tech_score/50, confluence_score/25)
            min_component = min(hist_score/25, tech_score/50, confluence_score/25)
            if max_component - min_component > 0.5:  # Gran desequilibrio
                adjustments -= 0.10
            
            final_probability = max(0, min(base_probability + adjustments, 0.95))
            return round(final_probability, 3)
            
        except Exception as e:
            log.error(f"Error calculando probabilidad objetivo: {e}")
            return 0.0
    
    def _generate_analysis_summary(self, historical: Dict, technical: Dict,
                                 confluence: Dict) -> Dict:
        """Genera resumen del análisis de cada componente"""
        try:
            summary = {
                'historical_highlights': [],
                'technical_highlights': [],
                'confluence_highlights': [],
                'overall_assessment': ''
            }
            
            # Resumen histórico
            hist_score = historical.get('historical_score', 0)
            if hist_score >= 20:
                summary['historical_highlights'].append('Patrones históricos muy favorables')
            elif hist_score >= 15:
                summary['historical_highlights'].append('Patrones históricos favorables')
            elif hist_score >= 10:
                summary['historical_highlights'].append('Algunos patrones históricos positivos')
            else:
                summary['historical_highlights'].append('Patrones históricos débiles')
            
            # Resumen técnico  
            tech_score = technical.get('technical_score', 0)
            if tech_score >= 40:
                summary['technical_highlights'].append('Indicadores técnicos muy alcistas')
            elif tech_score >= 30:
                summary['technical_highlights'].append('Indicadores técnicos alcistas')
            elif tech_score >= 20:
                summary['technical_highlights'].append('Algunos indicadores técnicos positivos')
            else:
                summary['technical_highlights'].append('Indicadores técnicos débiles')
            
            # Agregar detalles específicos si están disponibles
            if 'confluence_factors' in technical:
                factors = technical['confluence_factors']
                if 'triple_bullish_confluence' in factors:
                    summary['technical_highlights'].append('Triple confluencia alcista detectada')
                if 'momentum_breakout' in factors:
                    summary['technical_highlights'].append('Breakout de momentum con volumen')
            
            # Resumen confluencia
            conf_score = confluence.get('confluence_score', 0)
            bullish_tf = len(confluence.get('bullish_timeframes', []))
            total_tf = len(['5m', '15m', '1h', '4h'])
            
            summary['confluence_highlights'].append(
                f'Confluencia: {bullish_tf}/{total_tf} timeframes alcistas'
            )
            
            if conf_score >= 20:
                summary['confluence_highlights'].append('Confluencia multi-timeframe muy fuerte')
            elif conf_score >= 15:
                summary['confluence_highlights'].append('Confluencia multi-timeframe fuerte')
            elif conf_score >= 10:
                summary['confluence_highlights'].append('Confluencia multi-timeframe moderada')
            
            # Evaluación general
            total_score = hist_score + tech_score + conf_score
            if total_score >= 80:
                summary['overall_assessment'] = 'Señal de momentum alcista muy sólida con alta probabilidad'
            elif total_score >= 65:
                summary['overall_assessment'] = 'Señal de momentum alcista sólida con buena probabilidad'
            elif total_score >= 50:
                summary['overall_assessment'] = 'Señal de momentum alcista moderada'
            else:
                summary['overall_assessment'] = 'Señal de momentum alcista débil'
            
            return summary
            
        except Exception as e:
            log.error(f"Error generando resumen: {e}")
            return {}
    
    def _identify_risk_factors(self, historical: Dict, technical: Dict,
                             confluence: Dict) -> List[str]:
        """Identifica factores de riesgo potenciales"""
        risk_factors = []
        
        try:
            # Riesgos por desequilibrios
            hist_score = historical.get('historical_score', 0)
            tech_score = technical.get('technical_score', 0)
            conf_score = confluence.get('confluence_score', 0)
            
            if hist_score < 10:
                risk_factors.append('Patrones históricos débiles')
            
            if tech_score < 20:
                risk_factors.append('Indicadores técnicos débiles')
            
            if conf_score < 10:
                risk_factors.append('Baja confluencia entre timeframes')
            
            # Riesgos por sobrecompra
            if 'rsi_analysis' in technical:
                rsi_data = technical['rsi_analysis']
                if rsi_data.get('current_rsi', 50) > 75:
                    risk_factors.append('RSI en zona de sobrecompra')
            
            # Riesgos por timeframes bajistas
            bearish_tf = confluence.get('bearish_timeframes', [])
            if len(bearish_tf) >= 2:
                risk_factors.append(f'{len(bearish_tf)} timeframes con tendencia bajista')
            
            # Riesgo por falta de volumen
            if 'volume_analysis' in technical:
                vol_data = technical['volume_analysis']
                if vol_data.get('volume_ratio', 1) < 1.2:
                    risk_factors.append('Volumen por debajo del promedio')
            
            return risk_factors
            
        except Exception as e:
            log.error(f"Error identificando riesgos: {e}")
            return ['Error en análisis de riesgos']
    
    def _identify_confirmation_signals(self, historical: Dict, technical: Dict,
                                     confluence: Dict) -> List[str]:
        """Identifica señales de confirmación del momentum"""
        confirmations = []
        
        try:
            # Confirmaciones técnicas
            if 'confluence_factors' in technical:
                factors = technical['confluence_factors']
                for factor in factors:
                    if factor == 'triple_bullish_confluence':
                        confirmations.append('Triple confluencia técnica')
                    elif factor == 'momentum_breakout':
                        confirmations.append('Breakout con volumen confirmado')
                    elif factor == 'rsi_macd_bullish':
                        confirmations.append('RSI y MACD en sincronía alcista')
            
            # Confirmaciones de confluencia
            bullish_tf = len(confluence.get('bullish_timeframes', []))
            if bullish_tf >= 3:
                confirmations.append(f'{bullish_tf} timeframes confirman momentum alcista')
            
            # Confirmaciones históricas
            patterns = historical.get('momentum_patterns', [])
            if patterns:
                pattern_count = sum(p.get('count', 0) for p in patterns)
                if pattern_count >= 5:
                    confirmations.append('Múltiples patrones históricos alcistas')
            
            # Confirmación de volumen
            if 'volume_analysis' in technical:
                vol_signals = technical['volume_analysis'].get('signals', [])
                if 'explosive_volume' in vol_signals:
                    confirmations.append('Volumen explosivo confirma momentum')
                elif 'high_volume_spike' in vol_signals:
                    confirmations.append('Spike de volumen confirma interés')
            
            return confirmations
            
        except Exception as e:
            log.error(f"Error identificando confirmaciones: {e}")
            return []
    
    def _save_to_history(self, signal: Dict):
        """Guarda señal en historial para análisis posterior"""
        try:
            self.signal_history.append(signal)
            
            # Mantener solo las últimas señales
            if len(self.signal_history) > self.max_history:
                self.signal_history = self.signal_history[-self.max_history:]
                
        except Exception as e:
            log.error(f"Error guardando en historial: {e}")
    
    def get_signal_summary(self, signal: Dict) -> str:
        """Genera resumen textual de la señal para logs/alertas"""
        try:
            symbol = signal['symbol']
            score = signal['total_score']
            confidence = signal['confidence_level']
            recommendation = signal['recommendation']
            probability = signal['target_probability']
            
            summary = f"🎯 {symbol} | Score: {score}/100 | {confidence} | {recommendation}"
            summary += f" | Prob +7.5%: {probability:.1%}"
            
            # Agregar highlights principales
            components = signal.get('components', {})
            hist_score = components.get('historical', {}).get('historical_score', 0)
            tech_score = components.get('technical', {}).get('technical_score', 0)
            conf_score = components.get('confluence', {}).get('confluence_score', 0)
            
            summary += f" | H:{hist_score} T:{tech_score} C:{conf_score}"
            
            return summary
            
        except Exception as e:
            return f"Error en resumen de señal: {e}"
    
    def get_recent_signals(self, count: int = 10) -> List[Dict]:
        """Obtiene las señales más recientes"""
        return self.signal_history[-count:] if self.signal_history else []
    
    def get_strong_signals_today(self) -> List[Dict]:
        """Obtiene señales fuertes del día actual"""
        try:
            today = datetime.now().date()
            strong_signals = []
            
            for signal in self.signal_history:
                signal_date = signal.get('timestamp', datetime.now()).date()
                if signal_date == today:
                    if signal.get('confidence_level') in ['FUERTE', 'ALTO']:
                        strong_signals.append(signal)
            
            return strong_signals
            
        except Exception as e:
            log.error(f"Error obteniendo señales fuertes: {e}")
            return []
