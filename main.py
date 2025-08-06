"""
Launcher integrado para Bot v2.0 + Dashboard v2.0
Ejecuta ambos componentes simultáneamente
"""

import asyncio
import threading
import time
import sys
import signal
from typing import Dict, List
from datetime import datetime

from data.binance_collector import BinanceCollector
from core.momentum_detector import MomentumDetector
from config.parameters import TARGET_DAILY_SIGNALS, UPDATE_INTERVAL
from dashboard.web_dashboard_v2 import CryptoMomentumDashboardV2
from data.mongodb_manager import mongodb_manager
from utils.logger import log


class CryptoMomentumBot:
    """Bot principal v2.0 que coordina la detección de momentum alcista en tiempo real"""
    
    def __init__(self):
        # Componentes principales v2.0
        self.data_collector = BinanceCollector()
        self.momentum_detector = MomentumDetector()
        
        # Estado del bot
        self.running = False
        self.analysis_cycle_count = 0
        self.last_analysis_time = None
        
        # Resultados v2.0
        self.current_opportunities: Dict[str, Dict] = {}
        self.daily_signals: List[Dict] = []
        
    async def initialize(self):
        """Inicializa todos los componentes del bot v2.0"""
        try:
            log.info("🚀 Inicializando Crypto Momentum Bot v2.0...")
            
            # Conectar a MongoDB
            log.info("💾 Conectando a MongoDB...")
            await mongodb_manager.connect()
            
            # Validar que tenemos los parámetros necesarios
            log.info("✅ Parámetros v2.0 cargados")
            
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
        """Callback llamado cuando llegan nuevos datos v2.0"""
        try:
            # Solo procesar actualizaciones de ticker para triggers inmediatos
            if data_type == 'ticker':
                # Verificar si hay cambios significativos que requieran análisis inmediato
                if self._should_trigger_immediate_analysis(symbol, data):
                    log.debug(f"Trigger inmediato para {symbol}")
                    
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
            
            return False
            
        except Exception as e:
            log.error(f"Error evaluando trigger para {symbol}: {e}")
            return False
    
    async def _main_analysis_loop(self):
        """Ciclo principal de análisis de momentum"""
        log.info(f"🔍 Iniciando ciclo de análisis (cada {UPDATE_INTERVAL} segundos)")
        
        while self.running:
            try:
                cycle_start = datetime.now()
                log.info(f"📊 Iniciando ciclo de análisis #{self.analysis_cycle_count + 1}")
                
                # Obtener datos de todos los símbolos
                all_symbols_data = self.data_collector.get_all_symbols_data()
                
                if not all_symbols_data:
                    log.warning("No hay datos disponibles para análisis")
                    await asyncio.sleep(UPDATE_INTERVAL)
                    continue
                
                # Analizar símbolos en paralelo
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
                await asyncio.sleep(max(0, UPDATE_INTERVAL - cycle_duration))
                
            except Exception as e:
                log.error(f"Error en ciclo de análisis: {e}")
                await asyncio.sleep(5)
    
    async def _analyze_symbols_batch(self, symbols_data: Dict[str, Dict]):
        """Analiza símbolos usando el nuevo MomentumDetector v2.0"""
        try:
            log.info(f"🔍 Detectando oportunidades de momentum en {len(symbols_data)} símbolos")
            
            # Usar el nuevo detector para procesar todos los símbolos
            opportunities = await self.momentum_detector.detect_momentum_opportunities(symbols_data)
            
            # Actualizar oportunidades actuales
            self.current_opportunities.clear()
            for opportunity in opportunities:
                symbol = opportunity.get('symbol')
                if symbol:
                    self.current_opportunities[symbol] = opportunity
            
            # Agregar señales fuertes a la lista diaria
            for opportunity in opportunities:
                if opportunity.get('confidence_level') in ['FUERTE', 'ALTO']:
                    # Verificar que no esté duplicada
                    symbol = opportunity.get('symbol')
                    if not any(s.get('symbol') == symbol for s in self.daily_signals):
                        self.daily_signals.append(opportunity)
                        
                        # Guardar señal fuerte en MongoDB
                        try:
                            await mongodb_manager.save_signal(opportunity)
                            log.info(f"💾 Señal {opportunity.get('confidence_level')} guardada en MongoDB: {symbol}")
                        except Exception as e:
                            log.error(f"❌ Error guardando señal en MongoDB: {e}")
            
            # Mantener solo las mejores señales del día
            if len(self.daily_signals) > TARGET_DAILY_SIGNALS * 2:
                self.daily_signals.sort(key=lambda x: x.get('total_score', 0), reverse=True)
                self.daily_signals = self.daily_signals[:TARGET_DAILY_SIGNALS * 2]
            
            # Log resumen
            if opportunities:
                log.info(f"💡 {len(opportunities)} oportunidades detectadas, "
                        f"{len(self.daily_signals)} señales fuertes acumuladas hoy")
                
        except Exception as e:
            log.error(f"Error en análisis por lotes v2.0: {e}")
    
    def _update_top_opportunities(self):
        """Actualiza la lista de mejores oportunidades v2.0"""
        try:
            if not self.current_opportunities:
                return
            
            # Filtrar oportunidades por score mínimo
            filtered_opportunities = {
                symbol: opp for symbol, opp in self.current_opportunities.items()
                if opp.get('total_score', 0) >= 50
            }
            
            self.current_opportunities = filtered_opportunities
                
        except Exception as e:
            log.error(f"Error actualizando oportunidades: {e}")
    
    async def _check_and_send_alerts(self):
        """Verifica y envía alertas para nuevas oportunidades v2.0"""
        try:
            # Filtrar oportunidades que requieren alerta
            alert_opportunities = [
                opp for opp in self.current_opportunities.values()
                if opp.get('confidence_level') in ['FUERTE', 'ALTO'] and opp.get('total_score', 0) >= 70
            ]
            
            if alert_opportunities:
                log.info(f"🚨 {len(alert_opportunities)} oportunidades de alta calidad detectadas")
                    
        except Exception as e:
            log.error(f"Error enviando alertas: {e}")
    
    async def _reporting_loop(self):
        """Ciclo de reportes periódicos"""
        while self.running:
            try:
                await asyncio.sleep(300)  # Reporte cada 5 minutos
                if self.current_opportunities:
                    log.info(f"📈 {len(self.current_opportunities)} oportunidades activas")
                    
            except Exception as e:
                log.error(f"Error en reporte: {e}")
    
    async def stop(self):
        """Detiene el bot de forma ordenada"""
        try:
            log.info("🛑 Deteniendo Crypto Momentum Bot v2.0...")
            self.running = False
            
            # Cerrar conexión a MongoDB
            await mongodb_manager.close()
            log.info("💾 Conexión MongoDB cerrada")
            
            log.info("✅ Bot detenido correctamente")
            
        except Exception as e:
            log.error(f"❌ Error deteniendo bot: {e}")

    def get_bot_status(self) -> Dict:
        """Obtiene estado actual del bot v2.0"""
        try:
            strong_signals = len([opp for opp in self.current_opportunities.values() 
                                if opp.get('confidence_level') == 'FUERTE'])
            high_signals = len([opp for opp in self.current_opportunities.values() 
                              if opp.get('confidence_level') == 'ALTO'])
            
            return {
                'running': self.running,
                'analysis_cycles': self.analysis_cycle_count,
                'last_analysis': self.last_analysis_time,
                'current_opportunities': len(self.current_opportunities),
                'daily_signals': len(self.daily_signals),
                'strong_signals': strong_signals,
                'high_signals': high_signals,
                'target_daily_signals': TARGET_DAILY_SIGNALS,
                'version': '2.0'
            }
        except Exception as e:
            log.error(f"Error obteniendo estado: {e}")
            return {'error': str(e)}


class BotDashboardLauncher:
    """Ejecuta bot y dashboard v2.0 de forma integrada"""
    
    def __init__(self):
        self.bot = None
        self.dashboard = None
        self.dashboard_thread = None
        self.running = False
        
    async def start_integrated_system(self):
        """Inicia bot y dashboard de forma integrada"""
        try:
            log.info("🚀 Iniciando Crypto Momentum Bot v2.0 + Dashboard...")
            
            # 1. Crear instancia del bot
            self.bot = CryptoMomentumBot()
            
            # 2. Crear dashboard conectado al bot
            self.dashboard = CryptoMomentumDashboardV2(bot_instance=self.bot)
            
            # 3. Iniciar dashboard PRIMERO en thread separado
            log.info("🌐 Iniciando dashboard v2.0...")
            self.dashboard_thread = threading.Thread(
                target=self._run_dashboard_thread,
                daemon=True
            )
            self.dashboard_thread.start()
            log.info("✅ Thread del dashboard iniciado")
            
            # 4. Esperar a que dashboard se inicie
            log.info("⏳ Esperando a que dashboard se inicie...")
            await asyncio.sleep(3)
            log.info("🌐 Dashboard debería estar disponible en: http://localhost:8050")
            
            # 5. Inicializar bot después
            log.info("🤖 Inicializando bot v2.0...")
            await self.bot.initialize()
            
            # 6. Iniciar recolección de datos del bot
            log.info("📊 Iniciando recolección de datos...")
            await self.bot.data_collector.start()
            
            # 7. Marcar como ejecutándose
            self.running = True
            self.bot.running = True
            
            # 8. Iniciar ciclos de análisis
            log.info("🔍 Iniciando análisis de momentum...")
            analysis_task = asyncio.create_task(self.bot._main_analysis_loop())
            report_task = asyncio.create_task(self.bot._reporting_loop())
            
            # 9. Mostrar información del sistema
            self._show_system_info()
            
            # 10. Esperar ejecución
            log.info("✅ Sistema completamente iniciado!")
            log.info("🌐 Dashboard disponible en: http://localhost:8050")
            log.info("🛑 Presiona Ctrl+C para detener")
            
            await asyncio.gather(analysis_task, report_task)
            
        except KeyboardInterrupt:
            log.info("🛑 Deteniendo sistema por solicitud del usuario...")
        except Exception as e:
            log.error(f"❌ Error en sistema integrado: {e}")
        finally:
            await self.stop_integrated_system()
    
    def _run_dashboard_thread(self):
        """Ejecuta dashboard en thread separado"""
        try:
            log.info("🌐 Iniciando thread del dashboard...")
            self.dashboard.run(host='0.0.0.0', port=8050, debug=False)
        except Exception as e:
            log.error(f"❌ Error en dashboard thread: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
    
    def _show_system_info(self):
        """Muestra información del sistema iniciado"""
        log.info("="*60)
        log.info("🎯 CRYPTO MOMENTUM BOT v2.0 - SISTEMA INICIADO")
        log.info("="*60)
        log.info(f"⏰ Hora de inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log.info(f"🔄 Intervalo de análisis: {UPDATE_INTERVAL}s")
        log.info(f"🎯 Target diario: 3 señales fuertes")
        log.info(f"📊 Arquitectura: Histórico + Técnico + Confluencia = Señal Unificada")
        log.info(f"🌐 Dashboard: http://localhost:8050")
        log.info("="*60)
    
    async def stop_integrated_system(self):
        """Detiene todo el sistema de forma graceful"""
        try:
            log.info("🔄 Deteniendo sistema integrado...")
            
            self.running = False
            
            # Detener bot
            if self.bot:
                await self.bot.stop()
            
            # Detener dashboard
            if self.dashboard:
                self.dashboard.stop()
            
            log.info("✅ Sistema detenido correctamente")
            
        except Exception as e:
            log.error(f"Error deteniendo sistema: {e}")


async def main():
    """Función principal del launcher"""
    try:
        # Configurar manejo de señales
        def signal_handler(signum, frame):
            log.info(f"Señal {signum} recibida, deteniendo...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Crear y ejecutar launcher
        launcher = BotDashboardLauncher()
        await launcher.start_integrated_system()
        
    except KeyboardInterrupt:
        log.info("Sistema detenido por el usuario")
    except Exception as e:
        log.error(f"Error fatal en launcher: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                CRYPTO MOMENTUM BOT v2.0                     ║
    ║                   + DASHBOARD INTEGRADO                      ║
    ╠══════════════════════════════════════════════════════════════╣
    ║ 🚀 Iniciando sistema completo...                            ║
    ║ 📊 Dashboard: http://localhost:8050                         ║
    ║ 🛑 Ctrl+C para detener                                      ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Configurar event loop para Windows
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Ejecutar sistema integrado
    asyncio.run(main())
