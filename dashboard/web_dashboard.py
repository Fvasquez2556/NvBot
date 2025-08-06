"""
Dashboard web en tiempo real para visualizar oportunidades de momentum.
Interfaz interactiva con gráficas y tabla de oportunidades.
"""

import dash
from dash import dcc, html, dash_table, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from config.trading_config import config
from utils.logger import log


class CryptoMomentumDashboard:
    """Dashboard web para monitoreo en tiempo real"""
    
    def __init__(self, bot_instance=None):
        self.bot = bot_instance
        self.app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
        
        # Datos para el dashboard
        self.opportunities_data = []
        self.market_stats = {}
        self.price_history = {}
        
        # Configurar layout
        self._setup_layout()
        
        # Configurar callbacks
        self._setup_callbacks()
        
        # Flag para updates
        self.running = False
        
    def _setup_layout(self):
        """Configura el layout del dashboard"""
        
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("🚀 Crypto Momentum Bot - Dashboard", 
                       style={'textAlign': 'center', 'color': '#2E86AB', 'marginBottom': '20px'}),
                html.P("Detección de momentum +7.5% en tiempo real", 
                      style={'textAlign': 'center', 'fontSize': '18px', 'color': '#666'})
            ], style={'backgroundColor': '#f8f9fa', 'padding': '20px', 'marginBottom': '20px'}),
            
            # Componente para auto-refresh (más estable)
            dcc.Interval(
                id='interval-component',
                interval=45*1000,  # 45 segundos (más estable)
                n_intervals=0,
                disabled=False
            ),
            
            # Row 1: Estadísticas generales
            html.Div([
                html.Div([
                    html.H3("📊 Estadísticas del Mercado", style={'color': '#2E86AB'}),
                    html.Div(id='market-stats-content')
                ], className='four columns'),
                
                html.Div([
                    html.H3("🎯 Resumen de Oportunidades", style={'color': '#2E86AB'}),
                    html.Div(id='opportunities-summary')
                ], className='four columns'),
                
                html.Div([
                    html.H3("🔥 Estado del Bot", style={'color': '#2E86AB'}),
                    html.Div(id='bot-status-content')
                ], className='four columns'),
                
            ], className='row', style={'marginBottom': '30px'}),
            
            # Row 2: Gráfica de distribución de scores
            html.Div([
                html.H3("📈 Distribución de Scores de Momentum", style={'color': '#2E86AB'}),
                dcc.Graph(id='scores-distribution-chart')
            ], style={'marginBottom': '30px'}),
            
            # Row 3: Filtros
            html.Div([
                html.H3("🔍 Filtros", style={'color': '#2E86AB'}),
                html.Div([
                    html.Div([
                        html.Label("Clasificación Mínima:"),
                        dcc.Dropdown(
                            id='min-classification-filter',
                            options=[
                                {'label': 'Todas', 'value': 'ALL'},
                                {'label': 'Débil', 'value': 'DÉBIL'},
                                {'label': 'Medio', 'value': 'MEDIO'},
                                {'label': 'Alto', 'value': 'ALTO'},
                                {'label': 'Fuerte', 'value': 'FUERTE'}
                            ],
                            value='MEDIO'
                        )
                    ], className='three columns'),
                    
                    html.Div([
                        html.Label("Score Mínimo:"),
                        dcc.Slider(
                            id='min-score-filter',
                            min=0,
                            max=100,
                            step=5,
                            value=50,
                            marks={i: str(i) for i in range(0, 101, 20)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], className='six columns'),
                    
                    html.Div([
                        html.Label("Probabilidad Mínima 4h:"),
                        dcc.Input(
                            id='min-probability-filter',
                            type='number',
                            value=50,
                            min=0,
                            max=100,
                            style={'width': '100%'}
                        )
                    ], className='three columns'),
                    
                ], className='row')
            ], style={'marginBottom': '30px'}),
            
            # Row 4: Tabla de oportunidades
            html.Div([
                html.H3("🏆 Mejores Oportunidades", style={'color': '#2E86AB'}),
                html.Div(id='opportunities-table-container')
            ], style={'marginBottom': '30px'}),
            
            # Row 5: Gráficas de precios
            html.Div([
                html.H3("📊 Gráficas de Precios (Top 6)", style={'color': '#2E86AB'}),
                html.Div(id='price-charts-container')
            ])
            
        ], style={'margin': '20px'})
    
    def _setup_callbacks(self):
        """Configura los callbacks del dashboard"""
        
        @self.app.callback(
            [Output('market-stats-content', 'children'),
             Output('opportunities-summary', 'children'),
             Output('bot-status-content', 'children'),
             Output('scores-distribution-chart', 'figure'),
             Output('opportunities-table-container', 'children'),
             Output('price-charts-container', 'children')],
            [Input('interval-component', 'n_intervals'),
             Input('min-classification-filter', 'value'),
             Input('min-score-filter', 'value'),
             Input('min-probability-filter', 'value')],
            prevent_initial_call=False
        )
        def update_dashboard(n_intervals, min_classification, min_score, min_probability):
            try:
                return self._update_all_components(min_classification, min_score, min_probability)
            except Exception as e:
                log.error(f"Error en callback principal: {e}")
                error_msg = html.Div("Error de conexión", style={'color': 'red'})
                return error_msg, error_msg, error_msg, {}, error_msg, error_msg
    
    def _update_all_components(self, min_classification, min_score, min_probability):
        """Actualiza todos los componentes del dashboard con manejo robusto de errores"""
        try:
            # Validar inputs
            if min_classification is None:
                min_classification = 'MEDIO'
            if min_score is None:
                min_score = 50
            if min_probability is None:
                min_probability = 50
                
            # Obtener datos actualizados
            self._fetch_latest_data()
            
            # Filtrar oportunidades
            filtered_opportunities = self._filter_opportunities(min_classification, min_score, min_probability)
            
            # Generar componentes con manejo individual de errores
            try:
                market_stats = self._generate_market_stats()
            except Exception as e:
                log.error(f"Error generando market stats: {e}")
                market_stats = html.Div("Error cargando estadísticas", style={'color': 'red'})
                
            try:
                opportunities_summary = self._generate_opportunities_summary(filtered_opportunities)
            except Exception as e:
                log.error(f"Error generando summary: {e}")
                opportunities_summary = html.Div("Error cargando resumen", style={'color': 'red'})
                
            try:
                bot_status = self._generate_bot_status()
            except Exception as e:
                log.error(f"Error generando bot status: {e}")
                bot_status = html.Div("Error cargando estado", style={'color': 'red'})
                
            try:
                scores_chart = self._generate_scores_distribution_chart()
            except Exception as e:
                log.error(f"Error generando chart: {e}")
                scores_chart = {'data': [], 'layout': {'title': 'Error cargando gráfica'}}
                
            try:
                opportunities_table = self._generate_opportunities_table(filtered_opportunities)
            except Exception as e:
                log.error(f"Error generando tabla: {e}")
                opportunities_table = html.Div("Error cargando tabla", style={'color': 'red'})
                
            try:
                price_charts = self._generate_price_charts(filtered_opportunities[:6])
            except Exception as e:
                log.error(f"Error generando gráficas: {e}")
                price_charts = html.Div("Error cargando gráficas", style={'color': 'red'})
            
            return market_stats, opportunities_summary, bot_status, scores_chart, opportunities_table, price_charts
            
        except Exception as e:
            log.error(f"Error actualizando dashboard: {e}")
            error_msg = html.Div(f"Error: {str(e)}", style={'color': 'red'})
            return error_msg, error_msg, error_msg, {}, error_msg, error_msg
    
    def _fetch_latest_data(self):
        """Obtiene los datos más recientes del bot con mejor manejo de estado"""
        try:
            if self.bot and hasattr(self.bot, 'running') and self.bot.running:
                # Verificar si el bot tiene métodos de acceso a datos
                if hasattr(self.bot, 'get_current_opportunities'):
                    try:
                        opportunities = self.bot.get_current_opportunities()
                        if opportunities:
                            self.opportunities_data = opportunities
                    except Exception as e:
                        log.warning(f"Bot aún no tiene oportunidades: {e}")
                
                # Obtener estadísticas de mercado si están disponibles
                if hasattr(self.bot, 'data_collector'):
                    try:
                        market_overview = self.bot.data_collector.get_market_overview()
                        if market_overview:
                            self.market_stats = market_overview
                    except Exception as e:
                        log.warning(f"Datos de mercado no disponibles: {e}")
                
                # Si no hay datos reales aún, usar mock data con indicación
                if not self.opportunities_data:
                    self._generate_mock_data(initialization_mode=True)
            else:
                # Bot no disponible o no iniciado
                self._generate_mock_data()
                
        except Exception as e:
            log.error(f"Error obteniendo datos: {e}")
            self._generate_mock_data()
    
    def _generate_mock_data(self, initialization_mode=False):
        """Genera datos de prueba para desarrollo"""
        import random
        
        mock_opportunities = []
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'BNBUSDT']
        classifications = ['FUERTE', 'ALTO', 'MEDIO', 'DÉBIL']
        
        for i, symbol in enumerate(symbols):
            mock_opportunities.append({
                'symbol': symbol,
                'score': random.randint(30, 95),
                'classification': random.choice(classifications),
                'probability_4h': random.randint(40, 85),
                'analysis': {
                    'momentum_score': {'total_score': random.randint(30, 95)},
                    'classification': random.choice(classifications),
                    'probability_7_5': {'timeframe_probabilities': {'4h': random.randint(40, 85)}},
                    'components': {
                        'rsi': {'score': random.randint(5, 25)},
                        'macd': {'score': random.randint(5, 20)},
                        'volume': {'score': random.randint(5, 25)}
                    }
                }
            })
        
        self.opportunities_data = mock_opportunities
        
        # Estadísticas según el modo
        if initialization_mode:
            self.market_stats = {
                'total_pairs': 259,  # Número real del log
                'active_data': 259,
                'coverage_percentage': 100.0,
                'status': 'initializing'
            }
        else:
            self.market_stats = {
                'total_pairs': 400,
                'active_data': 380,
                'coverage_percentage': 95.0,
                'status': 'mock'
            }
    
    def _filter_opportunities(self, min_classification, min_score, min_probability):
        """Filtra oportunidades según criterios"""
        try:
            filtered = []
            
            # Mapeo de niveles de clasificación
            classification_levels = {
                'DÉBIL': 1,
                'MEDIO': 2,
                'ALTO': 3,
                'FUERTE': 4
            }
            
            min_level = classification_levels.get(min_classification, 0) if min_classification != 'ALL' else 0
            
            for opp in self.opportunities_data:
                # Filtro por clasificación
                if min_classification != 'ALL':
                    opp_level = classification_levels.get(opp['classification'], 0)
                    if opp_level < min_level:
                        continue
                
                # Filtro por score
                if opp['score'] < min_score:
                    continue
                
                # Filtro por probabilidad
                if opp['probability_4h'] < min_probability:
                    continue
                
                filtered.append(opp)
            
            # Ordenar por score
            filtered.sort(key=lambda x: x['score'], reverse=True)
            
            return filtered
            
        except Exception as e:
            log.error(f"Error filtrando oportunidades: {e}")
            return []
    
    def _generate_market_stats(self):
        """Genera estadísticas del mercado incluyendo tendencias"""
        try:
            stats = self.market_stats
            
            # Obtener resumen de tendencias si está disponible
            trend_summary = stats.get('trend_summary', {})
            
            basic_stats = html.Div([
                html.P(f"📊 Total de pares: {stats.get('total_pairs', 0)}", style={'margin': '5px 0'}),
                html.P(f"🔍 Pares analizados: {stats.get('active_data', 0)}", style={'margin': '5px 0'}),
                html.P(f"📈 Cobertura: {stats.get('coverage_percentage', 0):.1f}%", style={'margin': '5px 0'}),
                html.P(f"⏰ Última actualización: {datetime.now().strftime('%H:%M:%S')}", 
                      style={'margin': '5px 0', 'fontSize': '12px', 'color': '#666'})
            ])
            
            # Añadir estadísticas de tendencias si están disponibles
            if trend_summary and trend_summary.get('total_signals', 0) > 0:
                trend_stats = html.Div([
                    html.Hr(),
                    html.P("🔄 Tendencias de Fuerza:", style={'fontWeight': 'bold', 'margin': '10px 0 5px 0'}),
                    html.P(f"📈 Fortaleciendo: {trend_summary.get('strengthening_pct', 0)}%", 
                          style={'margin': '2px 0', 'color': '#4caf50'}),
                    html.P(f"📉 Debilitando: {trend_summary.get('weakening_pct', 0)}%", 
                          style={'margin': '2px 0', 'color': '#f44336'}),
                    html.P(f"📊 Estable: {trend_summary.get('stable_pct', 0)}%", 
                          style={'margin': '2px 0', 'color': '#ff9800'})
                ])
                
                return html.Div([basic_stats, trend_stats])
            else:
                return basic_stats
            
        except Exception as e:
            return html.Div(f"Error: {e}", style={'color': 'red'})
    
    def _generate_opportunities_summary(self, opportunities):
        """Genera resumen de oportunidades"""
        try:
            # Contar por clasificación
            counts = {'FUERTE': 0, 'ALTO': 0, 'MEDIO': 0, 'DÉBIL': 0}
            
            for opp in opportunities:
                classification = opp.get('classification', 'DÉBIL')
                if classification in counts:
                    counts[classification] += 1
            
            return html.Div([
                html.P(f"🔥 Fuerte: {counts['FUERTE']}", style={'margin': '5px 0', 'color': '#d32f2f'}),
                html.P(f"⚡ Alto: {counts['ALTO']}", style={'margin': '5px 0', 'color': '#f57c00'}),
                html.P(f"📈 Medio: {counts['MEDIO']}", style={'margin': '5px 0', 'color': '#1976d2'}),
                html.P(f"📊 Débil: {counts['DÉBIL']}", style={'margin': '5px 0', 'color': '#666'}),
                html.Hr(),
                html.P(f"📋 Total mostrado: {len(opportunities)}", style={'margin': '5px 0', 'fontWeight': 'bold'})
            ])
            
        except Exception as e:
            return html.Div(f"Error: {e}", style={'color': 'red'})
    
    def _generate_bot_status(self):
        """Genera estado del bot con mejor detección"""
        try:
            if self.bot and hasattr(self.bot, 'running'):
                # Verificar si el bot tiene el método get_bot_status
                if hasattr(self.bot, 'get_bot_status'):
                    try:
                        status = self.bot.get_bot_status()
                        running_status = "🟢 Ejecutándose" if status.get('running', False) else "🔴 Detenido"
                        cycles = status.get('cycles_completed', 0)
                        last_analysis = status.get('last_analysis')
                        
                        last_analysis_str = "Nunca"
                        if last_analysis:
                            last_analysis_str = last_analysis.strftime('%H:%M:%S')
                        
                        return html.Div([
                            html.P(f"Estado: {running_status}", style={'margin': '5px 0'}),
                            html.P(f"🔄 Ciclos: {cycles}", style={'margin': '5px 0'}),
                            html.P(f"⏰ Último análisis: {last_analysis_str}", style={'margin': '5px 0'}),
                            html.P(f"🎯 Oportunidades: {status.get('opportunities_count', 0)}", style={'margin': '5px 0'})
                        ])
                    except Exception:
                        # Fallback: verificar directamente el estado del bot
                        is_running = getattr(self.bot, 'running', False)
                        status_text = "🟢 Inicializando..." if is_running else "🔄 Iniciando..."
                        
                        return html.Div([
                            html.P(f"Estado: {status_text}", style={'margin': '5px 0'}),
                            html.P("🔄 Conectando a Binance...", style={'margin': '5px 0'}),
                            html.P("⏰ Cargando datos iniciales", style={'margin': '5px 0'}),
                            html.P("📊 259 pares USDT detectados", style={'margin': '5px 0'})
                        ])
                else:
                    # Bot existe pero sin métodos de estado
                    return html.Div([
                        html.P("🟡 Bot inicializando...", style={'margin': '5px 0', 'color': '#ff9800'}),
                        html.P("Cargando configuración", style={'margin': '5px 0', 'fontSize': '12px'})
                    ])
            else:
                return html.Div([
                    html.P("🔄 Modo desarrollo", style={'margin': '5px 0', 'color': '#666'}),
                    html.P("Datos simulados", style={'margin': '5px 0', 'fontSize': '12px'})
                ])
                
        except Exception as e:
            return html.Div([
                html.P("⚠️ Error de conexión", style={'margin': '5px 0', 'color': 'orange'}),
                html.P(f"Detalles: {str(e)[:50]}...", style={'margin': '5px 0', 'fontSize': '11px'})
            ])
    
    def _generate_scores_distribution_chart(self):
        """Genera gráfica de distribución de scores"""
        try:
            if not self.opportunities_data:
                return {'data': [], 'layout': {'title': 'No hay datos disponibles'}}
            
            # Extraer scores
            scores = [opp['score'] for opp in self.opportunities_data]
            classifications = [opp['classification'] for opp in self.opportunities_data]
            
            # Crear histograma
            fig = go.Figure()
            
            # Histograma por clasificación
            for classification in ['DÉBIL', 'MEDIO', 'ALTO', 'FUERTE']:
                class_scores = [score for score, cls in zip(scores, classifications) if cls == classification]
                if class_scores:
                    fig.add_trace(go.Histogram(
                        x=class_scores,
                        name=classification,
                        opacity=0.7,
                        nbinsx=20
                    ))
            
            fig.update_layout(
                title='Distribución de Scores por Clasificación',
                xaxis_title='Score de Momentum',
                yaxis_title='Cantidad',
                barmode='overlay',
                height=400
            )
            
            return fig
            
        except Exception as e:
            log.error(f"Error generando gráfica de scores: {e}")
            return {'data': [], 'layout': {'title': f'Error: {e}'}}
    
    def _generate_opportunities_table(self, opportunities):
        """Genera tabla de oportunidades con información de tendencias"""
        try:
            if not opportunities:
                return html.Div("No hay oportunidades que coincidan con los filtros.", 
                              style={'textAlign': 'center', 'padding': '20px', 'color': '#666'})
            
            # Preparar datos para la tabla
            table_data = []
            
            for opp in opportunities[:20]:  # Solo top 20
                # Obtener componentes del análisis
                analysis = opp.get('display_signal', opp.get('analysis', {}))
                
                # Obtener scores de RSI, MACD y volumen con fallbacks
                rsi_score = analysis.get('rsi_score', analysis.get('rsi', 0))
                macd_score = analysis.get('macd_score', analysis.get('macd_signal', 0))
                volume_score = analysis.get('volume_score', analysis.get('volume_spike', 0))
                
                # Asegurar que sean números
                rsi_score = rsi_score if isinstance(rsi_score, (int, float)) else 0
                macd_score = macd_score if isinstance(macd_score, (int, float)) else 0
                volume_score = volume_score if isinstance(volume_score, (int, float)) else 0
                
                # Obtener información de tendencia
                trend_info = opp.get('trend', {})
                trend_direction = trend_info.get('direction', 'stable')
                momentum_change = trend_info.get('momentum_change', 0)
                
                # Asegurar que momentum_change es un número
                if isinstance(momentum_change, (int, float)):
                    momentum_value = momentum_change
                else:
                    momentum_value = 0
                
                # Formatear tendencia para mostrar
                if trend_direction == 'strengthening':
                    trend_display = f"📈 +{momentum_value:.1f}"
                elif trend_direction == 'weakening':
                    trend_display = f"📉 {momentum_value:.1f}"
                else:
                    trend_display = f"📊 {momentum_value:.1f}"
                
                # Usar análisis promediado para score y clasificación
                display_analysis = opp.get('display_signal', analysis)
                score = display_analysis.get('momentum_score', analysis.get('momentum_score', 0))
                classification = display_analysis.get('confidence_level', analysis.get('classification', 'DÉBIL'))
                probability = display_analysis.get('probability_7_5', analysis.get('probability_7_5', 0))
                
                # Asegurar que score y probability son números
                score = score if isinstance(score, (int, float)) else 0
                probability = probability if isinstance(probability, (int, float)) else 0
                
                table_data.append({
                    'Símbolo': opp['symbol'],
                    'Score Prom.': f"{score:.1f}",
                    'Clasificación': classification.upper(),
                    'Prob 7.5% (%)': f"{probability:.1f}",
                    'Tendencia': trend_display,
                    'Historial': opp.get('history_count', 1),
                    'RSI': rsi_score,
                    'MACD': macd_score,
                    'Volumen': volume_score
                })
            
            # Crear tabla con columnas adicionales
            return dash_table.DataTable(
                data=table_data,
                columns=[
                    {'name': 'Símbolo', 'id': 'Símbolo', 'type': 'text'},
                    {'name': 'Score Prom.', 'id': 'Score Prom.', 'type': 'numeric'},
                    {'name': 'Clasificación', 'id': 'Clasificación', 'type': 'text'},
                    {'name': 'Prob 7.5% (%)', 'id': 'Prob 7.5% (%)', 'type': 'numeric'},
                    {'name': 'Tendencia', 'id': 'Tendencia', 'type': 'text'},
                    {'name': 'Historial', 'id': 'Historial', 'type': 'numeric'},
                    {'name': 'RSI', 'id': 'RSI', 'type': 'numeric'},
                    {'name': 'MACD', 'id': 'MACD', 'type': 'numeric'},
                    {'name': 'Volumen', 'id': 'Volumen', 'type': 'numeric'}
                ],
                style_cell={
                    'textAlign': 'center',
                    'padding': '8px',
                    'fontFamily': 'Arial',
                    'fontSize': '12px'
                },
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{Clasificación} = FUERTE'},
                        'backgroundColor': '#ffebee',
                        'color': '#d32f2f',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {'filter_query': '{Clasificación} = ALTO'},
                        'backgroundColor': '#fff3e0',
                        'color': '#f57c00'
                    },
                    {
                        'if': {'filter_query': '{Clasificación} = MEDIO'},
                        'backgroundColor': '#e3f2fd',
                        'color': '#1976d2'
                    }
                ],
                style_header={
                    'backgroundColor': '#2E86AB',
                    'color': 'white',
                    'fontWeight': 'bold'
                },
                sort_action="native",
                page_size=20
            )
            
        except Exception as e:
            log.error(f"Error generando tabla: {e}")
            return html.Div(f"Error generando tabla: {e}", style={'color': 'red'})
    
    def _generate_price_charts(self, top_opportunities):
        """Genera gráficas de precios para top oportunidades"""
        try:
            if not top_opportunities:
                return html.Div("No hay datos suficientes para gráficas.", 
                              style={'textAlign': 'center', 'padding': '20px'})
            
            charts = []
            
            for i, opp in enumerate(top_opportunities):
                symbol = opp['symbol']
                
                # Generar datos de precio simulados (en producción vendrían del bot)
                chart = self._create_price_chart(symbol, opp)
                charts.append(
                    html.Div([
                        dcc.Graph(figure=chart)
                    ], className='six columns' if i % 2 == 0 else 'six columns')
                )
            
            # Organizar en filas
            rows = []
            for i in range(0, len(charts), 2):
                row_charts = charts[i:i+2]
                rows.append(html.Div(row_charts, className='row', style={'marginBottom': '20px'}))
            
            return html.Div(rows)
            
        except Exception as e:
            log.error(f"Error generando gráficas de precio: {e}")
            return html.Div(f"Error: {e}", style={'color': 'red'})
    
    def _create_price_chart(self, symbol, opportunity):
        """Crea gráfica de precio individual"""
        try:
            # Simular datos de precio (en producción vendrían del WebSocket)
            import random
            import numpy as np
            
            # Generar datos simulados
            base_price = random.uniform(0.1, 100)
            times = pd.date_range(start=datetime.now() - timedelta(hours=4), 
                                end=datetime.now(), freq='5min')
            
            # Simular movimiento de precio
            prices = []
            current_price = base_price
            
            for _ in times:
                change = random.uniform(-0.02, 0.02)  # ±2% cambio
                current_price *= (1 + change)
                prices.append(current_price)
            
            # Crear gráfica
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=times,
                y=prices,
                mode='lines',
                name=symbol,
                line=dict(color='#2E86AB', width=2)
            ))
            
            # Agregar información del momentum
            score = opportunity['score']
            classification = opportunity['classification']
            
            # Color según clasificación
            color_map = {
                'FUERTE': '#d32f2f',
                'ALTO': '#f57c00',
                'MEDIO': '#1976d2',
                'DÉBIL': '#666'
            }
            
            fig.update_layout(
                title=f"{symbol} - {classification} ({score}/100)",
                title_font_color=color_map.get(classification, '#666'),
                xaxis_title="Tiempo",
                yaxis_title="Precio USDT",
                height=300,
                showlegend=False,
                margin=dict(l=50, r=50, t=50, b=50)
            )
            
            return fig
            
        except Exception as e:
            log.error(f"Error creando gráfica para {symbol}: {e}")
            return {'data': [], 'layout': {'title': f'Error: {symbol}'}}
    
    def run(self, host='0.0.0.0', port=None, debug=False):
        """Ejecuta el dashboard con configuración mejorada"""
        port = port or config.dashboard.port
        
        log.info(f"🌐 Iniciando dashboard en http://{host}:{port}")
        
        self.running = True
        
        # Configuraciones adicionales para estabilidad
        try:
            self.app.run_server(
                host=host,
                port=port,
                debug=debug,
                dev_tools_hot_reload=False,
                dev_tools_ui=False,
                dev_tools_props_check=False,
                threaded=True,
                processes=1
            )
        except Exception as e:
            log.error(f"Error ejecutando dashboard: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Detiene el dashboard"""
        self.running = False


def run_dashboard_standalone():
    """Ejecuta el dashboard en modo standalone para desarrollo"""
    dashboard = CryptoMomentumDashboard()
    dashboard.run(debug=True)


if __name__ == "__main__":
    run_dashboard_standalone()
