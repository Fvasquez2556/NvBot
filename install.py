"""
Script de instalación y configuración del Crypto Momentum Bot.
Automatiza la instalación de dependencias y configuración inicial.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Ejecuta un comando y maneja errores"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False


def install_dependencies():
    """Instala las dependencias de Python"""
    print("📦 Instalando dependencias de Python...")
    
    # Verificar pip
    if not run_command("pip --version", "Verificando pip"):
        print("❌ pip no encontrado. Instala Python y pip primero.")
        return False
    
    # Instalar dependencias
    return run_command("pip install -r requirements.txt", "Instalando dependencias")


def create_directories():
    """Crea directorios necesarios"""
    print("\n📁 Creando directorios necesarios...")
    
    directories = [
        "logs",
        "data/cache",
        "config/temp"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Directorio creado: {directory}")


def setup_config():
    """Configura archivos de configuración"""
    print("\n⚙️ Configurando archivos...")
    
    # Verificar .env
    if not os.path.exists('.env'):
        print("⚠️  Archivo .env no encontrado. Usa .env.example como referencia.")
        return False
    
    print("✅ Archivo .env encontrado")
    return True


def test_installation():
    """Prueba que la instalación funcione"""
    print("\n🧪 Probando instalación...")
    
    try:
        # Probar imports principales
        import pandas
        import numpy
        import websockets
        import dash
        print("✅ Dependencias principales importadas correctamente")
        
        # Probar configuración
        from config.trading_config import config
        print("✅ Configuración cargada correctamente")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error importando dependencias: {e}")
        return False
    except Exception as e:
        print(f"❌ Error en configuración: {e}")
        return False


def main():
    """Función principal de instalación"""
    print("""
🚀 CRYPTO MOMENTUM BOT - INSTALADOR
═══════════════════════════════════════════

Este script instalará y configurará el bot de momentum crypto.

Requisitos:
• Python 3.8+ instalado
• Conexión a internet
• API keys de Binance (opcional para testing)

═══════════════════════════════════════════
    """)
    
    # Confirmar instalación
    response = input("¿Continuar con la instalación? (y/n): ").lower()
    if response != 'y':
        print("Instalación cancelada.")
        sys.exit(0)
    
    # Pasos de instalación
    steps = [
        ("Creando directorios", create_directories),
        ("Instalando dependencias", install_dependencies),
        ("Configurando archivos", setup_config),
        ("Probando instalación", test_installation)
    ]
    
    success = True
    for description, func in steps:
        if not func():
            success = False
            break
    
    if success:
        print("""
✅ INSTALACIÓN COMPLETADA EXITOSAMENTE!

🔧 Próximos pasos:

1. Configurar API keys de Binance en .env:
   BINANCE_API_KEY=tu_api_key
   BINANCE_SECRET_KEY=tu_secret_key

2. Ejecutar el bot:
   python run_bot.py

3. Abrir dashboard:
   http://localhost:8050

📚 Documentación adicional en README.md

═══════════════════════════════════════════
        """)
    else:
        print("""
❌ INSTALACIÓN FALLÓ

Revisa los errores anteriores y soluciona los problemas.
Luego ejecuta este script nuevamente.

💡 Problemas comunes:
• Python no instalado o versión incorrecta
• Sin conexión a internet
• Permisos insuficientes

═══════════════════════════════════════════
        """)
        sys.exit(1)


if __name__ == "__main__":
    main()
