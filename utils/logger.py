"""
Sistema de logging configurado para el bot de trading.
"""

import sys
from pathlib import Path
from loguru import logger

def setup_logging():
    """Configura el sistema de logging"""
    
    # Remover el logger por defecto
    logger.remove()
    
    # Logger para consola con colores
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # Logger para archivo general
    logger.add(
        "logs/crypto_bot.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    # Logger específico para trades
    logger.add(
        "logs/trades.log",
        filter=lambda record: "TRADE" in record["extra"],
        rotation="1 week",
        retention="52 weeks",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {message}"
    )
    
    # Logger para errores críticos
    logger.add(
        "logs/errors.log",
        level="ERROR",
        rotation="1 week", 
        retention="52 weeks",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    # Crear directorio de logs si no existe
    Path("logs").mkdir(exist_ok=True)
    
    return logger

# Instancia global del logger
log = setup_logging()
