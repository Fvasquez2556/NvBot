"""
Launcher principal que ejecuta el bot y el dashboard simultáneamente.
"""

import asyncio
import threading
import time
import sys
from datetime import datetime

from main import CryptoMomentumBot
from dashboard.web_dashboard import CryptoMomentumDashboard
from utils.logger import log


class BotWithDashboard:
    """Ejecuta bot y dashboard simultáneamente"""
    
    def __init__(self):
        self.bot = None
        self.dashboard = None
        self.bot_task = None
        self.dashboard_thread = None
        self.running = False
    
    async def start(self):
        """Inicia bot y dashboard"""
        try:
            log.info("🚀 Iniciando Crypto Momentum Bot con Dashboard...")
            
            # Crear instancia del bot
            self.bot = CryptoMomentumBot()
            
            # Crear dashboard conectado al bot
            self.dashboard = CryptoMomentumDashboard(bot_instance=self.bot)
            
            # Iniciar dashboard en thread separado
            self.dashboard_thread = threading.Thread(
                target=self._run_dashboard_thread,
                daemon=True
            )
            self.dashboard_thread.start()
            
            # Esperar un poco para que el dashboard se inicie
            await asyncio.sleep(2)
            
            # Iniciar bot
            log.info("🤖 Iniciando bot de momentum...")
            self.running = True
            await self.bot.start()
            
        except KeyboardInterrupt:
            log.info("🛑 Deteniendo sistema por solicitud del usuario...")
        except Exception as e:
            log.error(f"❌ Error fatal: {e}")
        finally:
            await self.stop()
    
    def _run_dashboard_thread(self):
        """Ejecuta dashboard en thread separado"""
        try:
            self.dashboard.run(debug=False)
        except Exception as e:
            log.error(f"Error en dashboard: {e}")
    
    async def stop(self):
        """Detiene bot y dashboard"""
        try:
            log.info("🔄 Deteniendo sistema...")
            
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
    """Función principal"""
    try:
        # Mostrar información de inicio
        print("""
🚀 CRYPTO MOMENTUM BOT v1.0
═══════════════════════════════════════════

📊 Características:
• Análisis de TODOS los pares USDT de Binance
• Detección de momentum +7.5% en tiempo real  
• Clasificación: Débil, Medio, Alto, Fuerte
• Dashboard web interactivo
• Indicadores optimizados para crypto

🌐 Dashboard: http://localhost:8050
📝 Logs: logs/crypto_bot.log

═══════════════════════════════════════════
        """)
        
        # Crear e iniciar sistema
        system = BotWithDashboard()
        await system.start()
        
    except KeyboardInterrupt:
        log.info("Sistema detenido por el usuario")
    except Exception as e:
        log.error(f"Error fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Configurar event loop para Windows
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Ejecutar sistema completo
    asyncio.run(main())
