# 🚀 Crypto Momentum Bot - Detector de Oportunidades +7.5%

Bot avanzado para detectar momentum en criptomonedas con potencial de ganancia del 7.5% o más. Analiza TODOS los pares USDT de Binance en tiempo real.

## 🎯 Características Principales

- **Análisis Masivo**: Monitorea todos los pares USDT de Binance simultáneamente (~400+ pares)
- **4 Niveles de Confianza**: Débil, Medio, Alto, Fuerte
- **Predicción +7.5%**: Calcula probabilidad de movimientos alcistas
- **Dashboard Web**: Interfaz interactiva en tiempo real
- **Indicadores Optimizados**: RSI 25/75, MACD 3-10-16, análisis de volumen

## �️ Instalación

### 1. Configurar Entorno

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual (Windows)
.\venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar API Keys (Opcional para datos reales)

1. Ve a [Binance API Management](https://www.binance.com/en/my/settings/api-management)
2. Crea una nueva API Key con permisos de **SOLO LECTURA**
3. Edita el archivo `.env`:

```properties
BINANCE_API_KEY=tu_api_key_aqui
BINANCE_SECRET_KEY=tu_secret_key_aqui
```

## 🚀 Uso

### Modo Demo (Sin API Keys)
```bash
python demo.py
```

### Modo Real (Con API Keys)
```bash
python run_bot.py
```

## 📊 Dashboard Web

Accede a `http://localhost:8050` para ver:
- Tabla de oportunidades en tiempo real
- Gráficas de momentum por criptomoneda
- Alertas automáticas por nivel de confianza
- Historial de movimientos +7.5%

## ⚙️ Configuración

El sistema usa parámetros optimizados para crypto basados en investigación:
- RSI: Umbrales 25/75 (vs 30/70 tradicional)
- MACD: 3-10-16 (vs 12-26-9 tradicional)
- Volume Spike: 200-500% sobre promedio
- Scoring: Sistema de 100 puntos con confluencia

## 📈 Niveles de Momentum

- **🔥 Fuerte (85-100)**: Alta probabilidad +7.5% en 2-8 horas
- **⚡ Alto (70-84)**: Momentum confirmado, revisar en 30 min
- **📈 Medio (50-69)**: Momentum building, monitorear
- **📊 Débil (30-49)**: Señal temprana, confirmar con otros indicadores

## 🛠️ Estructura del Proyecto

```
crypto_momentum_bot/
├── config/          # Configuraciones
├── data/           # Obtención y procesamiento de datos
├── indicators/     # Indicadores técnicos optimizados
├── strategies/     # Lógica de momentum y scoring
├── dashboard/      # Dashboard web tiempo real
├── utils/          # Utilidades compartidas
└── main.py         # Punto de entrada
```
