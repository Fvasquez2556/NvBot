"""
Motor Principal de Detección de Momentum v2.0
Coordina el análisis completo: Histórico + Técnico + Confluencia = Señal Final
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from core.historical_analyzer import HistoricalAnalyzer
from core.technical_analyzer import TechnicalAnalyzer
from indicators.confluence_validator import ConfluenceValidator
from core.signal_unifier import SignalUnifier
from config.parameters import TARGET_DAILY_SIGNALS, TARGET_MOVEMENT
from utils.logger import log


class MomentumDetector:
    """
    Motor principal que coordina todo el análisis de momentum.
    Integra las 3 secciones principales para generar señales finales.
    """
    
    def __init__(self):
        # Inicializar componentes principales
        self.historical_analyzer = HistoricalAnalyzer()
        self.technical_analyzer = TechnicalAnalyzer()
        self.confluence_validator = ConfluenceValidator()
        self.signal_unifier = SignalUnifier()
        
        # Estado del detector
        self.analysis_count = 0
        self.last_analysis_time = None
        self.detected_opportunities: Dict[str, Dict] = {}
        self.daily_signals_count = 0
        
        # Cache para optimizar análisis
        self.symbol_cache: Dict[str, Dict] = {}
        self.cache_duration = 300  # 5 minutos
        
    async def detect_momentum_opportunities(self, market_data: Dict) -> List[Dict]:
        """
        Detecta oportunidades de momentum en el mercado completo.
        
        Args:
            market_data: Dict con datos de todos los símbolos del mercado
            
        Returns:
            List de oportunidades ordenadas por score total
        """
        try:
            log.info(f"🔍 Iniciando detección de momentum para {len(market_data)} símbolos")
            
            opportunities = []
            analysis_tasks = []
            
            # Crear tareas de análisis en paralelo (limitado para no sobrecargar)
            semaphore = asyncio.Semaphore(10)  # Máximo 10 análisis concurrentes
            
            for symbol, symbol_data in market_data.items():
                if self._should_analyze_symbol(symbol, symbol_data):
                    task = self._analyze_symbol_with_semaphore(
                        semaphore, symbol, symbol_data
                    )
                    analysis_tasks.append(task)
            
            # Ejecutar análisis en paralelo
            if analysis_tasks:
                log.info(f"🚀 Analizando {len(analysis_tasks)} símbolos en paralelo")
                results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
                
                # Procesar resultados
                for result in results:
                    if isinstance(result, Exception):
                        log.error(f"Error en análisis paralelo: {result}")
                        continue
                    
                    if result and result.get('total_score', 0) > 0:
                        opportunities.append(result)
            
            # Ordenar por score total (descendente)
            opportunities.sort(key=lambda x: x.get('total_score', 0), reverse=True)
            
            # Actualizar estado
            self.analysis_count += 1
            self.last_analysis_time = datetime.now()
            
            # Filtrar mejores oportunidades
            top_opportunities = self._filter_top_opportunities(opportunities)
            
            log.info(f"✅ Detección completada: {len(top_opportunities)}/{len(opportunities)} oportunidades seleccionadas")
            
            return top_opportunities
            
        except Exception as e:
            log.error(f"Error en detección de momentum: {e}")
            return []
    
    async def _analyze_symbol_with_semaphore(self, semaphore: asyncio.Semaphore,
                                           symbol: str, symbol_data: Dict) -> Optional[Dict]:
        """Analiza un símbolo con control de concurrencia"""
        async with semaphore:
            return await self.analyze_symbol_complete(symbol, symbol_data)
    
    async def analyze_symbol_complete(self, symbol: str, symbol_data: Dict) -> Optional[Dict]:
        """
        Análisis completo de un símbolo: Histórico + Técnico + Confluencia + Unificación
        
        Args:
            symbol: Símbolo a analizar
            symbol_data: Datos completos del símbolo
            
        Returns:
            Dict con análisis completo y señal unificada, o None si no hay oportunidad
        """
        try:
            log.debug(f"📊 Análisis completo iniciado para {symbol}")
            
            # Verificar cache
            cached_result = self._get_cached_analysis(symbol)
            if cached_result:
                log.debug(f"📋 Usando análisis cacheado para {symbol}")
                return cached_result
            
            # 1. SECCIÓN 1: Análisis Histórico (0-25 puntos)
            log.debug(f"📈 Análisis histórico {symbol}")
            historical_result = self.historical_analyzer.analyze_symbol_history(
                symbol, symbol_data.get('historical_data', {})
            )
            
            # 2. SECCIÓN 2: Análisis Técnico (0-50 puntos)
            log.debug(f"⚙️ Análisis técnico {symbol}")
            technical_result = await self.technical_analyzer.analyze_symbol_technicals(
                symbol, symbol_data.get('current_data', {})
            )
            
            # 3. CONFLUENCIA Multi-Timeframe (0-25 puntos)
            log.debug(f"🔗 Análisis confluencia {symbol}")
            confluence_result = await self.confluence_validator.validate_multi_timeframe_confluence(
                symbol, symbol_data.get('timeframe_data', {})
            )
            
            # 4. UNIFICACIÓN: Combinar las 3 secciones
            log.debug(f"🎯 Unificando señales {symbol}")
            unified_signal = self.signal_unifier.unify_signals(
                symbol, historical_result, technical_result, confluence_result
            )
            
            # Verificar si es una oportunidad válida
            if self._is_valid_opportunity(unified_signal):
                # Cachear resultado
                self._cache_analysis(symbol, unified_signal)
                
                log.info(f"✅ Oportunidad detectada: {self.signal_unifier.get_signal_summary(unified_signal)}")
                return unified_signal
            else:
                log.debug(f"❌ {symbol} no cumple criterios mínimos")
                return None
                
        except Exception as e:
            log.error(f"Error en análisis completo {symbol}: {e}")
            return None
    
    def _should_analyze_symbol(self, symbol: str, symbol_data: Dict) -> bool:
        """Determina si un símbolo debe ser analizado"""
        try:
            # Filtros básicos
            if not symbol.endswith('USDT'):
                return False
            
            # Verificar volumen mínimo
            volume_24h = symbol_data.get('volume_24h', 0)
            if volume_24h < 1_000_000:  # $1M mínimo
                return False
            
            # Verificar precio dentro de rango
            current_price = symbol_data.get('price', 0)
            if current_price < 0.01 or current_price > 1000:
                return False
            
            # Verificar que tengamos datos suficientes
            required_data = ['historical_data', 'current_data', 'timeframe_data']
            for data_type in required_data:
                if data_type not in symbol_data or not symbol_data[data_type]:
                    return False
            
            return True
            
        except Exception as e:
            log.error(f"Error verificando símbolo {symbol}: {e}")
            return False
    
    def _is_valid_opportunity(self, signal: Dict) -> bool:
        """Determina si una señal unificada es una oportunidad válida"""
        try:
            # Criterios mínimos para considerar oportunidad
            total_score = signal.get('total_score', 0)
            confidence_level = signal.get('confidence_level', 'DÉBIL')
            recommendation = signal.get('recommendation', 'HOLD')
            
            # Score mínimo
            if total_score < 30:
                return False
            
            # Solo señales de compra o vigilancia fuerte
            if recommendation not in ['STRONG_BUY', 'BUY', 'WEAK_BUY', 'WATCH']:
                return False
            
            # Para señales débiles, requerir score más alto
            if confidence_level == 'DÉBIL' and total_score < 40:
                return False
            
            # Verificar que no haya errores críticos
            if 'error' in signal:
                return False
            
            return True
            
        except Exception as e:
            log.error(f"Error validando oportunidad: {e}")
            return False
    
    def _filter_top_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        """Filtra las mejores oportunidades según criterios de calidad"""
        try:
            if not opportunities:
                return []
            
            # Separar por nivel de confianza
            strong_signals = [op for op in opportunities if op.get('confidence_level') == 'FUERTE']
            high_signals = [op for op in opportunities if op.get('confidence_level') == 'ALTO']
            medium_signals = [op for op in opportunities if op.get('confidence_level') == 'MEDIO']
            
            # Seleccionar las mejores de cada categoría
            top_opportunities = []
            
            # Todas las señales fuertes (máximo 5)
            top_opportunities.extend(strong_signals[:5])
            
            # Mejores señales altas (máximo 3 adicionales)
            remaining_slots = TARGET_DAILY_SIGNALS - len(top_opportunities)
            if remaining_slots > 0:
                top_opportunities.extend(high_signals[:min(3, remaining_slots)])
            
            # Si aún tenemos espacio, agregar mejores señales medias
            remaining_slots = TARGET_DAILY_SIGNALS - len(top_opportunities)
            if remaining_slots > 0:
                # Solo señales medias con score alto
                high_medium_signals = [op for op in medium_signals if op.get('total_score', 0) >= 60]
                top_opportunities.extend(high_medium_signals[:remaining_slots])
            
            # Limitar a objetivo diario + margen
            max_signals = TARGET_DAILY_SIGNALS + 2  # Margen de 2 señales adicionales
            return top_opportunities[:max_signals]
            
        except Exception as e:
            log.error(f"Error filtrando oportunidades: {e}")
            return opportunities[:TARGET_DAILY_SIGNALS]
    
    def _get_cached_analysis(self, symbol: str) -> Optional[Dict]:
        """Obtiene análisis cacheado si está vigente"""
        try:
            if symbol not in self.symbol_cache:
                return None
            
            cached_data = self.symbol_cache[symbol]
            cache_time = cached_data.get('cache_time')
            
            if cache_time:
                elapsed = (datetime.now() - cache_time).total_seconds()
                if elapsed < self.cache_duration:
                    return cached_data.get('analysis')
            
            # Cache expirado, eliminar
            del self.symbol_cache[symbol]
            return None
            
        except Exception as e:
            log.error(f"Error obteniendo cache {symbol}: {e}")
            return None
    
    def _cache_analysis(self, symbol: str, analysis: Dict):
        """Cachea análisis para evitar recálculos"""
        try:
            self.symbol_cache[symbol] = {
                'analysis': analysis,
                'cache_time': datetime.now()
            }
            
            # Limpiar cache viejo
            self._cleanup_cache()
            
        except Exception as e:
            log.error(f"Error cacheando análisis {symbol}: {e}")
    
    def _cleanup_cache(self):
        """Limpia entradas de cache expiradas"""
        try:
            current_time = datetime.now()
            expired_symbols = []
            
            for symbol, data in self.symbol_cache.items():
                cache_time = data.get('cache_time')
                if cache_time:
                    elapsed = (current_time - cache_time).total_seconds()
                    if elapsed >= self.cache_duration:
                        expired_symbols.append(symbol)
            
            for symbol in expired_symbols:
                del self.symbol_cache[symbol]
                
        except Exception as e:
            log.error(f"Error limpiando cache: {e}")
    
    async def get_analysis_summary(self) -> Dict:
        """Obtiene resumen del estado actual del detector"""
        try:
            # Señales fuertes del día
            strong_signals = self.signal_unifier.get_strong_signals_today()
            
            # Estadísticas
            cache_size = len(self.symbol_cache)
            
            summary = {
                'analysis_count': self.analysis_count,
                'last_analysis': self.last_analysis_time,
                'daily_strong_signals': len(strong_signals),
                'cache_size': cache_size,
                'detected_opportunities': len(self.detected_opportunities),
                'target_daily_signals': TARGET_DAILY_SIGNALS,
                'target_movement': f"+{TARGET_MOVEMENT}%"
            }
            
            return summary
            
        except Exception as e:
            log.error(f"Error generando resumen: {e}")
            return {}
    
    async def force_analysis_refresh(self):
        """Fuerza actualización de análisis limpiando cache"""
        try:
            self.symbol_cache.clear()
            log.info("🔄 Cache de análisis limpiado - próximo análisis será completo")
            
        except Exception as e:
            log.error(f"Error refrescando análisis: {e}")
    
    def get_top_opportunities_summary(self, count: int = 5) -> List[str]:
        """Obtiene resumen textual de las mejores oportunidades"""
        try:
            recent_signals = self.signal_unifier.get_recent_signals(count * 2)
            
            # Filtrar y ordenar por score
            valid_signals = [s for s in recent_signals if s.get('total_score', 0) >= 50]
            valid_signals.sort(key=lambda x: x.get('total_score', 0), reverse=True)
            
            summaries = []
            for signal in valid_signals[:count]:
                summary = self.signal_unifier.get_signal_summary(signal)
                summaries.append(summary)
            
            return summaries
            
        except Exception as e:
            log.error(f"Error generando resúmenes: {e}")
            return []
