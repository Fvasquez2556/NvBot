"""
MongoDB Manager para Crypto Momentum Bot
Maneja la persistencia de datos históricos, señales y métricas
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
import json

from utils.logger import log


class MongoDBManager:
    """Gestor de base de datos MongoDB para el bot de trading"""
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017"):
        self.connection_string = connection_string
        self.client = None
        self.db = None
        self.signals_collection = None
        self.market_data_collection = None
        self.analysis_history_collection = None
        self.performance_metrics_collection = None
        
    async def connect(self):
        """Conecta a MongoDB"""
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(self.connection_string)
            self.db = self.client.NvBot
            
            # Configurar collections
            self.signals_collection = self.db.crypto_signals
            self.market_data_collection = self.db.market_data
            self.analysis_history_collection = self.db.analysis_history
            self.performance_metrics_collection = self.db.performance_metrics
            
            # Crear índices para optimizar consultas
            await self._create_indexes()
            
            # Verificar conexión
            await self.client.admin.command('ping')
            log.info("✅ Conectado a MongoDB exitosamente")
            
        except Exception as e:
            log.error(f"❌ Error conectando a MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Desconecta de MongoDB"""
        if self.client:
            self.client.close()
            log.info("MongoDB desconectado")
    
    async def _create_indexes(self):
        """Crea índices para optimizar consultas"""
        try:
            # Índices para crypto_signals
            await self.signals_collection.create_index([
                ("timestamp", DESCENDING),
                ("symbol", ASCENDING)
            ])
            await self.signals_collection.create_index("confidence_level")
            await self.signals_collection.create_index("total_score")
            
            # Índices para market_data
            await self.market_data_collection.create_index([
                ("symbol", ASCENDING),
                ("timestamp", DESCENDING)
            ])
            
            # Índices para analysis_history
            await self.analysis_history_collection.create_index([
                ("timestamp", DESCENDING),
                ("analysis_cycle", ASCENDING)
            ])
            
            log.info("✅ Índices de MongoDB creados")
            
        except Exception as e:
            log.error(f"Error creando índices: {e}")
    
    async def save_signal(self, signal_data: Dict) -> bool:
        """Guarda una señal de trading"""
        try:
            # Agregar timestamp si no existe
            if 'timestamp' not in signal_data:
                signal_data['timestamp'] = datetime.utcnow()
            
            # Agregar ID único para evitar duplicados
            signal_id = f"{signal_data['symbol']}_{signal_data['timestamp'].strftime('%Y%m%d_%H%M%S')}"
            signal_data['signal_id'] = signal_id
            
            await self.signals_collection.insert_one(signal_data)
            log.debug(f"💾 Señal guardada: {signal_data['symbol']} - Score: {signal_data.get('total_score', 'N/A')}")
            return True
            
        except DuplicateKeyError:
            log.debug(f"Señal duplicada ignorada: {signal_data.get('symbol', 'N/A')}")
            return False
        except Exception as e:
            log.error(f"Error guardando señal: {e}")
            return False
    
    async def save_market_data(self, symbol: str, market_data: Dict) -> bool:
        """Guarda datos de mercado"""
        try:
            data = {
                'symbol': symbol,
                'timestamp': datetime.utcnow(),
                'price': market_data.get('price'),
                'volume_24h': market_data.get('volume_24h'),
                'change_24h': market_data.get('change_24h'),
                'high_24h': market_data.get('high_24h'),
                'low_24h': market_data.get('low_24h'),
                'market_cap': market_data.get('market_cap'),
                'raw_data': market_data
            }
            
            await self.market_data_collection.insert_one(data)
            return True
            
        except Exception as e:
            log.error(f"Error guardando datos de mercado para {symbol}: {e}")
            return False
    
    async def save_analysis_cycle(self, cycle_data: Dict) -> bool:
        """Guarda resultados de un ciclo de análisis"""
        try:
            cycle_data['timestamp'] = datetime.utcnow()
            await self.analysis_history_collection.insert_one(cycle_data)
            return True
            
        except Exception as e:
            log.error(f"Error guardando ciclo de análisis: {e}")
            return False
    
    async def get_signals_by_timeframe(self, start_time=None, end_time=None, hours: int = 24, confidence_filter: str = None) -> List[Dict]:
        """Obtiene señales de un periodo de tiempo específico"""
        try:
            # Si se proporcionan start_time y end_time, usarlos
            if start_time and end_time:
                query = {
                    "timestamp": {
                        "$gte": start_time,
                        "$lte": end_time
                    }
                }
            else:
                # ✅ VALIDACIÓN MÁS ROBUSTA PARA EVITAR ERROR DE TIMEDELTA
                try:
                    # Importar datetime aquí para verificación de tipo
                    from datetime import datetime as dt
                    
                    # Validar y convertir el parámetro hours de forma segura
                    if isinstance(hours, dt):
                        log.error(f"Se recibió datetime en lugar de hours: {hours}")
                        hours = 24  # Valor por defecto
                    elif isinstance(hours, str):
                        try:
                            hours = float(hours)
                        except (ValueError, TypeError):
                            log.error(f"No se pudo convertir string a número: {hours}")
                            hours = 24
                    elif not isinstance(hours, (int, float)):
                        log.error(f"El parámetro 'hours' debe ser un número, recibido: {type(hours)} - {hours}")
                        hours = 24
                    
                    # Asegurar que sea un número válido y convertir a float explícitamente
                    hours = float(max(1, min(8760, hours)))  # Entre 1 hora y 1 año
                    
                    # Verificación final antes de usar en timedelta
                    if not isinstance(hours, (int, float)) or hours <= 0:
                        log.error(f"Valor de hours inválido después de validación: {hours}")
                        hours = 24.0
                        
                except (ValueError, TypeError, AttributeError) as e:
                    log.error(f"Error convirtiendo hours: {e}, usando valor por defecto")
                    hours = 24.0
                
                # Usar el método anterior con horas - asegurándonos de que es un número
                try:
                    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                    query = {"timestamp": {"$gte": cutoff_time}}
                except (TypeError, ValueError) as e:
                    log.error(f"Error creando timedelta con hours={hours} (tipo: {type(hours)}): {e}")
                    # Fallback seguro
                    cutoff_time = datetime.utcnow() - timedelta(hours=24.0)
                    query = {"timestamp": {"$gte": cutoff_time}}
            
            if confidence_filter and confidence_filter != 'ALL':
                query["confidence_level"] = confidence_filter
            
            cursor = self.signals_collection.find(query).sort("timestamp", DESCENDING)
            signals = await cursor.to_list(length=1000)
            
            time_desc = f"periodo {start_time} - {end_time}" if start_time and end_time else f"últimas {hours}h"
            log.debug(f"📊 Recuperadas {len(signals)} señales del {time_desc}")
            return signals
            
        except Exception as e:
            log.error(f"Error obteniendo señales en get_signals_by_timeframe: {e}")
            log.error(f"Parámetros recibidos - start_time: {start_time}, end_time: {end_time}, hours: {hours} (tipo: {type(hours)})")
            return []
    
    async def get_top_signals(self, limit: int = 50, min_score: int = 50) -> List[Dict]:
        """Obtiene las mejores señales recientes"""
        try:
            query = {
                "total_score": {"$gte": min_score},
                "timestamp": {"$gte": datetime.utcnow() - timedelta(hours=24)}
            }
            
            cursor = self.signals_collection.find(query).sort("total_score", DESCENDING).limit(limit)
            signals = await cursor.to_list(length=limit)
            
            return signals
            
        except Exception as e:
            log.error(f"Error obteniendo top señales: {e}")
            return []
    
    async def get_signals_by_symbol(self, symbol: str, hours: int = 168) -> List[Dict]:
        """Obtiene historial de señales para un símbolo específico"""
        try:
            # Validar tipo de hours
            if not isinstance(hours, (int, float)):
                log.error(f"El parámetro 'hours' debe ser un número, recibido: {type(hours)} - {hours}")
                hours = 168  # Valor por defecto
                
            cutoff_time = datetime.utcnow() - timedelta(hours=int(hours))
            
            query = {
                "symbol": symbol,
                "timestamp": {"$gte": cutoff_time}
            }
            
            cursor = self.signals_collection.find(query).sort("timestamp", DESCENDING)
            signals = await cursor.to_list(length=100)
            
            return signals
            
        except Exception as e:
            log.error(f"Error obteniendo señales para {symbol}: {e}")
            return []
    
    async def get_confidence_distribution(self, hours: int = 24) -> Dict[str, int]:
        """Obtiene distribución de niveles de confianza"""
        try:
            # Validar tipo de hours
            if not isinstance(hours, (int, float)):
                log.error(f"El parámetro 'hours' debe ser un número, recibido: {type(hours)} - {hours}")
                hours = 24  # Valor por defecto
                
            cutoff_time = datetime.utcnow() - timedelta(hours=int(hours))
            
            pipeline = [
                {"$match": {"timestamp": {"$gte": cutoff_time}}},
                {"$group": {
                    "_id": "$confidence_level",
                    "count": {"$sum": 1}
                }}
            ]
            
            result = await self.signals_collection.aggregate(pipeline).to_list(length=10)
            
            distribution = {item["_id"]: item["count"] for item in result}
            return distribution
            
        except Exception as e:
            log.error(f"Error obteniendo distribución de confianza: {e}")
            return {}
    
    async def get_hourly_signal_counts(self, hours: int = 24) -> List[Dict]:
        """Obtiene conteo de señales por hora"""
        try:
            # Validar tipo de hours
            if not isinstance(hours, (int, float)):
                log.error(f"El parámetro 'hours' debe ser un número, recibido: {type(hours)} - {hours}")
                hours = 24  # Valor por defecto
                
            cutoff_time = datetime.utcnow() - timedelta(hours=int(hours))
            
            pipeline = [
                {"$match": {"timestamp": {"$gte": cutoff_time}}},
                {"$group": {
                    "_id": {
                        "year": {"$year": "$timestamp"},
                        "month": {"$month": "$timestamp"},
                        "day": {"$dayOfMonth": "$timestamp"},
                        "hour": {"$hour": "$timestamp"}
                    },
                    "total_signals": {"$sum": 1},
                    "strong_signals": {
                        "$sum": {"$cond": [{"$eq": ["$confidence_level", "FUERTE"]}, 1, 0]}
                    }
                }},
                {"$sort": {"_id": 1}}
            ]
            
            result = await self.signals_collection.aggregate(pipeline).to_list(length=24)
            return result
            
        except Exception as e:
            log.error(f"Error obteniendo conteos por hora: {e}")
            return []
    
    async def save_performance_metrics(self, metrics: Dict) -> bool:
        """Guarda métricas de rendimiento del bot"""
        try:
            metrics['timestamp'] = datetime.utcnow()
            await self.performance_metrics_collection.insert_one(metrics)
            return True
            
        except Exception as e:
            log.error(f"Error guardando métricas de rendimiento: {e}")
            return False
    
    async def get_database_stats(self) -> Dict:
        """Obtiene estadísticas de la base de datos"""
        try:
            stats = {
                'total_signals': await self.signals_collection.count_documents({}),
                'signals_today': await self.signals_collection.count_documents({
                    'timestamp': {'$gte': datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
                }),
                'market_data_points': await self.market_data_collection.count_documents({}),
                'analysis_cycles': await self.analysis_history_collection.count_documents({})
            }
            
            return stats
            
        except Exception as e:
            log.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Limpia datos antiguos para mantener la BD optimizada"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Limpiar datos de mercado antiguos (mantener solo últimos 7 días)
            market_cutoff = datetime.utcnow() - timedelta(days=7)
            result1 = await self.market_data_collection.delete_many({
                'timestamp': {'$lt': market_cutoff}
            })
            
            # Limpiar análisis antiguos (mantener según parámetro)
            result2 = await self.analysis_history_collection.delete_many({
                'timestamp': {'$lt': cutoff_time}
            })
            
            # Las señales las mantenemos más tiempo (según parámetro)
            result3 = await self.signals_collection.delete_many({
                'timestamp': {'$lt': cutoff_time}
            })
            
            log.info(f"🧹 Limpieza completada: "
                    f"Market data: {result1.deleted_count}, "
                    f"Analysis: {result2.deleted_count}, "
                    f"Signals: {result3.deleted_count}")
            
        except Exception as e:
            log.error(f"Error en limpieza de datos: {e}")


# Instancia global del manager
mongodb_manager = MongoDBManager()
