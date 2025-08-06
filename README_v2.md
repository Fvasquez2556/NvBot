# Crypto Momentum Bot v2.0 🚀

Bot de detección de momentum alcista para criptomonedas que analiza todos los pares USDT de Binance para detectar oportunidades de subida +7.5%. Genera mínimo 3 señales diarias clasificadas como: **Débil, Medio, Alto, Fuerte**.

## 🆕 Novedades v2.0

### Arquitectura Completamente Reestructurada
- **Solo momentum ALCISTA** (eliminado análisis bajista)
- **Sistema de confluencia multi-timeframe**: 5m, 15m, 1h, 4h
- **Análisis histórico de patrones integrado**
- **Lógica de unificación simplificada**
- **Sistema de scoring 0-100 puntos**

### Nuevos Componentes

#### 🔍 Core Components
- **HistoricalAnalyzer**: Análisis histórico y detección de patrones (0-25 puntos)
- **TechnicalAnalyzer**: Indicadores técnicos momentum (0-50 puntos)  
- **ConfluenceValidator**: Validación multi-timeframe (0-25 puntos)
- **SignalUnifier**: Unifica las 3 secciones para señal final
- **MomentumDetector**: Motor principal de detección

#### 📊 Indicators
- **RSI Crypto-Optimized**: Umbrales 25/75 
- **MACD Sensitive**: Configuración 3-10-16
- **Volume Spike Detector**: Threshold 300%+
- **Multi-Timeframe Confluence**: 4 timeframes simultáneos

#### 🎯 Signals
- **SignalGenerator**: Genera señales finales optimizadas
- **Confidence Classifier**: Clasificación Débil→Fuerte

## 📈 Sistema de Scoring

### Distribución de Puntos (0-100)
- **Histórico**: 25 puntos máximo
  - Promedios de precio vs actual: 8 pts
  - Análisis de picos: 10 pts
  - Patrones de momentum: 7 pts

- **Técnico**: 50 puntos máximo
  - RSI: 15 pts máximo
  - MACD: 20 pts máximo
  - Volumen: 15 pts máximo

- **Confluencia**: 25 puntos máximo
  - Timeframes alcistas: 15 pts
  - Fuerza promedio: 6 pts
  - Consistencia: 4 pts

### Niveles de Confianza
- **FUERTE** (85-100): Alta probabilidad +7.5%
- **ALTO** (70-84): Buena probabilidad +7.5%
- **MEDIO** (50-69): Probabilidad moderada
- **DÉBIL** (30-49): Baja probabilidad

## 🛠️ Instalación

```bash
# Clonar repositorio
git clone <repository-url>
cd binance_intraday_bot

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de Binance
```

## ⚙️ Configuración

### Variables de Entorno (.env)
```env
BINANCE_API_KEY=tu_api_key
BINANCE_SECRET_KEY=tu_secret_key
BINANCE_TESTNET=false
MIN_VOLUME_24H=1000000
```

### Parámetros Principales (config/parameters.py)
```python
# Indicadores Técnicos
RSI_OVERSOLD = 25
RSI_OVERBOUGHT = 75
MACD_FAST = 3
MACD_SLOW = 10
MACD_SIGNAL = 16

# Volume Analysis
VOLUME_SPIKE_THRESHOLD = 3.0  # 300%+
MIN_VOLUME_24H = 1_000_000    # $1M mínimo

# Sistema de Scoring
CONFIDENCE_LEVELS = {
    'FUERTE': (85, 100),
    'ALTO': (70, 84),
    'MEDIO': (50, 69),
    'DÉBIL': (30, 49)
}
```

## 🚀 Uso

### Ejecutar Bot Principal
```bash
python main.py
```

### Ejecutar Demo/Pruebas
```bash
python demo.py
```

### Verificar Instalación
```bash
python install.py
```

## 📊 Estructura v2.0

```
crypto_momentum_bot_v2/
├── core/                      # 🧠 Componentes principales
│   ├── historical_analyzer.py    # Análisis histórico (0-25 pts)
│   ├── technical_analyzer.py     # Análisis técnico (0-50 pts)
│   ├── momentum_detector.py      # Motor principal
│   └── signal_unifier.py         # Unificador de señales
├── data/
│   ├── binance_collector.py      # Adaptador WebSocket Binance
│   ├── data_fetcher.py          # Collector original (reutilizado)
│   └── cache/                    # Cache de datos
├── indicators/
│   ├── confluence_validator.py   # Validación multi-timeframe
│   ├── rsi_optimizer.py         # RSI crypto-optimizado
│   ├── macd_sensitive.py        # MACD 3-10-16 
│   └── volume_analyzer.py       # Análisis de volumen
├── signals/
│   ├── signal_generator.py      # Generador señales finales
│   └── confidence_classifier.py # Clasificador confianza
├── config/
│   ├── parameters.py           # Parámetros v2.0 simplificados
│   └── trading_config.py       # Config original (legacy)
└── utils/
    ├── logger.py               # Sistema de logs
    └── signal_averaging.py     # Promediado (legacy)
```

## 🎯 Características Principales

### 🔍 Análisis Multi-Dimensional
1. **Histórico**: Patrones de precio, picos, promedios
2. **Técnico**: RSI, MACD, volumen optimizados para crypto
3. **Confluencia**: Validación en 4 timeframes simultáneos

### 📈 Optimizado para +7.5%
- Target específico de movimiento +7.5%
- Probabilidades calculadas por señal
- Filtros de calidad estrictos

### ⚡ Tiempo Real
- WebSocket masivo Binance
- Análisis cada 30 segundos
- Cache inteligente para optimización

### 🎨 Dashboard Simplificado
- Señales en tiempo real
- Scoring detallado
- Estadísticas de rendimiento

## 📝 Logs y Monitoreo

### Archivos de Log
- `logs/crypto_bot.log`: Log principal
- `logs/trades.log`: Señales generadas
- `logs/errors.log`: Errores del sistema

### Ejemplo de Output
```
🎯 BTCUSDT | Score: 87/100 | FUERTE | STRONG_BUY | Prob +7.5%: 73.2% | H:22 T:42 C:23
🎯 ETHUSDT | Score: 74/100 | ALTO | BUY | Prob +7.5%: 65.8% | H:18 T:35 C:21
🎯 ADAUSDT | Score: 68/100 | ALTO | WEAK_BUY | Prob +7.5%: 58.4% | H:15 T:32 C:21
```

## 🛡️ Gestión de Riesgos

### Filtros Automáticos
- Volumen mínimo $1M en 24h
- Price range 0.01-1000 USDT
- Score mínimo 30 puntos
- Sin duplicados en 2 horas

### Límites Operativos
- Máximo 3 señales objetivo diario
- Máximo 2 señales adicionales FUERTE
- Válidas por 4 horas máximo

## 🔧 Desarrollo y Contribución

### Estructura Modular
Cada componente es independiente y testeable:
- `HistoricalAnalyzer`: Analiza patrones históricos
- `TechnicalAnalyzer`: Procesa indicadores técnicos
- `ConfluenceValidator`: Valida confluencia multi-timeframe
- `SignalUnifier`: Combina análisis en señal final

### Testing
```bash
# Probar componente individual
python -c "from core.historical_analyzer import HistoricalAnalyzer; print('OK')"

# Probar análisis completo
python demo.py
```

## 📈 Roadmap v2.1

- [ ] Integración Telegram alerts
- [ ] Dashboard web interactivo
- [ ] Backtesting integrado
- [ ] Machine Learning scoring
- [ ] Múltiples exchanges
- [ ] API REST para señales

## 📞 Soporte

Para reportar bugs o solicitar features:
1. Revisar logs en `logs/`
2. Verificar configuración en `config/`
3. Crear issue con detalles completos

---

**Crypto Momentum Bot v2.0** - Sistema inteligente de detección de momentum alcista optimizado para movimientos +7.5% con alta probabilidad de éxito.
