"""
Sistema de promedios históricos para señales de momentum.
Mantiene un historial de análisis y calcula promedios móviles.
"""

from typing import Dict, List, Optional, Deque
from collections import deque
from datetime import datetime, timedelta
import json
import os

class SignalAveraging:
    """Maneja el promediado histórico de señales de momentum"""
    
    def __init__(self, window_size: int = 10, history_file: str = "data/signal_history.json"):
        """
        Args:
            window_size: Número de análisis para el promedio móvil
            history_file: Archivo para persistir el historial
        """
        self.window_size = window_size
        self.history_file = history_file
        
        # Historial de señales por símbolo
        # Estructura: {symbol: deque([{timestamp, analysis}, ...])}
        self.signal_history: Dict[str, Deque] = {}
        
        # Promedios actuales calculados
        self.current_averages: Dict[str, Dict] = {}
        
        # Tendencias (si está ganando o perdiendo fuerza)
        self.signal_trends: Dict[str, Dict] = {}
        
        self._load_history()
    
    def add_signal(self, symbol: str, analysis: Dict) -> Dict:
        """
        Añade una nueva señal y calcula el promedio actualizado
        
        Args:
            symbol: Símbolo de la criptomoneda
            analysis: Análisis actual del símbolo
            
        Returns:
            Dict con el análisis promediado y tendencia
        """
        # Inicializar historial si no existe
        if symbol not in self.signal_history:
            self.signal_history[symbol] = deque(maxlen=self.window_size)
        
        # Añadir timestamp al análisis
        timestamped_analysis = {
            'timestamp': datetime.now().isoformat(),
            'analysis': analysis.copy()
        }
        
        # Añadir al historial
        self.signal_history[symbol].append(timestamped_analysis)
        
        # Calcular nuevo promedio
        averaged_analysis = self._calculate_average(symbol)
        
        # Calcular tendencia
        trend = self._calculate_trend(symbol)
        
        # Construir resultado final
        result = {
            'symbol': symbol,
            'current_signal': analysis,  # Señal actual
            'averaged_signal': averaged_analysis,  # Señal promediada
            'trend': trend,  # Tendencia de fuerza
            'history_count': len(self.signal_history[symbol]),
            'last_updated': datetime.now().isoformat()
        }
        
        # Guardar en cache
        self.current_averages[symbol] = result
        
        # Persistir historial cada cierto tiempo
        self._save_history()
        
        return result
    
    def _calculate_average(self, symbol: str) -> Dict:
        """Calcula el promedio móvil de las señales"""
        if symbol not in self.signal_history or not self.signal_history[symbol]:
            return {}
        
        history = list(self.signal_history[symbol])
        
        # Campos numéricos para promediar
        numeric_fields = [
            'momentum_score', 'probability_7_5', 'rsi_score', 'macd_score',
            'volume_score', 'velocity_score', 'breakout_score', 'total_score'
        ]
        
        averaged = {}
        
        # Calcular promedios para campos numéricos
        for field in numeric_fields:
            values = []
            for entry in history:
                if field in entry['analysis'] and entry['analysis'][field] is not None:
                    values.append(float(entry['analysis'][field]))
            
            if values:
                averaged[field] = round(sum(values) / len(values), 2)
            else:
                averaged[field] = 0
        
        # Campos categóricos - usar el más frecuente
        categorical_fields = ['confidence_level', 'macd_signal']
        
        for field in categorical_fields:
            values = []
            for entry in history:
                if field in entry['analysis'] and entry['analysis'][field]:
                    values.append(entry['analysis'][field])
            
            if values:
                # Encontrar el valor más frecuente
                from collections import Counter
                most_common = Counter(values).most_common(1)
                averaged[field] = most_common[0][0] if most_common else None
            else:
                averaged[field] = None
        
        # Recalcular nivel de confianza basado en score promedio
        avg_score = averaged.get('momentum_score', 0)
        if avg_score >= 80:
            averaged['confidence_level'] = 'Fuerte'
        elif avg_score >= 65:
            averaged['confidence_level'] = 'Alto'
        elif avg_score >= 50:
            averaged['confidence_level'] = 'Medio'
        else:
            averaged['confidence_level'] = 'Débil'
        
        # Campos que se mantienen del análisis actual
        if history:
            current = history[-1]['analysis']
            for field in ['symbol', 'price', 'change_24h', 'volume_24h']:
                if field in current:
                    averaged[field] = current[field]
        
        return averaged
    
    def _calculate_trend(self, symbol: str) -> Dict:
        """Calcula la tendencia de la señal (ganando/perdiendo fuerza)"""
        if symbol not in self.signal_history or len(self.signal_history[symbol]) < 2:
            return {
                'direction': 'neutral',
                'strength': 'unknown',
                'momentum_change': 0,
                'probability_change': 0
            }
        
        history = list(self.signal_history[symbol])
        
        # Comparar últimos vs primeros análisis
        recent_half = history[len(history)//2:]
        older_half = history[:len(history)//2]
        
        # Calcular promedios de cada mitad
        def avg_field(data, field):
            values = [entry['analysis'].get(field, 0) for entry in data 
                     if entry['analysis'].get(field) is not None]
            return sum(values) / len(values) if values else 0
        
        recent_momentum = avg_field(recent_half, 'momentum_score')
        older_momentum = avg_field(older_half, 'momentum_score')
        
        recent_probability = avg_field(recent_half, 'probability_7_5')
        older_probability = avg_field(older_half, 'probability_7_5')
        
        # Calcular cambios
        momentum_change = recent_momentum - older_momentum
        probability_change = recent_probability - older_probability
        
        # Determinar dirección
        if momentum_change > 5:
            direction = 'strengthening'
            strength = 'strong' if momentum_change > 15 else 'moderate'
        elif momentum_change < -5:
            direction = 'weakening'
            strength = 'strong' if momentum_change < -15 else 'moderate'
        else:
            direction = 'stable'
            strength = 'minimal'
        
        return {
            'direction': direction,
            'strength': strength,
            'momentum_change': round(momentum_change, 2),
            'probability_change': round(probability_change, 2),
            'trend_score': round((momentum_change + probability_change) / 2, 2)
        }
    
    def get_signal_with_average(self, symbol: str) -> Optional[Dict]:
        """Obtiene la señal promediada para un símbolo"""
        return self.current_averages.get(symbol)
    
    def get_all_averaged_signals(self) -> Dict[str, Dict]:
        """Obtiene todas las señales promediadas"""
        return self.current_averages.copy()
    
    def cleanup_old_signals(self, max_age_hours: int = 24):
        """Limpia señales antiguas del historial"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for symbol in list(self.signal_history.keys()):
            # Filtrar entradas antiguas
            filtered_history = deque()
            for entry in self.signal_history[symbol]:
                entry_time = datetime.fromisoformat(entry['timestamp'])
                if entry_time > cutoff_time:
                    filtered_history.append(entry)
            
            if filtered_history:
                self.signal_history[symbol] = filtered_history
            else:
                # Eliminar símbolo si no tiene datos recientes
                del self.signal_history[symbol]
                if symbol in self.current_averages:
                    del self.current_averages[symbol]
    
    def _save_history(self):
        """Guarda el historial en archivo JSON"""
        try:
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            
            # Convertir deques a listas para JSON
            serializable_history = {}
            for symbol, history in self.signal_history.items():
                serializable_history[symbol] = list(history)
            
            with open(self.history_file, 'w') as f:
                json.dump(serializable_history, f, indent=2)
                
        except Exception as e:
            print(f"Error guardando historial: {e}")
    
    def _load_history(self):
        """Carga el historial desde archivo JSON"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                
                # Convertir listas a deques
                for symbol, history in data.items():
                    self.signal_history[symbol] = deque(history, maxlen=self.window_size)
                    
        except Exception as e:
            print(f"Error cargando historial: {e}")
            self.signal_history = {}
    
    def get_trend_summary(self) -> Dict:
        """Obtiene un resumen de las tendencias del mercado"""
        if not self.current_averages:
            return {}
        
        trends = {
            'strengthening': 0,
            'weakening': 0,
            'stable': 0,
            'total_signals': len(self.current_averages)
        }
        
        for signal_data in self.current_averages.values():
            direction = signal_data.get('trend', {}).get('direction', 'stable')
            trends[direction] += 1
        
        # Calcular porcentajes
        total = trends['total_signals']
        if total > 0:
            trends['strengthening_pct'] = round((trends['strengthening'] / total) * 100, 1)
            trends['weakening_pct'] = round((trends['weakening'] / total) * 100, 1)
            trends['stable_pct'] = round((trends['stable'] / total) * 100, 1)
        
        return trends
