"""
Obtención de datos masivos de Binance para análisis de momentum.
Maneja todos los pares USDT simultáneamente vía WebSocket.
"""

import asyncio
import json
import websockets
import aiohttp
from typing import Dict, List, Callable, Optional
from datetime import datetime, timedelta
from binance.client import Client
from binance.exceptions import BinanceAPIException

from config.trading_config import config
from config.exchange_config import get_binance_config
from utils.logger import log


class MassiveDataCollector:
    """Recolector de datos masivo para todos los pares USDT de Binance"""
    
    def __init__(self):
        self.binance_config = get_binance_config()
        self.client = Client(
            self.binance_config.api_key,
            self.binance_config.secret_key,
            testnet=self.binance_config.testnet
        )
        
        self.active_pairs: List[str] = []
        self.websocket_connections: Dict[int, websockets.WebSocketServerProtocol] = {}
        self.price_data: Dict[str, Dict] = {}
        self.data_callbacks: List[Callable] = []
        
        self.running = False
        self.last_update = {}
        
    async def initialize(self):
        """Inicializa el recolector obteniendo pares activos"""
        try:
            log.info("Inicializando recolector de datos masivos...")
            await self._get_active_usdt_pairs()
            await self._setup_websocket_connections()
            log.info(f"Inicialización completa. Monitoreando {len(self.active_pairs)} pares USDT")
            
        except Exception as e:
            log.error(f"Error en inicialización: {e}")
            raise
    
    async def _get_active_usdt_pairs(self):
        """Obtiene todos los pares USDT activos de Binance"""
        try:
            log.info("Obteniendo pares USDT activos...")
            
            exchange_info = self.client.get_exchange_info()
            
            filtered_pairs = []
            for symbol_info in exchange_info['symbols']:
                symbol = symbol_info['symbol']
                
                # Filtros básicos
                if (symbol_info['quoteAsset'] == 'USDT' and 
                    symbol_info['status'] == 'TRADING' and
                    symbol_info['isSpotTradingAllowed']):
                    
                    # Filtro de volumen mínimo
                    try:
                        ticker = self.client.get_ticker(symbol=symbol)
                        volume_usdt = float(ticker['quoteVolume'])
                        price = float(ticker['lastPrice'])
                        
                        if (volume_usdt >= config.filters.min_volume_24h and
                            config.filters.min_price <= price <= config.filters.max_price):
                            
                            filtered_pairs.append({
                                'symbol': symbol,
                                'price': price,
                                'volume_24h': volume_usdt
                            })
                            
                    except Exception as e:
                        log.warning(f"Error procesando {symbol}: {e}")
                        continue
            
            # Ordenar por volumen descendente
            filtered_pairs.sort(key=lambda x: x['volume_24h'], reverse=True)
            self.active_pairs = [pair['symbol'] for pair in filtered_pairs]
            
            log.info(f"Pares USDT seleccionados: {len(self.active_pairs)}")
            log.info(f"Top 10 por volumen: {[p['symbol'] for p in filtered_pairs[:10]]}")
            
        except BinanceAPIException as e:
            log.error(f"Error API Binance al obtener pares: {e}")
            raise
        except Exception as e:
            log.error(f"Error inesperado al obtener pares: {e}")
            raise
    
    async def _setup_websocket_connections(self):
        """Configura múltiples conexiones WebSocket para manejar todos los pares"""
        try:
            log.info("Configurando conexiones WebSocket...")
            
            # Dividir pares en lotes (máximo 190 streams por conexión)
            batch_size = config.websocket.max_streams_per_connection
            pair_batches = [
                self.active_pairs[i:i + batch_size] 
                for i in range(0, len(self.active_pairs), batch_size)
            ]
            
            log.info(f"Creando {len(pair_batches)} conexiones WebSocket")
            
            # Crear tareas para cada conexión
            connection_tasks = []
            for i, batch in enumerate(pair_batches):
                task = asyncio.create_task(
                    self._create_websocket_connection(batch, i)
                )
                connection_tasks.append(task)
            
            # Esperar que todas las conexiones estén listas
            await asyncio.gather(*connection_tasks)
            
        except Exception as e:
            log.error(f"Error configurando WebSockets: {e}")
            raise
    
    async def _create_websocket_connection(self, pairs: List[str], connection_id: int):
        """Crea una conexión WebSocket individual para un lote de pares"""
        try:
            # Crear streams para ticker y kline data
            streams = []
            for pair in pairs:
                symbol_lower = pair.lower()
                streams.extend([
                    f"{symbol_lower}@ticker",      # Precio y volumen en tiempo real
                    f"{symbol_lower}@kline_1m",    # Velas 1 minuto para indicadores
                    f"{symbol_lower}@kline_5m",    # Velas 5 minutos
                    f"{symbol_lower}@kline_15m"    # Velas 15 minutos
                ])
            
            # URL del WebSocket
            base_url = self.binance_config.effective_ws_url
            streams_param = "/".join(streams)
            ws_url = f"{base_url}/stream?streams={streams_param}"
            
            log.info(f"Conexión {connection_id}: {len(pairs)} pares, {len(streams)} streams")
            
            while self.running:
                try:
                    async with websockets.connect(
                        ws_url,
                        ping_interval=config.websocket.ping_interval,
                        ping_timeout=config.websocket.connection_timeout
                    ) as websocket:
                        
                        self.websocket_connections[connection_id] = websocket
                        log.info(f"WebSocket {connection_id} conectado exitosamente")
                        
                        async for message in websocket:
                            if not self.running:
                                break
                                
                            await self._process_websocket_message(message, connection_id)
                            
                except websockets.exceptions.ConnectionClosed:
                    log.warning(f"WebSocket {connection_id} desconectado, reintentando...")
                    await asyncio.sleep(5)
                except Exception as e:
                    log.error(f"Error en WebSocket {connection_id}: {e}")
                    await asyncio.sleep(5)
                    
        except Exception as e:
            log.error(f"Error fatal en conexión {connection_id}: {e}")
            raise
    
    async def _process_websocket_message(self, message: str, connection_id: int):
        """Procesa mensajes del WebSocket"""
        try:
            data = json.loads(message)
            
            if 'stream' not in data or 'data' not in data:
                return
            
            stream = data['stream']
            stream_data = data['data']
            
            # Extraer símbolo del stream
            symbol = None
            if '@ticker' in stream:
                symbol = stream_data.get('s')
                await self._process_ticker_data(symbol, stream_data)
            elif '@kline' in stream:
                symbol = stream_data['s']
                await self._process_kline_data(symbol, stream_data)
            
        except json.JSONDecodeError:
            log.warning(f"Mensaje JSON inválido en conexión {connection_id}")
        except Exception as e:
            log.error(f"Error procesando mensaje WebSocket: {e}")
    
    async def _process_ticker_data(self, symbol: str, ticker_data: Dict):
        """Procesa datos de ticker (precio, volumen, cambio)"""
        try:
            current_time = datetime.now()
            
            processed_data = {
                'symbol': symbol,
                'price': float(ticker_data['c']),           # Último precio
                'price_change': float(ticker_data['P']),    # Cambio %
                'volume_24h': float(ticker_data['q']),      # Volumen 24h en USDT
                'volume_change': float(ticker_data['P']),   # Cambio volumen %
                'high_24h': float(ticker_data['h']),       # Máximo 24h
                'low_24h': float(ticker_data['l']),        # Mínimo 24h
                'bid_price': float(ticker_data['b']),      # Mejor bid
                'ask_price': float(ticker_data['a']),      # Mejor ask
                'timestamp': current_time
            }
            
            # Actualizar cache de datos
            if symbol not in self.price_data:
                self.price_data[symbol] = {}
            
            self.price_data[symbol]['ticker'] = processed_data
            self.last_update[symbol] = current_time
            
            # Notificar callbacks
            await self._notify_callbacks('ticker', symbol, processed_data)
            
        except Exception as e:
            log.error(f"Error procesando ticker {symbol}: {e}")
    
    async def _process_kline_data(self, symbol: str, kline_data: Dict):
        """Procesa datos de velas (OHLCV)"""
        try:
            kline = kline_data['k']
            
            # Solo procesar velas cerradas
            if not kline['x']:  # x = is_closed
                return
            
            timeframe = kline['i']  # intervalo (1m, 5m, 15m, etc.)
            
            processed_kline = {
                'symbol': symbol,
                'timeframe': timeframe,
                'open_time': int(kline['t']),
                'close_time': int(kline['T']),
                'open': float(kline['o']),
                'high': float(kline['h']),
                'low': float(kline['l']),
                'close': float(kline['c']),
                'volume': float(kline['v']),
                'quote_volume': float(kline['q']),
                'trades_count': int(kline['n']),
                'timestamp': datetime.now()
            }
            
            # Actualizar cache de datos
            if symbol not in self.price_data:
                self.price_data[symbol] = {}
            if 'klines' not in self.price_data[symbol]:
                self.price_data[symbol]['klines'] = {}
            if timeframe not in self.price_data[symbol]['klines']:
                self.price_data[symbol]['klines'][timeframe] = []
            
            # Mantener últimas 200 velas por timeframe
            klines_list = self.price_data[symbol]['klines'][timeframe]
            klines_list.append(processed_kline)
            if len(klines_list) > 200:
                klines_list.pop(0)
            
            # Notificar callbacks
            await self._notify_callbacks('kline', symbol, processed_kline)
            
        except Exception as e:
            log.error(f"Error procesando kline {symbol}: {e}")
    
    async def _notify_callbacks(self, data_type: str, symbol: str, data: Dict):
        """Notifica a todos los callbacks registrados"""
        for callback in self.data_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data_type, symbol, data)
                else:
                    callback(data_type, symbol, data)
            except Exception as e:
                log.error(f"Error en callback: {e}")
    
    def register_callback(self, callback: Callable):
        """Registra un callback para recibir datos"""
        self.data_callbacks.append(callback)
        log.info(f"Callback registrado: {callback.__name__}")
    
    def get_symbol_data(self, symbol: str) -> Optional[Dict]:
        """Obtiene datos actuales de un símbolo"""
        return self.price_data.get(symbol)
    
    def get_all_symbols_data(self) -> Dict[str, Dict]:
        """Obtiene datos de todos los símbolos"""
        return self.price_data.copy()
    
    async def start(self):
        """Inicia la recolección de datos"""
        self.running = True
        log.info("Iniciando recolección de datos masivos...")
        await self.initialize()
    
    async def stop(self):
        """Detiene la recolección de datos"""
        self.running = False
        log.info("Deteniendo recolección de datos...")
        
        # Cerrar conexiones WebSocket
        for connection_id, websocket in self.websocket_connections.items():
            try:
                await websocket.close()
                log.info(f"WebSocket {connection_id} cerrado")
            except Exception as e:
                log.error(f"Error cerrando WebSocket {connection_id}: {e}")
        
        self.websocket_connections.clear()
        log.info("Recolección de datos detenida")
    
    def get_market_overview(self) -> Dict:
        """Obtiene resumen del mercado"""
        try:
            total_pairs = len(self.active_pairs)
            active_data = len([s for s in self.price_data.keys() 
                             if 'ticker' in self.price_data[s]])
            
            # Calcular estadísticas básicas
            gainers = []
            losers = []
            high_volume = []
            
            for symbol, data in self.price_data.items():
                if 'ticker' in data:
                    ticker = data['ticker']
                    change = ticker['price_change']
                    volume = ticker['volume_24h']
                    
                    if change > 0:
                        gainers.append((symbol, change))
                    elif change < 0:
                        losers.append((symbol, change))
                    
                    if volume > config.filters.min_volume_24h * 5:  # 5x volumen mínimo
                        high_volume.append((symbol, volume))
            
            # Ordenar por cambio/volumen
            gainers.sort(key=lambda x: x[1], reverse=True)
            losers.sort(key=lambda x: x[1])
            high_volume.sort(key=lambda x: x[1], reverse=True)
            
            return {
                'total_pairs': total_pairs,
                'active_data': active_data,
                'coverage_percentage': (active_data / total_pairs) * 100 if total_pairs > 0 else 0,
                'top_gainers': gainers[:10],
                'top_losers': losers[:10],
                'high_volume': high_volume[:10],
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            log.error(f"Error generando resumen de mercado: {e}")
            return {}
