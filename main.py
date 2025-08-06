"""
Bot principal de detección de momentum crypto.
Punto de entrada que coordina todos los componentes del sistema.
"""

import asyncio
import signal
import sys
from typing import Dict, List
from datetime import datetime

from data.data_fetcher import MassiveDataCollector
from strategies.momentum_strategy import MomentumAnalyzer
from config.trading_config import config
from utils.logger import log


class CryptoMomentumBot:
    """Bot principal que coordina la detección de momentum en tiempo real"""
    
    def __init__(self):
        # Componentes principales
        self.data_collector = MassiveDataCollector()
        self.momentum_analyzer = MomentumAnalyzer()
        
        # Estado del bot
        self.running = False
        self.analysis_cycle_count = 0
        self.last_analysis_time = None
        
        # Resultados
        self.current_opportunities: Dict[str, Dict] = {}
        self.top_opportunities: List[Dict] = []
        
    async def initialize(self):
        """Inicializa todos los componentes del bot"""
        try:
            log.info("🚀 Inicializando Crypto Momentum Bot...")
            
            # Validar configuración
            config.validate()
            log.info("✅ Configuración validada")
            
            # Inicializar recolector de datos
            await self.data_collector.initialize()
            log.info("✅ Recolector de datos inicializado")
            
            # Registrar callback para procesar datos
            self.data_collector.register_callback(self._on_new_data)
            log.info("✅ Callbacks registrados")
            
            log.info("🎯 Bot inicializado correctamente")
            
        except Exception as e:
            log.error(f"❌ Error en inicialización: {e}")
            raise
    
    async def start(self):
        """Inicia el bot y todos sus procesos"""
        try:
            log.info("🔥 Iniciando Crypto Momentum Bot...")
            
            # Configurar handlers para cierre graceful
            self._setup_signal_handlers()
            
            # Inicializar
            await self.initialize()
            
            # Marcar como running
            self.running = True
            
            # Iniciar recolección de datos
            await self.data_collector.start()
            
            # Iniciar ciclo principal de análisis
            analysis_task = asyncio.create_task(self._main_analysis_loop())
            
            # Iniciar ciclo de reportes
            report_task = asyncio.create_task(self._reporting_loop())
            
            log.info("🌟 Bot ejecutándose - Presiona Ctrl+C para detener")
            
            # Esperar a que termine
            await asyncio.gather(analysis_task, report_task)
            
        except KeyboardInterrupt:
            log.info("🛑 Deteniendo bot por solicitud del usuario...")
        except Exception as e:
            log.error(f"❌ Error fatal en bot: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Detiene el bot de forma graceful"""
        try:
            log.info("🔄 Deteniendo Crypto Momentum Bot...")
            
            self.running = False
            
            # Detener recolector de datos
            await self.data_collector.stop()
            
            log.info("✅ Bot detenido correctamente")
            
        except Exception as e:
            log.error(f"Error deteniendo bot: {e}")
    
    def _setup_signal_handlers(self):
        """Configura handlers para señales del sistema"""
        def signal_handler(signum, frame):
            log.info(f"Señal {signum} recibida, deteniendo bot...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _on_new_data(self, data_type: str, symbol: str, data: Dict):
        """Callback llamado cuando llegan nuevos datos"""
        try:
            # Solo procesar actualizaciones de ticker para triggers inmediatos
            if data_type == 'ticker':
                # Verificar si hay cambios significativos que requieran análisis inmediato
                if self._should_trigger_immediate_analysis(symbol, data):
                    log.debug(f"Trigger inmediato para {symbol}")
                    # Aquí podrías implementar análisis inmediato para símbolos específicos
                    
        except Exception as e:
            log.error(f"Error procesando datos de {symbol}: {e}")
    
    def _should_trigger_immediate_analysis(self, symbol: str, ticker_data: Dict) -> bool:
        """Determina si un símbolo requiere análisis inmediato"""
        try:
            # Triggers para análisis inmediato:
            # 1. Cambio de precio > 5% en poco tiempo
            price_change = abs(ticker_data.get('price_change', 0))
            if price_change > 5:
                return True
            
            # 2. Volumen spike muy alto
            # (Se implementaría comparando con datos históricos)
            
            return False
            
        except Exception as e:
            log.error(f"Error evaluando trigger para {symbol}: {e}")
            return False
    
    async def _main_analysis_loop(self):
        """Ciclo principal de análisis de momentum"""
        log.info(f"🔍 Iniciando ciclo de análisis (cada {config.update_interval} segundos)")
        
        while self.running:
            try:
                cycle_start = datetime.now()
                log.info(f"📊 Iniciando ciclo de análisis #{self.analysis_cycle_count + 1}")
                
                # Obtener datos de todos los símbolos
                all_symbols_data = self.data_collector.get_all_symbols_data()
                
                if not all_symbols_data:
                    log.warning("No hay datos disponibles para análisis")
                    await asyncio.sleep(config.update_interval)
                    continue
                
                # Analizar símbolos en paralelo (en lotes para no sobrecargar)
                await self._analyze_symbols_batch(all_symbols_data)
                
                # Actualizar oportunidades top
                self._update_top_opportunities()
                
                # Generar alertas si hay nuevas oportunidades fuertes
                await self._check_and_send_alerts()
                
                # Estadísticas del ciclo
                cycle_duration = (datetime.now() - cycle_start).total_seconds()
                self.analysis_cycle_count += 1
                self.last_analysis_time = datetime.now()
                
                log.info(f"✅ Ciclo #{self.analysis_cycle_count} completado en {cycle_duration:.2f}s")
                
                # Esperar hasta el próximo ciclo
                await asyncio.sleep(max(0, config.update_interval - cycle_duration))
                
            except Exception as e:
                log.error(f"Error en ciclo de análisis: {e}")
                await asyncio.sleep(5)  # Pausa corta antes de reintentar
    
    async def _analyze_symbols_batch(self, symbols_data: Dict[str, Dict]):
        """Analiza símbolos en lotes para optimizar performance"""
        try:
            symbols = list(symbols_data.keys())
            batch_size = 50  # Procesar 50 símbolos por lote
            
            log.info(f"Analizando {len(symbols)} símbolos en lotes de {batch_size}")
            
            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                
                # Crear tareas para análisis paralelo
                analysis_tasks = []
                for symbol in batch_symbols:
                    symbol_data = symbols_data[symbol]
                    if self._has_sufficient_data(symbol_data):
                        task = self.momentum_analyzer.analyze_symbol_momentum(symbol, symbol_data)
                        analysis_tasks.append(task)
                
                # Ejecutar análisis en paralelo
                if analysis_tasks:
                    results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
                    
                    # Procesar resultados
                    for result in results:
                        if isinstance(result, Exception):
                            log.error(f"Error en análisis: {result}")
                        elif isinstance(result, dict) and 'symbol' in result:
                            symbol = result['symbol']
                            if 'error' not in result:
                                self.current_opportunities[symbol] = result
                
                # Pausa pequeña entre lotes
                await asyncio.sleep(0.1)
                
        except Exception as e:
            log.error(f"Error en análisis por lotes: {e}")
    
    def _has_sufficient_data(self, symbol_data: Dict) -> bool:
        """Verifica si un símbolo tiene datos suficientes para análisis"""
        try:
            # Verificar estructura básica
            if 'ticker' not in symbol_data or 'klines' not in symbol_data:
                return False
            
            # Verificar timeframes necesarios
            required_timeframes = ['1m', '5m', '15m']
            for tf in required_timeframes:
                if tf not in symbol_data['klines']:
                    return False
                if len(symbol_data['klines'][tf]) < 30:  # Mínimo 30 velas
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _update_top_opportunities(self):
        """Actualiza la lista de mejores oportunidades"""
        try:
            # Clasificar oportunidades por score
            opportunities = []
            
            for symbol, analysis in self.current_opportunities.items():
                if 'error' not in analysis:
                    score = analysis.get('momentum_score', {}).get('total_score', 0)
                    classification = analysis.get('classification', 'DÉBIL')
                    prob_4h = analysis.get('probability_7_5', {}).get('timeframe_probabilities', {}).get('4h', 0)
                    
                    opportunities.append({
                        'symbol': symbol,
                        'score': score,
                        'classification': classification,
                        'probability_4h': prob_4h,
                        'analysis': analysis
                    })
            
            # Ordenar por score descendente
            opportunities.sort(key=lambda x: x['score'], reverse=True)
            
            # Mantener top 50
            self.top_opportunities = opportunities[:50]
            
            # Log de estadísticas
            strong_count = len([o for o in opportunities if o['classification'] == 'FUERTE'])
            high_count = len([o for o in opportunities if o['classification'] == 'ALTO'])
            
            log.info(f"🎯 Oportunidades detectadas: {strong_count} FUERTES, {high_count} ALTAS de {len(opportunities)} total")
            
        except Exception as e:
            log.error(f"Error actualizando top oportunidades: {e}")
    
    async def _check_and_send_alerts(self):
        """Verifica y envía alertas para nuevas oportunidades"""
        try:
            # Filtrar oportunidades que requieren alerta
            alert_opportunities = [
                opp for opp in self.top_opportunities[:10]  # Top 10
                if opp['classification'] in ['FUERTE', 'ALTO'] and opp['score'] >= 70
            ]
            
            if alert_opportunities:
                log.info(f"🚨 {len(alert_opportunities)} oportunidades de alta calidad detectadas")
                
                # Aquí se implementaría el sistema de alertas (Telegram, Discord, etc.)
                for opp in alert_opportunities[:3]:  # Solo top 3 para evitar spam
                    await self._send_opportunity_alert(opp)
                    
        except Exception as e:
            log.error(f"Error enviando alertas: {e}")
    
    async def _send_opportunity_alert(self, opportunity: Dict):
        """Envía alerta para una oportunidad específica"""
        try:
            symbol = opportunity['symbol']
            score = opportunity['score']
            classification = opportunity['classification']
            prob_4h = opportunity['probability_4h']
            
            # Crear mensaje de alerta
            alert_message = f"""
🚀 OPORTUNIDAD DETECTADA

💰 Símbolo: {symbol}
🎯 Clasificación: {classification}
📊 Score: {score}/100
🔥 Probabilidad +7.5% (4h): {prob_4h:.1f}%

⏰ {datetime.now().strftime('%H:%M:%S')}
            """.strip()
            
            log.info(f"ALERTA: {alert_message}")
            
            # Aquí implementarías el envío real (Telegram, Discord, etc.)
            
        except Exception as e:
            log.error(f"Error enviando alerta individual: {e}")
    
    async def _reporting_loop(self):
        """Ciclo de reportes periódicos"""
        while self.running:
            try:
                await asyncio.sleep(300)  # Reporte cada 5 minutos
                
                if self.current_opportunities:
                    await self._generate_periodic_report()
                    
            except Exception as e:
                log.error(f"Error en ciclo de reportes: {e}")
                await asyncio.sleep(60)
    
    async def _generate_periodic_report(self):
        """Genera reporte periódico del estado del bot"""
        try:
            # Obtener resumen de mercado
            market_summary = self.momentum_analyzer.get_market_momentum_summary()
            
            if 'error' not in market_summary:
                strong_count = market_summary.get('strong_opportunities', 0)
                high_count = market_summary.get('high_opportunities', 0)
                total_analyzed = market_summary.get('total_analyzed', 0)
                avg_score = market_summary.get('average_score', 0)
                
                # Obtener datos de mercado general
                market_overview = self.data_collector.get_market_overview()
                coverage = market_overview.get('coverage_percentage', 0)
                
                log.info(f"""
📈 REPORTE PERIÓDICO - {datetime.now().strftime('%H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Oportunidades: {strong_count} FUERTES | {high_count} ALTAS
📊 Total analizados: {total_analyzed} símbolos
🔍 Cobertura: {coverage:.1f}%
📈 Score promedio: {avg_score:.1f}/100
🔄 Ciclos completados: {self.analysis_cycle_count}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                """.strip())
                
                # Mostrar top 5 oportunidades
                if self.top_opportunities:
                    log.info("🏆 TOP 5 OPORTUNIDADES:")
                    for i, opp in enumerate(self.top_opportunities[:5], 1):
                        log.info(f"  {i}. {opp['symbol']}: {opp['score']}/100 ({opp['classification']}) - {opp['probability_4h']:.1f}%")
                        
        except Exception as e:
            log.error(f"Error generando reporte: {e}")
    
    def get_current_opportunities(self) -> List[Dict]:
        """Obtiene las oportunidades actuales"""
        return self.top_opportunities.copy()
    
    def get_bot_status(self) -> Dict:
        """Obtiene estado actual del bot"""
        return {
            'running': self.running,
            'cycles_completed': self.analysis_cycle_count,
            'last_analysis': self.last_analysis_time,
            'opportunities_count': len(self.current_opportunities),
            'top_opportunities_count': len(self.top_opportunities),
            'data_coverage': self.data_collector.get_market_overview().get('coverage_percentage', 0)
        }


async def main():
    """Función principal"""
    try:
        # Crear e iniciar bot
        bot = CryptoMomentumBot()
        await bot.start()
        
    except KeyboardInterrupt:
        log.info("Bot detenido por el usuario")
    except Exception as e:
        log.error(f"Error fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Configurar event loop para Windows
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Ejecutar bot
    asyncio.run(main())
