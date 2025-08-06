"""
Generador de Señales v2.0
Genera las señales finales optimizadas para el objetivo +7.5%
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from config.parameters import TARGET_DAILY_SIGNALS, TARGET_MOVEMENT, CONFIDENCE_LEVELS
from utils.logger import log


class SignalGenerator:
    """
    Genera señales finales de trading basadas en el análisis unificado.
    Optimizado para movimientos de +7.5% con alta probabilidad de éxito.
    """
    
    def __init__(self):
        self.generated_signals: List[Dict] = []
        self.daily_signal_count = 0
        self.last_reset_date = datetime.now().date()
        
    def generate_final_signals(self, unified_signals: List[Dict]) -> List[Dict]:
        """
        Genera señales finales de trading a partir de señales unificadas.
        
        Args:
            unified_signals: Lista de señales unificadas del SignalUnifier
            
        Returns:
            Lista de señales finales de trading optimizadas
        """
        try:
            self._reset_daily_count_if_needed()
            
            # Filtrar señales candidatas
            candidate_signals = self._filter_candidate_signals(unified_signals)
            
            # Clasificar por prioridad
            prioritized_signals = self._prioritize_signals(candidate_signals)
            
            # Seleccionar señales finales
            final_signals = self._select_final_signals(prioritized_signals)
            
            # Formatear para trading
            trading_signals = []
            for signal in final_signals:
                trading_signal = self._format_trading_signal(signal)
                if trading_signal:
                    trading_signals.append(trading_signal)
                    self.generated_signals.append(trading_signal)
            
            # Actualizar contador diario
            self.daily_signal_count += len(trading_signals)
            
            log.info(f"🎯 Generadas {len(trading_signals)} señales finales "
                    f"({self.daily_signal_count}/{TARGET_DAILY_SIGNALS} del día)")
            
            return trading_signals
            
        except Exception as e:
            log.error(f"Error generando señales finales: {e}")
            return []
    
    def _filter_candidate_signals(self, unified_signals: List[Dict]) -> List[Dict]:
        """Filtra señales candidatas según criterios de calidad"""
        try:
            candidates = []
            
            for signal in unified_signals:
                # Criterios mínimos para candidatura
                if not self._meets_minimum_criteria(signal):
                    continue
                
                # Verificar que no sea duplicada
                if self._is_duplicate_signal(signal):
                    continue
                
                # Verificar límite diario
                if self.daily_signal_count >= TARGET_DAILY_SIGNALS:
                    # Solo aceptar señales FUERTE si ya alcanzamos el límite
                    if signal.get('confidence_level') != 'FUERTE':
                        continue
                
                candidates.append(signal)
            
            log.debug(f"🔍 {len(candidates)} señales candidatas de {len(unified_signals)} analizadas")
            return candidates
            
        except Exception as e:
            log.error(f"Error filtrando candidatos: {e}")
            return []
    
    def _meets_minimum_criteria(self, signal: Dict) -> bool:
        """Verifica criterios mínimos para una señal"""
        try:
            # Score mínimo
            total_score = signal.get('total_score', 0)
            if total_score < 45:
                return False
            
            # Nivel de confianza mínimo
            confidence = signal.get('confidence_level', 'DÉBIL')
            if confidence == 'DÉBIL' and total_score < 55:
                return False
            
            # Recomendación debe ser de compra
            recommendation = signal.get('recommendation', 'HOLD')
            if recommendation not in ['STRONG_BUY', 'BUY', 'WEAK_BUY']:
                return False
            
            # Probabilidad mínima de éxito
            probability = signal.get('target_probability', 0)
            if probability < 0.35:  # 35% mínimo
                return False
            
            # Verificar componentes balanceados
            components = signal.get('components', {})
            hist_score = components.get('historical', {}).get('historical_score', 0)
            tech_score = components.get('technical', {}).get('technical_score', 0)
            conf_score = components.get('confluence', {}).get('confluence_score', 0)
            
            # Al menos 2 componentes deben tener score decente
            decent_components = sum([
                hist_score >= 12,   # 50% del máximo histórico
                tech_score >= 25,   # 50% del máximo técnico
                conf_score >= 12    # 50% del máximo confluencia
            ])
            
            if decent_components < 2:
                return False
            
            return True
            
        except Exception as e:
            log.error(f"Error verificando criterios mínimos: {e}")
            return False
    
    def _is_duplicate_signal(self, signal: Dict) -> bool:
        """Verifica si ya generamos una señal similar recientemente"""
        try:
            symbol = signal.get('symbol')
            if not symbol:
                return True
            
            # Buscar señales del mismo símbolo en las últimas 2 horas
            cutoff_time = datetime.now() - timedelta(hours=2)
            
            for prev_signal in self.generated_signals:
                if prev_signal.get('symbol') == symbol:
                    prev_time = prev_signal.get('timestamp', datetime.now())
                    if prev_time > cutoff_time:
                        return True
            
            return False
            
        except Exception as e:
            log.error(f"Error verificando duplicados: {e}")
            return False
    
    def _prioritize_signals(self, candidates: List[Dict]) -> List[Dict]:
        """Prioriza señales según múltiples criterios"""
        try:
            def calculate_priority_score(signal: Dict) -> float:
                priority = 0
                
                # Factor 1: Score total (40% del peso)
                total_score = signal.get('total_score', 0)
                priority += (total_score / 100) * 40
                
                # Factor 2: Probabilidad de éxito (25% del peso)
                probability = signal.get('target_probability', 0)
                priority += probability * 25
                
                # Factor 3: Nivel de confianza (20% del peso)
                confidence = signal.get('confidence_level', 'DÉBIL')
                confidence_weights = {
                    'FUERTE': 20,
                    'ALTO': 15,
                    'MEDIO': 10,
                    'DÉBIL': 5
                }
                priority += confidence_weights.get(confidence, 0)
                
                # Factor 4: Fuerza de la recomendación (10% del peso)
                recommendation = signal.get('recommendation', 'HOLD')
                rec_weights = {
                    'STRONG_BUY': 10,
                    'BUY': 8,
                    'WEAK_BUY': 6,
                    'WATCH': 3
                }
                priority += rec_weights.get(recommendation, 0)
                
                # Factor 5: Balance de componentes (5% del peso)
                balance_score = self._calculate_balance_score(signal)
                priority += balance_score * 5
                
                return priority
            
            # Calcular prioridad y ordenar
            for signal in candidates:
                signal['priority_score'] = calculate_priority_score(signal)
            
            # Ordenar por prioridad descendente
            prioritized = sorted(candidates, key=lambda x: x.get('priority_score', 0), reverse=True)
            
            return prioritized
            
        except Exception as e:
            log.error(f"Error priorizando señales: {e}")
            return candidates
    
    def _calculate_balance_score(self, signal: Dict) -> float:
        """Calcula score de balance entre componentes (0-1)"""
        try:
            components = signal.get('components', {})
            
            # Normalizar scores de componentes
            hist_norm = components.get('historical', {}).get('historical_score', 0) / 25
            tech_norm = components.get('technical', {}).get('technical_score', 0) / 50
            conf_norm = components.get('confluence', {}).get('confluence_score', 0) / 25
            
            scores = [hist_norm, tech_norm, conf_norm]
            
            # Balance = 1 - desviación estándar
            if scores:
                mean_score = sum(scores) / len(scores)
                variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
                std_dev = variance ** 0.5
                balance = max(0, 1 - std_dev)
                return balance
            
            return 0
            
        except Exception:
            return 0
    
    def _select_final_signals(self, prioritized_signals: List[Dict]) -> List[Dict]:
        """Selecciona las señales finales respetando límites y diversificación"""
        try:
            final_signals = []
            remaining_slots = TARGET_DAILY_SIGNALS - self.daily_signal_count
            
            if remaining_slots <= 0:
                # Solo señales FUERTE si ya alcanzamos el límite
                fuerte_signals = [s for s in prioritized_signals 
                                if s.get('confidence_level') == 'FUERTE']
                return fuerte_signals[:2]  # Máximo 2 adicionales muy fuertes
            
            # Selección diversificada
            selected_symbols = set()
            
            # Prioridad 1: Señales FUERTE (hasta 3)
            fuerte_count = 0
            for signal in prioritized_signals:
                if signal.get('confidence_level') == 'FUERTE' and fuerte_count < 3:
                    symbol = signal.get('symbol')
                    if symbol not in selected_symbols:
                        final_signals.append(signal)
                        selected_symbols.add(symbol)
                        fuerte_count += 1
                        remaining_slots -= 1
                        if remaining_slots <= 0:
                            break
            
            # Prioridad 2: Señales ALTO (llenar resto)
            if remaining_slots > 0:
                for signal in prioritized_signals:
                    if signal.get('confidence_level') == 'ALTO':
                        symbol = signal.get('symbol')
                        if symbol not in selected_symbols:
                            final_signals.append(signal)
                            selected_symbols.add(symbol)
                            remaining_slots -= 1
                            if remaining_slots <= 0:
                                break
            
            # Prioridad 3: Mejores señales MEDIO si aún hay espacio
            if remaining_slots > 0:
                medio_signals = [s for s in prioritized_signals 
                               if s.get('confidence_level') == 'MEDIO' 
                               and s.get('total_score', 0) >= 65]
                
                for signal in medio_signals:
                    symbol = signal.get('symbol')
                    if symbol not in selected_symbols:
                        final_signals.append(signal)
                        selected_symbols.add(symbol)
                        remaining_slots -= 1
                        if remaining_slots <= 0:
                            break
            
            return final_signals
            
        except Exception as e:
            log.error(f"Error seleccionando señales finales: {e}")
            return []
    
    def _format_trading_signal(self, signal: Dict) -> Optional[Dict]:
        """Formatea señal para uso en trading"""
        try:
            trading_signal = {
                # Información básica
                'signal_id': f"{signal.get('symbol')}_{int(datetime.now().timestamp())}",
                'symbol': signal.get('symbol'),
                'timestamp': datetime.now(),
                'signal_type': 'BUY_MOMENTUM',
                
                # Clasificación
                'confidence_level': signal.get('confidence_level'),
                'strength': signal.get('signal_strength'),
                'priority_score': signal.get('priority_score', 0),
                
                # Scoring detallado
                'total_score': signal.get('total_score'),
                'component_scores': {
                    'historical': signal.get('components', {}).get('historical', {}).get('historical_score', 0),
                    'technical': signal.get('components', {}).get('technical', {}).get('technical_score', 0),
                    'confluence': signal.get('components', {}).get('confluence', {}).get('confluence_score', 0)
                },
                
                # Probabilidades y objetivos
                'target_movement': TARGET_MOVEMENT,
                'target_probability': signal.get('target_probability'),
                'recommendation': signal.get('recommendation'),
                
                # Análisis de riesgo
                'risk_factors': signal.get('risk_factors', []),
                'confirmation_signals': signal.get('confirmation_signals', []),
                
                # Resumen ejecutivo
                'analysis_summary': signal.get('analysis_summary', {}),
                
                # Metadatos
                'generation_version': '2.0',
                'valid_until': datetime.now() + timedelta(hours=4),  # Válida por 4 horas
                'status': 'ACTIVE'
            }
            
            return trading_signal
            
        except Exception as e:
            log.error(f"Error formateando señal de trading: {e}")
            return None
    
    def _reset_daily_count_if_needed(self):
        """Resetea contador diario si cambió el día"""
        try:
            current_date = datetime.now().date()
            if current_date != self.last_reset_date:
                self.daily_signal_count = 0
                self.last_reset_date = current_date
                
                # Limpiar señales antiguas (más de 24 horas)
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.generated_signals = [
                    s for s in self.generated_signals 
                    if s.get('timestamp', datetime.now()) > cutoff_time
                ]
                
                log.info(f"🔄 Contador diario reseteado para {current_date}")
                
        except Exception as e:
            log.error(f"Error reseteando contador diario: {e}")
    
    def get_daily_summary(self) -> Dict:
        """Obtiene resumen de señales del día"""
        try:
            today = datetime.now().date()
            today_signals = [
                s for s in self.generated_signals 
                if s.get('timestamp', datetime.now()).date() == today
            ]
            
            # Contar por nivel de confianza
            confidence_counts = {}
            for level in ['FUERTE', 'ALTO', 'MEDIO', 'DÉBIL']:
                confidence_counts[level] = len([
                    s for s in today_signals 
                    if s.get('confidence_level') == level
                ])
            
            return {
                'date': today,
                'total_signals': len(today_signals),
                'target_signals': TARGET_DAILY_SIGNALS,
                'remaining_slots': max(0, TARGET_DAILY_SIGNALS - self.daily_signal_count),
                'confidence_breakdown': confidence_counts,
                'avg_score': sum(s.get('total_score', 0) for s in today_signals) / len(today_signals) if today_signals else 0,
                'avg_probability': sum(s.get('target_probability', 0) for s in today_signals) / len(today_signals) if today_signals else 0
            }
            
        except Exception as e:
            log.error(f"Error generando resumen diario: {e}")
            return {}
    
    def get_active_signals(self) -> List[Dict]:
        """Obtiene señales actualmente activas"""
        try:
            current_time = datetime.now()
            active_signals = [
                s for s in self.generated_signals
                if (s.get('status') == 'ACTIVE' and 
                    s.get('valid_until', current_time) > current_time)
            ]
            
            return active_signals
            
        except Exception as e:
            log.error(f"Error obteniendo señales activas: {e}")
            return []
