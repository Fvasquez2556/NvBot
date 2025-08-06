"""
Demo del bot con datos simulados incluyendo sistema de promedios y tendencias
"""

import asyncio
import time
import random
from datetime import datetime
from dashboard.web_dashboard import CryptoMomentumDashboard

def generate_demo_data():
    """Genera datos demo de criptomonedas con información de tendencias"""
    pairs = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT',
        'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT',
        'LINKUSDT', 'UNIUSDT', 'LTCUSDT', 'ALICEUSDT', 'SANDUSDT'
    ]
    
    data = []
    for pair in pairs:
        # Simular datos de momentum actuales
        current_momentum_score = random.randint(30, 95)
        
        # Simular datos promediados (más estables)
        avg_momentum_score = current_momentum_score + random.randint(-10, 10)
        avg_momentum_score = max(20, min(100, avg_momentum_score))
        
        # Clasificación basada en score promedio
        if avg_momentum_score >= 80:
            confidence = "Fuerte"
        elif avg_momentum_score >= 65:
            confidence = "Alto"
        elif avg_momentum_score >= 50:
            confidence = "Medio"
        else:
            confidence = "Débil"
            
        probability = min(avg_momentum_score * 0.8 + random.randint(-10, 10), 95)
        
        # Simular tendencia
        momentum_change = random.uniform(-20, 20)
        if momentum_change > 5:
            trend_direction = "strengthening"
        elif momentum_change < -5:
            trend_direction = "weakening"
        else:
            trend_direction = "stable"
        
        # Simular historial
        history_count = random.randint(3, 15)
        
        data.append({
            'symbol': pair,
            'price': round(random.uniform(0.1, 100), 4),
            'change_24h': round(random.uniform(-15, 25), 2),
            'volume_24h': random.randint(1000000, 100000000),
            
            # Análisis actual (fluctúa más)
            'current_analysis': {
                'momentum_score': current_momentum_score,
                'probability_7_5': max(0, current_momentum_score * 0.7 + random.randint(-15, 15)),
                'confidence_level': confidence,
            },
            
            # Análisis promediado (más estable)
            'display_signal': {
                'momentum_score': avg_momentum_score,
                'probability_7_5': max(0, probability),
                'confidence_level': confidence,
                'rsi_score': random.randint(20, 80),
                'macd_score': random.randint(15, 85),
                'volume_score': random.randint(10, 90),
            },
            
            # Información de tendencia
            'trend': {
                'direction': trend_direction,
                'momentum_change': momentum_change,
                'strength': 'strong' if abs(momentum_change) > 15 else 'moderate'
            },
            
            'history_count': history_count,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            
            # Para compatibilidad con dashboard existente
            'score': avg_momentum_score,
            'classification': confidence.upper(),
            'rsi': random.randint(20, 80),
            'macd_signal': random.choice(['BUY', 'SELL', 'HOLD']),
            'volume_spike': random.choice([True, False])
        })
    
    return data

async def run_demo():
    """Ejecuta el demo con dashboard"""
    print("""
🚀 CRYPTO MOMENTUM BOT v1.0 - MODO DEMO CON TENDENCIAS
═══════════════════════════════════════════════════════
📊 Características:
• Datos simulados para demostración
• Dashboard web interactivo con sistema de tendencias
• Promedios históricos de señales
• Actualización cada 30 segundos

🌐 Dashboard: http://localhost:8050
📝 Presiona Ctrl+C para detener

═══════════════════════════════════════════════════════
""")

    # Crear y configurar el dashboard
    dashboard = CryptoMomentumDashboard()
    
    # Inicializar datos
    initial_data = generate_demo_data()
    dashboard.opportunities_data = initial_data
    dashboard.market_stats = {
        'total_pairs': 400,
        'active_data': len(initial_data),
        'coverage_percentage': (len(initial_data) / 400) * 100,
        'trend_summary': {
            'total_signals': len(initial_data),
            'strengthening': 0,
            'weakening': 0,
            'stable': len(initial_data),
            'strengthening_pct': 0,
            'weakening_pct': 0,
            'stable_pct': 100
        }
    }
    
    # Función para actualizar datos
    async def update_demo_data():
        while True:
            new_data = generate_demo_data()
            
            # Calcular estadísticas de tendencias
            strengthening = sum(1 for item in new_data if item['trend']['direction'] == 'strengthening')
            weakening = sum(1 for item in new_data if item['trend']['direction'] == 'weakening')
            stable = sum(1 for item in new_data if item['trend']['direction'] == 'stable')
            total = len(new_data)
            
            # Actualizar datos del dashboard
            dashboard.opportunities_data = new_data
            dashboard.market_stats = {
                'total_pairs': 400,
                'active_data': len(new_data),
                'coverage_percentage': (len(new_data) / 400) * 100,
                'trend_summary': {
                    'total_signals': total,
                    'strengthening': strengthening,
                    'weakening': weakening,
                    'stable': stable,
                    'strengthening_pct': (strengthening / total) * 100 if total > 0 else 0,
                    'weakening_pct': (weakening / total) * 100 if total > 0 else 0,
                    'stable_pct': (stable / total) * 100 if total > 0 else 0
                }
            }
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Datos actualizados - {len(new_data)} pares analizados")
            print(f"  📈 Fortaleciendo: {strengthening} ({(strengthening/total)*100:.1f}%)")
            print(f"  📉 Debilitando: {weakening} ({(weakening/total)*100:.1f}%)")
            print(f"  📊 Estable: {stable} ({(stable/total)*100:.1f}%)")
            await asyncio.sleep(30)
    
    # Ejecutar dashboard y actualización de datos
    try:
        # Iniciar actualización de datos en background
        update_task = asyncio.create_task(update_demo_data())
        
        # Ejecutar dashboard
        print("📊 Iniciando dashboard en http://localhost:8050")
        print("⚠️  MODO DEMO - Datos simulados para demostración")
        print("💡 Para usar datos reales, configura las API keys en .env")
        print("🔄 Nuevo: Sistema de promedios históricos y análisis de tendencias")
        print("📈 La tabla ahora muestra:")
        print("   • Score Promediado (más estable que el actual)")
        print("   • Tendencia de fuerza (📈📉📊)")
        print("   • Cantidad de análisis en el historial")
        
        dashboard.app.run_server(
            host='localhost',
            port=8050,
            debug=False,
            use_reloader=False
        )
        
    except KeyboardInterrupt:
        print("\n🔄 Deteniendo demo...")
        update_task.cancel()
        print("✅ Demo detenido correctamente")

if __name__ == "__main__":
    asyncio.run(run_demo())
