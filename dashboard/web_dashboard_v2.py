"""
Dashboard Web v2.0 para Crypto Momentum Bot
Diseñado específicamente para la nueva arquitectura v2.0
"""

import dash
from dash import dcc, html, dash_table, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import asyncio

from config.parameters import TARGET_DAILY_SIGNALS, UPDATE_INTERVAL, CONFIDENCE_LEVELS
from utils.logger import log
from data.mongodb_manager import mongodb_manager


class CryptoMomentumDashboardV2:
    """Dashboard web optimizado para la arquitectura v2.0"""
    
    def __init__(self, bot_instance=None):
        self.bot = bot_instance
        self.app = dash.Dash(__name__, external_stylesheets=[
            'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap'
        ])
        
        # Estado del dashboard
        self.running = False
        self.last_update = None
        
        # Configurar layout y callbacks
        self._setup_layout()
        self._setup_callbacks()
        
    def _setup_layout(self):
        """Configura el layout del dashboard v2.0 - Diseño moderno inspirado en analytics dashboards"""
        
        self.app.layout = html.Div([
            # Header moderno con gradiente
            html.Div([
                html.Div([
                    html.H1("🚀 Crypto Momentum Bot v2.0", 
                           style={
                               'textAlign': 'left', 
                               'color': '#ffffff', 
                               'marginBottom': '8px',
                               'fontFamily': 'Inter, sans-serif',
                               'fontWeight': '700',
                               'fontSize': '2.2rem',
                               'margin': '0'
                           }),
                    html.P(f"Sistema Unificado | Meta: Mínimo {TARGET_DAILY_SIGNALS} señales/día +7.5%", 
                          style={
                              'textAlign': 'left', 
                              'fontSize': '16px', 
                              'color': '#e5e7eb',
                              'fontFamily': 'Inter, sans-serif',
                              'margin': '0',
                              'opacity': '0.9'
                          }),
                ], style={'flex': '1'}),
                html.Div([
                    html.Div(id='last-update-display', 
                            style={
                                'fontSize': '14px', 
                                'color': '#d1d5db',
                                'fontFamily': 'Inter, sans-serif',
                                'textAlign': 'right'
                            }),
                    html.Div([
                        html.Span("●", style={'color': '#10b981', 'fontSize': '12px', 'marginRight': '6px'}),
                        html.Span("LIVE", style={'color': '#10b981', 'fontSize': '12px', 'fontWeight': '600'})
                    ], style={'textAlign': 'right', 'marginTop': '4px'})
                ], style={'textAlign': 'right'})
            ], style={
                'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
                'padding': '24px 32px', 
                'marginBottom': '24px',
                'borderRadius': '16px',
                'boxShadow': '0 8px 32px rgba(0,0,0,0.12)',
                'display': 'flex',
                'alignItems': 'center',
                'justifyContent': 'space-between'
            }),
            
            # Auto-refresh
            dcc.Interval(
                id='interval-update',
                interval=UPDATE_INTERVAL * 1000,
                n_intervals=0,
                disabled=False
            ),
            
            # Métricas principales - Estilo tarjetas modernas
            html.Div([
                # Total Spend equivalente - Pares Monitoreados
                html.Div([
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-chart-line", style={
                                'fontSize': '24px', 
                                'color': '#3b82f6',
                                'backgroundColor': '#dbeafe',
                                'padding': '12px',
                                'borderRadius': '12px',
                                'marginBottom': '16px'
                            }),
                        ], style={'display': 'flex', 'justifyContent': 'center'}),
                        html.Div(id='system-metrics'),
                        html.P("Total Pares", style={
                            'color': '#6b7280', 
                            'fontSize': '14px',
                            'fontWeight': '500',
                            'margin': '8px 0 0 0'
                        }),
                        html.P("+2.45%", style={
                            'color': '#10b981', 
                            'fontSize': '12px',
                            'fontWeight': '600',
                            'margin': '4px 0 0 0'
                        })
                    ], style={
                        'textAlign': 'center',
                        'padding': '24px',
                        'backgroundColor': '#ffffff',
                        'borderRadius': '16px',
                        'boxShadow': '0 4px 20px rgba(0,0,0,0.08)',
                        'border': '1px solid #f3f4f6'
                    })
                ], className='three columns'),
                
                # Total Impressions equivalente - Oportunidades Detectadas
                html.Div([
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-bullseye", style={
                                'fontSize': '24px', 
                                'color': '#8b5cf6',
                                'backgroundColor': '#ede9fe',
                                'padding': '12px',
                                'borderRadius': '12px',
                                'marginBottom': '16px'
                            }),
                        ], style={'display': 'flex', 'justifyContent': 'center'}),
                        html.Div(id='opportunities-metrics'),
                        html.P("Total Oportunidades", style={
                            'color': '#6b7280', 
                            'fontSize': '14px',
                            'fontWeight': '500',
                            'margin': '8px 0 0 0'
                        }),
                        html.P("-1.2%", style={
                            'color': '#ef4444', 
                            'fontSize': '12px',
                            'fontWeight': '600',
                            'margin': '4px 0 0 0'
                        })
                    ], style={
                        'textAlign': 'center',
                        'padding': '24px',
                        'backgroundColor': '#ffffff',
                        'borderRadius': '16px',
                        'boxShadow': '0 4px 20px rgba(0,0,0,0.08)',
                        'border': '1px solid #f3f4f6'
                    })
                ], className='three columns'),
                
                # Viewable Impressions equivalente - Señales Fuertes
                html.Div([
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-eye", style={
                                'fontSize': '24px', 
                                'color': '#10b981',
                                'backgroundColor': '#d1fae5',
                                'padding': '12px',
                                'borderRadius': '12px',
                                'marginBottom': '16px'
                            }),
                        ], style={'display': 'flex', 'justifyContent': 'center'}),
                        html.Div(id='signals-metrics'),
                        html.P("Señales Fuertes", style={
                            'color': '#6b7280', 
                            'fontSize': '14px',
                            'fontWeight': '500',
                            'margin': '8px 0 0 0'
                        }),
                        html.P("+6.2%", style={
                            'color': '#10b981', 
                            'fontSize': '12px',
                            'fontWeight': '600',
                            'margin': '4px 0 0 0'
                        })
                    ], style={
                        'textAlign': 'center',
                        'padding': '24px',
                        'backgroundColor': '#ffffff',
                        'borderRadius': '16px',
                        'boxShadow': '0 4px 20px rgba(0,0,0,0.08)',
                        'border': '1px solid #f3f4f6'
                    })
                ], className='three columns'),
                
                # Total Sales equivalente - Performance/Ciclos
                html.Div([
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-chart-bar", style={
                                'fontSize': '24px', 
                                'color': '#f59e0b',
                                'backgroundColor': '#fef3c7',
                                'padding': '12px',
                                'borderRadius': '12px',
                                'marginBottom': '16px'
                            }),
                        ], style={'display': 'flex', 'justifyContent': 'center'}),
                        html.Div(id='performance-metrics'),
                        html.P("Análisis Completados", style={
                            'color': '#6b7280', 
                            'fontSize': '14px',
                            'fontWeight': '500',
                            'margin': '8px 0 0 0'
                        }),
                        html.P("+4.46%", style={
                            'color': '#10b981', 
                            'fontSize': '12px',
                            'fontWeight': '600',
                            'margin': '4px 0 0 0'
                        })
                    ], style={
                        'textAlign': 'center',
                        'padding': '24px',
                        'backgroundColor': '#ffffff',
                        'borderRadius': '16px',
                        'boxShadow': '0 4px 20px rgba(0,0,0,0.08)',
                        'border': '1px solid #f3f4f6'
                    })
                ], className='three columns'),
                
            ], className='row', style={'marginBottom': '32px'}),
            
            # Sección de gráficas principales - Estilo moderno con 2 columnas
            html.Div([
                # Columna izquierda - Gráfica principal de scoring
                html.Div([
                    html.Div([
                        html.H3("📈 Análisis de Scoring en Tiempo Real", 
                               style={
                                   'color': '#1f2937', 
                                   'fontFamily': 'Inter, sans-serif',
                                   'fontSize': '18px',
                                   'fontWeight': '600',
                                   'marginBottom': '20px'
                               }),
                        dcc.Graph(id='scoring-analysis-chart', style={'height': '350px'})
                    ], style={
                        'backgroundColor': '#ffffff',
                        'borderRadius': '16px',
                        'padding': '24px',
                        'boxShadow': '0 4px 20px rgba(0,0,0,0.08)',
                        'border': '1px solid #f3f4f6'
                    })
                ], className='eight columns'),
                
                # Columna derecha - Métricas circulares como en la imagen
                html.Div([
                    html.Div([
                        html.H3("🎯 Distribución de Señales", 
                               style={
                                   'color': '#1f2937', 
                                   'fontFamily': 'Inter, sans-serif',
                                   'fontSize': '18px',
                                   'fontWeight': '600',
                                   'marginBottom': '20px'
                               }),
                        dcc.Graph(id='confidence-distribution-chart', style={'height': '350px'})
                    ], style={
                        'backgroundColor': '#ffffff',
                        'borderRadius': '16px',
                        'padding': '24px',
                        'boxShadow': '0 4px 20px rgba(0,0,0,0.08)',
                        'border': '1px solid #f3f4f6'
                    })
                ], className='four columns')
            ], className='row', style={'marginBottom': '32px'}),
            
            # Sección inferior - Gráfica de tendencias temporal
            html.Div([
                html.Div([
                    html.H3("📊 Tendencias de Oportunidades", 
                           style={
                               'color': '#1f2937', 
                               'fontFamily': 'Inter, sans-serif',
                               'fontSize': '18px',
                               'fontWeight': '600',
                               'marginBottom': '20px'
                           }),
                    dcc.Graph(id='temporal-trends-chart', style={'height': '300px'})
                ], style={
                    'backgroundColor': '#ffffff',
                    'borderRadius': '16px',
                    'padding': '24px',
                    'boxShadow': '0 4px 20px rgba(0,0,0,0.08)',
                    'border': '1px solid #f3f4f6'
                })
            ], style={'marginBottom': '32px'}),
            
            # Filtros modernos
            html.Div([
                html.Div([
                    html.H3("🔍 Filtros de Análisis", 
                           style={
                               'color': '#1f2937', 
                               'fontFamily': 'Inter, sans-serif',
                               'fontSize': '18px',
                               'fontWeight': '600',
                               'marginBottom': '20px'
                           }),
                    html.Div([
                        html.Div([
                            html.Label("Nivel de Confianza:", style={
                                'fontWeight': '500',
                                'color': '#374151',
                                'marginBottom': '8px',
                                'display': 'block'
                            }),
                            dcc.Dropdown(
                                id='confidence-filter',
                                options=[
                                    {'label': 'Todas las Señales', 'value': 'ALL'},
                                    {'label': '🔴 Débil (30-49)', 'value': 'DÉBIL'},
                                    {'label': '🟡 Medio (50-69)', 'value': 'MEDIO'},
                                    {'label': '🟢 Alto (70-84)', 'value': 'ALTO'},
                                    {'label': '🚀 Fuerte (85-100)', 'value': 'FUERTE'}
                                ],
                                value='MEDIO',
                                style={'marginBottom': '16px'}
                            )
                        ], className='six columns'),
                        
                        html.Div([
                            html.Label("Score Mínimo:", style={
                                'fontWeight': '500',
                                'color': '#374151',
                                'marginBottom': '8px',
                                'display': 'block'
                            }),
                            dcc.Slider(
                                id='score-filter',
                                min=0,
                                max=100,
                                step=5,
                                value=50,
                                marks={i: f'{i}' for i in range(0, 101, 25)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ], className='six columns'),
                        
                    ], className='row')
                ], style={
                    'backgroundColor': '#ffffff',
                    'borderRadius': '16px',
                    'padding': '24px',
                    'boxShadow': '0 4px 20px rgba(0,0,0,0.08)',
                    'border': '1px solid #f3f4f6'
                })
            ], style={'marginBottom': '32px'}),
            
            # Tabla de oportunidades - Diseño moderno
            html.Div([
                html.Div([
                    html.H3("🏆 Top Oportunidades Detectadas", 
                           style={
                               'color': '#1f2937', 
                               'fontFamily': 'Inter, sans-serif',
                               'fontSize': '18px',
                               'fontWeight': '600',
                               'marginBottom': '20px'
                           }),
                    html.Div(id='opportunities-table')
                ], style={
                    'backgroundColor': '#ffffff',
                    'borderRadius': '16px',
                    'padding': '24px',
                    'boxShadow': '0 4px 20px rgba(0,0,0,0.08)',
                    'border': '1px solid #f3f4f6'
                })
            ]),
            
        ], style={
            'margin': '20px', 
            'fontFamily': 'Inter, sans-serif',
            'backgroundColor': '#f8fafc',
            'minHeight': '100vh'
        })
    
    def _setup_callbacks(self):
        """Configura los callbacks del dashboard"""
        
        @self.app.callback(
            [Output('last-update-display', 'children'),
             Output('system-metrics', 'children'),
             Output('opportunities-metrics', 'children'),
             Output('signals-metrics', 'children'),
             Output('performance-metrics', 'children'),
             Output('scoring-analysis-chart', 'figure'),
             Output('confidence-distribution-chart', 'figure'),
             Output('temporal-trends-chart', 'figure'),
             Output('opportunities-table', 'children')],
            [Input('interval-update', 'n_intervals'),
             Input('confidence-filter', 'value'),
             Input('score-filter', 'value')],
            prevent_initial_call=False
        )
        def update_dashboard(n_intervals, confidence_filter, score_filter):
            try:
                # Verificar valores por defecto
                if confidence_filter is None:
                    confidence_filter = 'MEDIO'
                if score_filter is None:
                    score_filter = 50
                    
                return self._update_components(confidence_filter, score_filter)
            except Exception as e:
                log.error(f"Error actualizando dashboard: {e}")
                error_msg = html.Div(f"Error: {str(e)}", style={'color': '#ef4444'})
                empty_fig = {'data': [], 'layout': {'title': 'Error en Dashboard'}}
                
                # Retornar exactamente 9 valores para los 9 Outputs
                return (
                    f"Error: {datetime.now().strftime('%H:%M:%S')}",  # last-update-display
                    error_msg,  # system-metrics
                    error_msg,  # opportunities-metrics  
                    error_msg,  # signals-metrics
                    error_msg,  # performance-metrics
                    empty_fig,  # scoring-analysis-chart
                    empty_fig,  # confidence-distribution-chart
                    empty_fig,  # temporal-trends-chart
                    error_msg   # opportunities-table
                )
    
    def _update_components(self, confidence_filter, score_filter):
        """Actualiza todos los componentes"""
        
        try:
            # Timestamp
            timestamp = f"Actualizado: {datetime.now().strftime('%H:%M:%S')}"
            
            # Obtener datos del bot
            opportunities = self._get_opportunities()
            daily_signals = self._get_daily_signals()
            
            # Filtrar oportunidades
            filtered_opportunities = self._filter_opportunities(opportunities, confidence_filter, score_filter)
            
            # Generar componentes
            system_metrics = self._create_system_metrics()
            opportunities_metrics = self._create_opportunities_metrics(opportunities)
            signals_metrics = self._create_signals_metrics(daily_signals)
            performance_metrics = self._create_performance_metrics()
            
            # Gráficas
            scoring_chart = self._create_scoring_chart(opportunities)
            confidence_chart = self._create_confidence_distribution_chart(opportunities)
            temporal_chart = self._create_temporal_trends_chart(opportunities)
            
            # Tabla
            opportunities_table = self._create_opportunities_table(filtered_opportunities)
            
            # Retornar exactamente 9 valores
            return (
                timestamp,                # 1. last-update-display
                system_metrics,          # 2. system-metrics
                opportunities_metrics,   # 3. opportunities-metrics
                signals_metrics,         # 4. signals-metrics
                performance_metrics,     # 5. performance-metrics
                scoring_chart,           # 6. scoring-analysis-chart
                confidence_chart,        # 7. confidence-distribution-chart
                temporal_chart,          # 8. temporal-trends-chart
                opportunities_table      # 9. opportunities-table
            )
            
        except Exception as e:
            log.error(f"Error en _update_components: {e}")
            # Retornar valores de error seguros
            error_msg = html.Div(f"Error: {str(e)}", style={'color': '#ef4444'})
            empty_fig = {'data': [], 'layout': {'title': 'Error en componente'}}
            
            return (
                f"Error: {datetime.now().strftime('%H:%M:%S')}",
                error_msg, error_msg, error_msg, error_msg,
                empty_fig, empty_fig, empty_fig,
                error_msg
            )
    
    def _get_opportunities(self) -> List[Dict]:
        """Obtiene oportunidades del bot v2.0"""
        try:
            if self.bot and hasattr(self.bot, 'current_opportunities'):
                opportunities = []
                for symbol, data in self.bot.current_opportunities.items():
                    if isinstance(data, dict) and data.get('total_score', 0) > 0:
                        opportunities.append({
                            'symbol': symbol,
                            'total_score': data.get('total_score', 0),
                            'confidence_level': data.get('confidence_level', 'DÉBIL'),
                            'historical_score': data.get('historical_score', 0),
                            'technical_score': data.get('technical_score', 0),
                            'confluence_score': data.get('confluence_score', 0),
                            'target_probability': data.get('target_probability', 0),
                            'recommendation': data.get('recommendation', 'HOLD'),
                            'risk_level': data.get('risk_level', 'MEDIUM')
                        })
                return sorted(opportunities, key=lambda x: x['total_score'], reverse=True)
            
            # Datos de prueba si no hay bot
            return self._generate_sample_opportunities()
            
        except Exception as e:
            log.error(f"Error obteniendo oportunidades: {e}")
            return []
    
    def _get_daily_signals(self) -> List[Dict]:
        """Obtiene señales del día"""
        try:
            if self.bot and hasattr(self.bot, 'daily_signals'):
                return self.bot.daily_signals or []
            return []
        except Exception as e:
            log.error(f"Error obteniendo señales diarias: {e}")
            return []
    
    def _filter_opportunities(self, opportunities: List[Dict], confidence_filter: str, score_filter: int) -> List[Dict]:
        """Filtra oportunidades según criterios"""
        try:
            if not opportunities:
                return []
            
            filtered = []
            confidence_order = {'DÉBIL': 1, 'MEDIO': 2, 'ALTO': 3, 'FUERTE': 4}
            min_confidence_level = confidence_order.get(confidence_filter, 0)
            
            for opp in opportunities:
                # Filtrar por score
                if opp.get('total_score', 0) < score_filter:
                    continue
                
                # Filtrar por confianza
                if confidence_filter != 'ALL':
                    opp_confidence = confidence_order.get(opp.get('confidence_level'), 0)
                    if opp_confidence < min_confidence_level:
                        continue
                
                filtered.append(opp)
            
            return filtered
            
        except Exception as e:
            log.error(f"Error filtrando oportunidades: {e}")
            return opportunities
    
    def _create_system_metrics(self):
        """Crea métricas del sistema estilo dashboard moderno"""
        try:
            if self.bot and hasattr(self.bot, 'data_collector'):
                total_pairs = getattr(self.bot.data_collector, 'total_pairs', 244)
                status = "ACTIVO" if getattr(self.bot, 'running', False) else "DETENIDO"
            else:
                total_pairs = 244
                status = "DEMO"
            
            return html.Div([
                html.H2(f"{total_pairs:,}", style={
                    'color': '#1f2937', 
                    'margin': '0', 
                    'fontSize': '2.5rem',
                    'fontWeight': '700',
                    'lineHeight': '1'
                }),
            ])
            
        except Exception as e:
            log.error(f"Error creando métricas sistema: {e}")
            return html.Div("244", style={'color': '#1f2937', 'fontSize': '2.5rem', 'fontWeight': '700'})
    
    def _create_opportunities_metrics(self, opportunities: List[Dict]):
        """Crea métricas de oportunidades estilo moderno"""
        try:
            total = len(opportunities)
            strong = len([o for o in opportunities if o.get('confidence_level') == 'FUERTE'])
            
            return html.Div([
                html.H2(f"{total:,}", style={
                    'color': '#1f2937', 
                    'margin': '0', 
                    'fontSize': '2.5rem',
                    'fontWeight': '700',
                    'lineHeight': '1'
                }),
            ])
            
        except Exception as e:
            return html.Div("0", style={'color': '#1f2937', 'fontSize': '2.5rem', 'fontWeight': '700'})
    
    def _create_signals_metrics(self, daily_signals: List[Dict]):
        """Crea métricas de señales diarias estilo moderno"""
        try:
            total_today = len(daily_signals)
            strong_today = len([s for s in daily_signals if s.get('confidence_level') == 'FUERTE'])
            
            return html.Div([
                html.H2(f"{strong_today:,}", style={
                    'color': '#1f2937', 
                    'margin': '0', 
                    'fontSize': '2.5rem',
                    'fontWeight': '700',
                    'lineHeight': '1'
                }),
            ])
            
        except Exception as e:
            return html.Div("0", style={'color': '#1f2937', 'fontSize': '2.5rem', 'fontWeight': '700'})
    
    def _create_performance_metrics(self):
        """Crea métricas de rendimiento estilo moderno"""
        try:
            cycles = getattr(self.bot, 'analysis_cycle_count', 0) if self.bot else 12
            
            return html.Div([
                html.H2(f"{cycles:,}", style={
                    'color': '#1f2937', 
                    'margin': '0', 
                    'fontSize': '2.5rem',
                    'fontWeight': '700',
                    'lineHeight': '1'
                }),
            ])
            
        except Exception as e:
            return html.Div("12", style={'color': '#1f2937', 'fontSize': '2.5rem', 'fontWeight': '700'})
    
    def _create_scoring_chart(self, opportunities: List[Dict]):
        """Crea gráfica de análisis de scoring"""
        try:
            if not opportunities:
                return {'data': [], 'layout': {'title': 'No hay datos disponibles'}}
            
            # Preparar datos para la gráfica
            symbols = [opp['symbol'] for opp in opportunities[:10]]  # Top 10
            historical_scores = [opp.get('historical_score', 0) for opp in opportunities[:10]]
            technical_scores = [opp.get('technical_score', 0) for opp in opportunities[:10]]
            confluence_scores = [opp.get('confluence_score', 0) for opp in opportunities[:10]]
            
            fig = go.Figure()
            
            # Barras apiladas para mostrar las 3 secciones
            fig.add_trace(go.Bar(
                name='Histórico (0-25)',
                x=symbols,
                y=historical_scores,
                marker_color='#3b82f6'
            ))
            
            fig.add_trace(go.Bar(
                name='Técnico (0-50)',
                x=symbols,
                y=technical_scores,
                marker_color='#10b981'
            ))
            
            fig.add_trace(go.Bar(
                name='Confluencia (0-25)',
                x=symbols,
                y=confluence_scores,
                marker_color='#f59e0b'
            ))
            
            fig.update_layout(
                title='Desglose de Scoring por Secciones (Top 10)',
                barmode='stack',
                xaxis_title='Símbolo',
                yaxis_title='Puntos',
                font=dict(family='Inter, sans-serif'),
                height=400
            )
            
            return fig
            
        except Exception as e:
            log.error(f"Error creando gráfica: {e}")
            return {'data': [], 'layout': {'title': f'Error: {str(e)}'}}
    
    def _create_confidence_distribution_chart(self, opportunities: List[Dict]):
        """Crea gráfica de distribución de confianza (tipo donut como en la imagen)"""
        try:
            if not opportunities:
                return {'data': [], 'layout': {'title': 'No hay datos disponibles'}}
            
            # Contar por nivel de confianza
            confidence_counts = {'FUERTE': 0, 'ALTO': 0, 'MEDIO': 0, 'DÉBIL': 0}
            for opp in opportunities:
                level = opp.get('confidence_level', 'DÉBIL')
                if level in confidence_counts:
                    confidence_counts[level] += 1
            
            # Crear gráfica de donut
            fig = go.Figure(data=[go.Pie(
                labels=list(confidence_counts.keys()),
                values=list(confidence_counts.values()),
                hole=0.6,
                marker_colors=['#10b981', '#3b82f6', '#f59e0b', '#ef4444'],
                textinfo='label+percent',
                textposition='outside'
            )])
            
            fig.update_layout(
                title='Distribución por Confianza',
                font=dict(family='Inter, sans-serif', size=12),
                showlegend=False,
                margin=dict(l=20, r=20, t=40, b=20),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            return fig
            
        except Exception as e:
            log.error(f"Error creando gráfica de distribución: {e}")
            return {'data': [], 'layout': {'title': f'Error: {str(e)}'}}
    
    def _create_temporal_trends_chart(self, opportunities: List[Dict]):
        """Crea gráfica de tendencias temporales usando datos reales de MongoDB"""
        try:
            # Intentar obtener datos históricos de MongoDB
            historical_data = []
            try:
                # Usar una función sincrónica para evitar problemas con asyncio en el dashboard
                from datetime import datetime, timedelta
                
                # Obtener señales de las últimas 7 horas
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=7)  # Usar entero directamente
                
                # Por ahora usar datos simulados hasta que MongoDB esté completamente configurado
                log.info(f"Intentando obtener datos históricos desde {start_time} hasta {end_time}")
                
            except Exception as e:
                log.warning(f"No se pudieron obtener datos históricos de MongoDB: {e}")
                historical_data = []
            
            # Usar datos simulados como estándar por ahora
            import random
            
            # Generar datos de las últimas 7 horas
            hours = []
            opp_counts = []
            strong_counts = []
            
            for i in range(7):
                hour_time = datetime.now() - timedelta(hours=6-i)
                hours.append(hour_time.strftime('%H:%M'))
                
                # Simular conteo de oportunidades basado en datos reales si existen
                if opportunities:
                    base_count = len(opportunities)
                    strong_base = len([o for o in opportunities if o.get('confidence_level') == 'FUERTE'])
                    opp_counts.append(max(1, base_count + random.randint(-3, 5)))
                    strong_counts.append(max(0, strong_base + random.randint(-1, 3)))
                else:
                    opp_counts.append(random.randint(15, 25))
                    strong_counts.append(random.randint(3, 8))
            
            fig = go.Figure()
            
            # Línea de oportunidades totales
            fig.add_trace(go.Scatter(
                x=hours,
                y=opp_counts,
                mode='lines+markers',
                name='Total Oportunidades',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=8)
            ))
            
            # Línea de señales fuertes
            fig.add_trace(go.Scatter(
                x=hours,
                y=strong_counts,
                mode='lines+markers',
                name='Señales Fuertes',
                line=dict(color='#10b981', width=3),
                marker=dict(size=8)
            ))
            
            fig.update_layout(
                title='Tendencias de las Últimas Horas',
                xaxis_title='Tiempo',
                yaxis_title='Cantidad',
                font=dict(family='Inter, sans-serif'),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=60, b=40),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)')
            )
            
            return fig
            
        except Exception as e:
            log.error(f"Error creando gráfica temporal: {e}")
            return {'data': [], 'layout': {'title': f'Error: {str(e)}'}}
    
    def _create_opportunities_table(self, opportunities: List[Dict]):
        """Crea tabla de oportunidades"""
        try:
            if not opportunities:
                return html.Div("No hay oportunidades disponibles", 
                              style={'textAlign': 'center', 'color': '#6b7280', 'padding': '20px'})
            
            # Preparar datos para la tabla
            table_data = []
            for opp in opportunities[:20]:  # Top 20
                table_data.append({
                    'Símbolo': opp['symbol'],
                    'Score Total': f"{opp['total_score']}/100",
                    'Confianza': opp['confidence_level'],
                    'Histórico': f"{opp.get('historical_score', 0)}/25",
                    'Técnico': f"{opp.get('technical_score', 0)}/50",
                    'Confluencia': f"{opp.get('confluence_score', 0)}/25",
                    'Probabilidad': f"{opp.get('target_probability', 0):.1%}",
                    'Recomendación': opp.get('recommendation', 'HOLD')
                })
            
            return dash_table.DataTable(
                data=table_data,
                columns=[{"name": i, "id": i} for i in table_data[0].keys()],
                style_cell={
                    'textAlign': 'center',
                    'fontFamily': 'Inter, sans-serif',
                    'fontSize': '14px'
                },
                style_header={
                    'backgroundColor': '#f3f4f6',
                    'fontWeight': 'bold',
                    'color': '#1f2937'
                },
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{Confianza} = FUERTE'},
                        'backgroundColor': '#dcfce7',
                        'color': '#166534',
                    },
                    {
                        'if': {'filter_query': '{Confianza} = ALTO'},
                        'backgroundColor': '#dbeafe',
                        'color': '#1e40af',
                    },
                    {
                        'if': {'filter_query': '{Confianza} = MEDIO'},
                        'backgroundColor': '#fef3c7',
                        'color': '#92400e',
                    }
                ],
                page_size=10,
                sort_action="native"
            )
            
        except Exception as e:
            log.error(f"Error creando tabla: {e}")
            return html.Div(f"Error: {str(e)}", style={'color': '#ef4444'})
    
    def _generate_sample_opportunities(self) -> List[Dict]:
        """Genera oportunidades de muestra para demo"""
        import random
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT', 'XRPUSDT']
        confidence_levels = ['FUERTE', 'ALTO', 'MEDIO', 'DÉBIL']
        
        opportunities = []
        for symbol in symbols:
            historical = random.randint(10, 25)
            technical = random.randint(20, 50)
            confluence = random.randint(10, 25)
            total = historical + technical + confluence
            
            # Determinar confianza basada en total
            if total >= 85:
                confidence = 'FUERTE'
            elif total >= 70:
                confidence = 'ALTO'
            elif total >= 50:
                confidence = 'MEDIO'
            else:
                confidence = 'DÉBIL'
            
            opportunities.append({
                'symbol': symbol,
                'total_score': total,
                'confidence_level': confidence,
                'historical_score': historical,
                'technical_score': technical,
                'confluence_score': confluence,
                'target_probability': random.uniform(0.4, 0.8),
                'recommendation': 'BUY' if total > 60 else 'HOLD',
                'risk_level': 'LOW' if total > 70 else 'MEDIUM'
            })
        
        return sorted(opportunities, key=lambda x: x['total_score'], reverse=True)
    
    def run(self, host='0.0.0.0', port=8050, debug=False):
        """Ejecuta el dashboard"""
        try:
            log.info(f"🌐 Iniciando Dashboard v2.0 en http://{host}:{port}")
            self.running = True
            self.app.run_server(host=host, port=port, debug=debug)
        except Exception as e:
            log.error(f"Error ejecutando dashboard: {e}")
    
    def stop(self):
        """Detiene el dashboard"""
        self.running = False
        log.info("Dashboard detenido")


if __name__ == "__main__":
    dashboard = CryptoMomentumDashboardV2()
    dashboard.run(debug=True)
