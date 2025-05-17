import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# API endpoint
API_URL = "http://localhost:8000"

# Set page configuration
st.set_page_config(
    page_title="Machine Performance Dashboard",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #111827;
        color: white;
    }
    .stApp {
        background-color: #111827;
    }
    h1, h2, h3, h4, h5, h6 {
        color: white !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1f2937;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        color: white;
    }
    .stTabs [aria-selected="true"] {
        background-color: #374151;
        border-radius: 5px;
    }
    .metric-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .machine-card {
        background-color: #1f2937;
        border-radius: 10px;
        padding: 15px;
        transition: transform 0.2s;
        cursor: pointer;
    }
    .machine-card:hover {
        transform: translateY(-5px);
    }
    .operational {
        border-left: 5px solid #10b981;
    }
    .warning {
        border-left: 5px solid #f59e0b;
    }
    .failure {
        border-left: 5px solid #ef4444;
    }
    .stProgress > div > div > div > div {
        background-color: #111827;
    }
    .status-operational {
        color: #10b981;
    }
    .status-warning {
        color: #f59e0b;
    }
    .status-failure {
        color: #ef4444;
    }
    .alert-badge {
        padding: 5px 10px;
        border-radius: 20px;
        font-weight: bold;
        margin: 5px 0;
    }
    .alert-critical {
        background-color: #ef4444;
        color: white;
    }
    .alert-warning {
        background-color: #f59e0b;
        color: black;
    }
    .alert-normal {
        background-color: #10b981;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Functions to fetch data from API
def get_all_lathes():
    try:
        response = requests.get(f"{API_URL}/lathes")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching lathes data: {e}")
        return []

def get_lathe_details(lathe_id):
    try:
        response = requests.get(f"{API_URL}/lathes/{lathe_id}")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching lathe details: {e}")
        return None

def get_lathe_sensor_data(lathe_id):
    try:
        response = requests.get(f"{API_URL}/lathes/{lathe_id}/sensor-data")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching lathe sensor data: {e}")
        return None

def get_lathe_product_analysis(lathe_id):
    try:
        response = requests.get(f"{API_URL}/lathes/{lathe_id}/product-analysis")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching lathe product analysis: {e}")
        return None

def get_lathe_history(lathe_id, hours=24):
    try:
        response = requests.get(f"{API_URL}/lathes/{lathe_id}/history?hours={hours}")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching lathe history: {e}")
        return None

# Custom components
def render_status_badge(status):
    if status == "Operational":
        return f"<span class='status-operational'>● {status}</span>"
    elif status == "Warning":
        return f"<span class='status-warning'>● {status}</span>"
    else:
        return f"<span class='status-failure'>● {status}</span>"

def render_health_bar(value):
    if isinstance(value, (int, float)):
        if value >= 80:
            color = "#10b981"  # green
        elif value >= 60:
            color = "#f59e0b"  # yellow
        else:
            color = "#ef4444"  # red
        return st.progress(int(value)/100, text=f"{value}%")
    return st.progress(0, text="N/A")

def generate_alert(status, message):
    if status == "critical":
        return f"<div class='alert-badge alert-critical'>{message}</div>"
    elif status == "warning":
        return f"<div class='alert-badge alert-warning'>{message}</div>"
    else:
        return f"<div class='alert-badge alert-normal'>{message}</div>"

def show_dashboard():
    st.title("Machine Performance Dashboard")
    st.markdown("Monitor performance, uptime, and health status of all lathe machines")
    
    # Fetch all lathes
    lathes = get_all_lathes()
    
    if not lathes:
        st.warning("No lathe data available. Please ensure the backend is running and MongoDB is populated.")
        return
    
    # Display lathe cards in a grid
    cols_per_row = 4
    rows = (len(lathes) + cols_per_row - 1) // cols_per_row
    
    for row in range(rows):
        cols = st.columns(cols_per_row)
        for col in range(cols_per_row):
            idx = row * cols_per_row + col
            if idx < len(lathes):
                lathe = lathes[idx]
                with cols[col]:
                    status = lathe.get('status', 'Unknown').lower()
                    
                    with st.container():
                        st.markdown(f"""
                        <div class='machine-card {status}'>
                            <h3>{lathe.get('name', f"Lathe {lathe.get('lathe_id', '')}")} {render_status_badge(lathe.get('status', 'Unknown'))}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("#### Health Score")
                        render_health_bar(lathe.get('health_score'))
                        
                        st.markdown("#### Uptime")
                        render_health_bar(lathe.get('uptime'))
                        
                        if st.button(f"View Details", key=f"btn_{lathe.get('lathe_id', idx)}"):
                            st.session_state.selected_lathe = lathe.get('lathe_id')
                            st.session_state.view = "lathe_details"
                            st.rerun()

def show_lathe_details():
    if 'selected_lathe' not in st.session_state or not st.session_state.selected_lathe:
        st.warning("No lathe selected. Returning to dashboard.")
        st.session_state.view = "dashboard"
        st.rerun()
        return
    
    lathe_id = st.session_state.selected_lathe
    lathe_details = get_lathe_details(lathe_id)
    history_data = get_lathe_history(lathe_id)
    
    if not lathe_details:
        st.warning(f"No data available for Lathe {lathe_id}")
        if st.button("← Back to Dashboard"):
            st.session_state.view = "dashboard"
            st.rerun()
        return
    
    # Back button
    col1, col2 = st.columns([1, 11])
    with col1:
        if st.button("← Back"):
            st.session_state.view = "dashboard"
            st.rerun()
    
    with col2:
        lathe_name = lathe_details.get('name', f"Lathe {lathe_id}")
        st.title(f"{lathe_name} Details")
        status = lathe_details.get('status', 'Unknown')
        st.markdown(f"Current Status: {render_status_badge(status)}", unsafe_allow_html=True)
    
    # Current alerts section
    st.subheader("Current Alerts")
    alerts = []
    
    # Check temperature
    current_temp = lathe_details.get('current_temperature', 0)
    if current_temp > 80:
        alerts.append(generate_alert("critical", f"High Temperature: {current_temp}°C"))
    elif current_temp > 60:
        alerts.append(generate_alert("warning", f"Elevated Temperature: {current_temp}°C"))
    else:
        alerts.append(generate_alert("normal", f"Temperature Normal: {current_temp}°C"))
    
    # Check vibration
    current_vib = lathe_details.get('current_vibration', 0)
    if current_vib > 5:
        alerts.append(generate_alert("critical", f"High Vibration: {current_vib}"))
    elif current_vib > 3:
        alerts.append(generate_alert("warning", f"Elevated Vibration: {current_vib}"))
    else:
        alerts.append(generate_alert("normal", f"Vibration Normal: {current_vib}"))
    
    # Check tool wear
    current_wear = lathe_details.get('current_tool_wear', 0)
    if current_wear > 80:
        alerts.append(generate_alert("critical", f"High Tool Wear: {current_wear}%"))
    elif current_wear > 60:
        alerts.append(generate_alert("warning", f"Elevated Tool Wear: {current_wear}%"))
    else:
        alerts.append(generate_alert("normal", f"Tool Wear Normal: {current_wear}%"))
    
    # Display alerts in columns
    alert_cols = st.columns(3)
    for i, alert in enumerate(alerts):
        with alert_cols[i % 3]:
            st.markdown(alert, unsafe_allow_html=True)
    
    # Tabs for different analysis
    tab1, tab2, tab3 = st.tabs(["Sensor Data Analysis", "Product Analysis", "Production Analytics"])
    
    # Sensor Data Tab
    with tab1:
        sensor_data = get_lathe_sensor_data(lathe_id)
        
        if not sensor_data:
            st.warning("Sensor data not available")
        else:
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                health_score = lathe_details.get('health_score', 'N/A')
                health_score_display = f"{health_score}%" if isinstance(health_score, (int, float)) else health_score
                st.metric("Health Score", health_score_display)
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col2:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                uptime = lathe_details.get('uptime', 'N/A')
                uptime_display = f"{uptime}%" if isinstance(uptime, (int, float)) else uptime
                st.metric("Uptime", uptime_display)
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col3:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                failure_count = lathe_details.get('failure_count', 'N/A')
                st.metric("Failure Count", failure_count)
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col4:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                current_job = lathe_details.get('current_job', {}).get('JobID', 'N/A')
                st.metric("Current Job", current_job)
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Health score trend
            if history_data:
                st.subheader("Health Score Trend (Last 24 Hours)")
                health_history = [{'timestamp': h['timestamp'], 'health_score': h['health_score']} 
                                for h in history_data if 'health_score' in h]
                
                if health_history:
                    df_health = pd.DataFrame(health_history)
                    df_health['timestamp'] = pd.to_datetime(df_health['timestamp'])
                    
                    fig = px.line(
                        df_health,
                        x='timestamp',
                        y='health_score',
                        title="Health Score Trend",
                        labels={'health_score': 'Health Score (%)', 'timestamp': 'Time'}
                    )
                    fig.update_layout(
                        height=300,
                        paper_bgcolor="#1f2937",
                        plot_bgcolor="#1f2937",
                        font={'color': "white"},
                        xaxis_title="Time",
                        yaxis_title="Health Score (%)",
                        yaxis_range=[0, 100]
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            # Sensor visualizations
            if 'stats' not in sensor_data:
                st.warning("Sensor statistics not available in the response")
            else:
                st.subheader("Sensor Readings")
                
                # Temperature charts
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'Temperature' in sensor_data['stats']:
                        temp_stats = sensor_data['stats']['Temperature']
                        fig = go.Figure()
                        fig.add_trace(go.Indicator(
                            mode="gauge+number",
                            value=temp_stats.get('avg', 0),
                            title={"text": "Temperature [°C]"},
                            gauge={
                                'axis': {'range': [temp_stats.get('min', 0), 
                                        temp_stats.get('max', 100)]},
                                'bar': {'color': "#ef4444"},
                                'bgcolor': "gray",
                                'threshold': {
                                    'line': {'color': "white", 'width': 2},
                                    'thickness': 0.75,
                                    'value': 80
                                }
                            }
                        ))
                        fig.update_layout(
                            height=250,
                            paper_bgcolor="#1f2937",
                            plot_bgcolor="#1f2937",
                            font={'color': "white"}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Temperature data not available")
                
                with col2:
                    if 'Vibration' in sensor_data['stats']:
                        vib_stats = sensor_data['stats']['Vibration']
                        fig = go.Figure()
                        fig.add_trace(go.Indicator(
                            mode="gauge+number",
                            value=vib_stats.get('avg', 0),
                            title={"text": "Vibration"},
                            gauge={
                                'axis': {'range': [vib_stats.get('min', 0), 
                                        vib_stats.get('max', 10)]},
                                'bar': {'color': "#f59e0b"},
                                'bgcolor': "gray",
                                'threshold': {
                                    'line': {'color': "white", 'width': 2},
                                    'thickness': 0.75,
                                    'value': 5
                                }
                            }
                        ))
                        fig.update_layout(
                            height=250,
                            paper_bgcolor="#1f2937",
                            plot_bgcolor="#1f2937",
                            font={'color': "white"}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Vibration data not available")
                
                # RPM and Power
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'RPM' in sensor_data['stats']:
                        rpm_stats = sensor_data['stats']['RPM']
                        fig = go.Figure()
                        fig.add_trace(go.Indicator(
                            mode="gauge+number",
                            value=rpm_stats.get('avg', 0),
                            title={"text": "Rotational Speed [RPM]"},
                            gauge={
                                'axis': {'range': [rpm_stats.get('min', 0), 
                                                rpm_stats.get('max', 3000)]},
                                'bar': {'color': "#10b981"},
                                'bgcolor': "gray",
                                'threshold': {
                                    'line': {'color': "white", 'width': 2},
                                    'thickness': 0.75,
                                    'value': 2000
                                }
                            }
                        ))
                        fig.update_layout(
                            height=250,
                            paper_bgcolor="#1f2937",
                            plot_bgcolor="#1f2937",
                            font={'color': "white"}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("RPM data not available")
                
                with col2:
                    if 'Power' in sensor_data['stats']:
                        power_stats = sensor_data['stats']['Power']
                        fig = go.Figure()
                        fig.add_trace(go.Indicator(
                            mode="gauge+number",
                            value=power_stats.get('avg', 0),
                            title={"text": "Power [kW]"},
                            gauge={
                                'axis': {'range': [power_stats.get('min', 0), 
                                        power_stats.get('max', 15)]},
                                'bar': {'color': "#10b981"},
                                'bgcolor': "gray",
                                'threshold': {
                                    'line': {'color': "white", 'width': 2},
                                    'thickness': 0.75,
                                    'value': 10
                                }
                            }
                        ))
                        fig.update_layout(
                            height=250,
                            paper_bgcolor="#1f2937",
                            plot_bgcolor="#1f2937",
                            font={'color': "white"}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Power data not available")
                
                # Tool Wear
                if 'ToolWear' in sensor_data['stats']:
                    tool_stats = sensor_data['stats']['ToolWear']
                    fig = go.Figure()
                    fig.add_trace(go.Indicator(
                        mode="gauge+number",
                        value=tool_stats.get('avg', 0),
                        title={"text": "Tool Wear [%]"},
                        gauge={
                            'axis': {'range': [tool_stats.get('min', 0), 
                                    tool_stats.get('max', 100)]},
                            'bar': {'color': "#f59e0b"},
                            'bgcolor': "gray",
                            'threshold': {
                                'line': {'color': "white", 'width': 2},
                                'thickness': 0.75,
                                'value': 80
                            }
                        }
                    ))
                    fig.update_layout(
                        height=250,
                        paper_bgcolor="#1f2937",
                        plot_bgcolor="#1f2937",
                        font={'color': "white"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Tool wear data not available")
                
                # Time series charts for sensor data
                if history_data:
                    st.subheader("Sensor Data Trends (Last 24 Hours)")
                    
                    # Prepare data
                    timestamps = [h['timestamp'] for h in history_data]
                    temps = [h.get('Temperature', None) for h in history_data]
                    vibs = [h.get('Vibration', None) for h in history_data]
                    rpms = [h.get('RPM', None) for h in history_data]
                    powers = [h.get('Power', None) for h in history_data]
                    tool_wears = [h.get('ToolWear', None) for h in history_data]
                    
                    # Create figure with secondary y-axis
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    
                    # Add traces
                    if any(temps):
                        fig.add_trace(
                            go.Scatter(x=timestamps, y=temps, name="Temperature (°C)"),
                            secondary_y=False,
                        )
                    
                    if any(vibs):
                        fig.add_trace(
                            go.Scatter(x=timestamps, y=vibs, name="Vibration"),
                            secondary_y=False,
                        )
                    
                    if any(rpms):
                        fig.add_trace(
                            go.Scatter(x=timestamps, y=rpms, name="RPM"),
                            secondary_y=True,
                        )
                    
                    if any(powers):
                        fig.add_trace(
                            go.Scatter(x=timestamps, y=powers, name="Power (kW)"),
                            secondary_y=True,
                        )
                    
                    if any(tool_wears):
                        fig.add_trace(
                            go.Scatter(x=timestamps, y=tool_wears, name="Tool Wear (%)"),
                            secondary_y=False,
                        )
                    
                    # Add figure title
                    fig.update_layout(
                        title_text="Sensor Data Over Time",
                        height=400,
                        paper_bgcolor="#1f2937",
                        plot_bgcolor="#1f2937",
                        font={'color': "white"}
                    )
                    
                    # Set x-axis title
                    fig.update_xaxes(title_text="Time")
                    
                    # Set y-axes titles
                    fig.update_yaxes(title_text="Temperature/Vibration/Tool Wear", secondary_y=False)
                    fig.update_yaxes(title_text="RPM/Power", secondary_y=True)
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # Radar Chart comparing all parameters
                st.subheader("Parameter Comparison")
                
                # Normalize values for radar chart
                radar_data = {}
                valid_params = ['Temperature', 'Vibration', 'RPM', 'Power', 'ToolWear']
                
                for param in valid_params:
                    if param in sensor_data['stats']:
                        min_val = sensor_data['stats'][param].get('min', 0)
                        max_val = sensor_data['stats'][param].get('max', 1)
                        avg_val = sensor_data['stats'][param].get('avg', 0)
                        
                        # Normalize to 0-1 range
                        if max_val != min_val:
                            normalized = (avg_val - min_val) / (max_val - min_val)
                        else:
                            normalized = 0.5
                        
                        radar_data[param] = normalized
                
                if radar_data:
                    # Create radar chart
                    categories = list(radar_data.keys())
                    values = list(radar_data.values())
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=categories,
                        fill='toself',
                        name='Parameters',
                        line_color='#10b981'
                    ))
                    
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 1]
                            )
                        ),
                        height=400,
                        paper_bgcolor="#1f2937",
                        plot_bgcolor="#1f2937",
                        font={'color': "white"}
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No valid parameters available for radar chart")
    
    # Product Analysis Tab
    with tab2:
        product_data = get_lathe_product_analysis(lathe_id)
        
        if not product_data:
            st.warning("Product analysis data not available")
        else:
            # Product Type Distribution
            st.subheader("Product Type Distribution")
            
            if 'product_types' in product_data and product_data['product_types']:
                # Create pie chart
                fig = px.pie(
                    values=list(product_data['product_types'].values()),
                    names=list(product_data['product_types'].keys()),
                    title="Product Types"
                )
                fig.update_layout(
                    height=350,
                    paper_bgcolor="#1f2937",
                    plot_bgcolor="#1f2937",
                    font={'color': "white"}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Product type distribution data not available")
                
            # Product Quality Analysis
            st.subheader("Product Quality Analysis")
            
            if 'product_quality' in product_data and product_data['product_quality']:
                # Create bar chart for failure rates
                product_types = list(product_data['product_quality'].keys())
                failure_rates = []
                health_scores = []
                
                for pt in product_types:
                    if 'failure_rate' in product_data['product_quality'][pt]:
                        failure_rates.append(product_data['product_quality'][pt]['failure_rate'])
                    if 'avg_health_score' in product_data['product_quality'][pt]:
                        health_scores.append(product_data['product_quality'][pt]['avg_health_score'])
                
                # Two column layout
                col1, col2 = st.columns(2)
                
                with col1:
                    if failure_rates:
                        fig = px.bar(
                            x=product_types,
                            y=failure_rates,
                            labels={'x': 'Product Type', 'y': 'Failure Rate (%)'},
                            title="Failure Rate by Product Type",
                            color=failure_rates,
                            color_continuous_scale=['green', 'yellow', 'red']
                        )
                        fig.update_layout(
                            height=350,
                            paper_bgcolor="#1f2937",
                            plot_bgcolor="#1f2937",
                            font={'color': "white"}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Failure rate data not available")
                
                with col2:
                    if health_scores:
                        fig = px.bar(
                            x=product_types,
                            y=health_scores,
                            labels={'x': 'Product Type', 'y': 'Health Score'},
                            title="Health Score by Product Type",
                            color=health_scores,
                            color_continuous_scale=['red', 'yellow', 'green']
                        )
                        fig.update_layout(
                            height=350,
                            paper_bgcolor="#1f2937",
                            plot_bgcolor="#1f2937",
                            font={'color': "white"}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Health score data not available")
            
            # Parameters by Product Type
            st.subheader("Parameters by Product Type")
            
            if 'params_by_type' in product_data and product_data['params_by_type']:
                # Create a dataframe from params_by_type
                params_data = []
                for product_type, params in product_data['params_by_type'].items():
                    for param_name, value in params.items():
                        params_data.append({
                            'Product Type': product_type,
                            'Parameter': param_name,
                            'Value': value
                        })
                
                if params_data:
                    df_params = pd.DataFrame(params_data)
                    
                    # Create grouped bar chart
                    fig = px.bar(
                        df_params,
                        x='Parameter',
                        y='Value',
                        color='Product Type',
                        barmode='group',
                        title="Machine Parameters by Product Type"
                    )
                    fig.update_layout(
                        height=400,
                        paper_bgcolor="#1f2937",
                        plot_bgcolor="#1f2937",
                        font={'color': "white"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No parameter data available by product type")
            
            # Tool Wear vs Temperature by Product Type
            st.subheader("Tool Wear vs Temperature by Product Type")
            
            if 'params_by_type' in product_data and product_data['params_by_type']:
                # Extract data for scatter plot
                scatter_data = []
                for product_type, params in product_data['params_by_type'].items():
                    if 'Temperature' in params and 'ToolWear' in params:
                        scatter_data.append({
                            'Product Type': product_type,
                            'Temperature': params['Temperature'],
                            'ToolWear': params['ToolWear']
                        })
                
                if scatter_data:
                    df_scatter = pd.DataFrame(scatter_data)
                    
                    # Create scatter plot
                    fig = px.scatter(
                        df_scatter,
                        x='Temperature',
                        y='ToolWear',
                        color='Product Type',
                        size=[30] * len(scatter_data),
                        title="Tool Wear vs Temperature"
                    )
                    fig.update_layout(
                        height=400,
                        paper_bgcolor="#1f2937",
                        plot_bgcolor="#1f2937",
                        font={'color': "white"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Insufficient data for Tool Wear vs Temperature analysis")
            
            # Power Consumption Profile
            st.subheader("Power Consumption Profile by Product Type")
            
            if 'params_by_type' in product_data and product_data['params_by_type']:
                power_data = []
                for product_type, params in product_data['params_by_type'].items():
                    if 'Power' in params:
                        power_data.append({
                            'Product Type': product_type,
                            'Power (kW)': params['Power']
                        })
                
                if power_data:
                    df_power = pd.DataFrame(power_data)
                    
                    fig = px.line(
                        df_power,
                        x='Product Type',
                        y='Power (kW)',
                        title="Power Consumption by Product Type",
                        markers=True
                    )
                    fig.update_layout(
                        height=400,
                        paper_bgcolor="#1f2937",
                        plot_bgcolor="#1f2937",
                        font={'color': "white"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Insufficient data for Power Consumption analysis")
    
    # Production Analytics Tab
    with tab3:
        st.subheader("Production Capacity")
        
        # Current job metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            current_job = lathe_details.get('current_job', {})
            job_id = current_job.get('JobID', 'N/A')
            st.metric("Current Job ID", job_id)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            jobs_completed = lathe_details.get('jobs_completed_today', 0)
            job_target = lathe_details.get('daily_job_target', 10)
            st.metric("Jobs Completed Today", f"{jobs_completed}/{job_target}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            avg_job_duration = lathe_details.get('avg_job_duration_minutes', 'N/A')
            st.metric("Average Job Duration", f"{avg_job_duration} mins" if isinstance(avg_job_duration, (int, float)) else avg_job_duration)
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Capacity utilization
        st.subheader("Capacity Utilization")
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_rpm = lathe_details.get('current_rpm', 0)
            max_rpm = 3000  # Assuming max RPM is 3000
            rpm_utilization = (current_rpm / max_rpm) * 100 if max_rpm > 0 else 0
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=rpm_utilization,
                title={'text': "RPM Utilization (%)"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#10b981"},
                    'threshold': {
                        'line': {'color': "white", 'width': 2},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig.update_layout(
                height=250,
                paper_bgcolor="#1f2937",
                plot_bgcolor="#1f2937",
                font={'color': "white"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            current_power = lathe_details.get('current_power', 0)
            max_power = 15  # Assuming max power is 15 kW
            power_utilization = (current_power / max_power) * 100 if max_power > 0 else 0
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=power_utilization,
                title={'text': "Power Utilization (%)"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#10b981"},
                    'threshold': {
                        'line': {'color': "white", 'width': 2},
                        'thickness': 0.75,
                        'value': 80
                    }
                }
            ))
            fig.update_layout(
                height=250,
                paper_bgcolor="#1f2937",
                plot_bgcolor="#1f2937",
                font={'color': "white"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Production trends
        if history_data:
            st.subheader("Production Trends (Last 24 Hours)")
            
            # Prepare job completion data
            job_counts = {}
            for h in history_data:
                if 'current_job' in h and h['current_job']:
                    job_id = h['current_job'].get('JobID', '')
                    timestamp = pd.to_datetime(h['timestamp'])
                    hour = timestamp.replace(minute=0, second=0, microsecond=0)
                    
                    if hour not in job_counts:
                        job_counts[hour] = {'count': 0, 'materials': set()}
                    
                    job_counts[hour]['count'] += 1
                    if 'Material' in h['current_job']:
                        job_counts[hour]['materials'].add(h['current_job']['Material'])
            
            if job_counts:
                # Create dataframe for plotting
                hours = sorted(job_counts.keys())
                counts = [job_counts[h]['count'] for h in hours]
                materials = [', '.join(job_counts[h]['materials']) if job_counts[h]['materials'] else 'Unknown' for h in hours]
                
                df_jobs = pd.DataFrame({
                    'Hour': hours,
                    'Jobs Completed': counts,
                    'Materials': materials
                })
                
                # Create bar chart
                fig = px.bar(
                    df_jobs,
                    x='Hour',
                    y='Jobs Completed',
                    color='Materials',
                    title="Jobs Completed by Hour",
                    labels={'Hour': 'Time', 'Jobs Completed': 'Number of Jobs'}
                )
                fig.update_layout(
                    height=400,
                    paper_bgcolor="#1f2937",
                    plot_bgcolor="#1f2937",
                    font={'color': "white"}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Optimal RPM by Material
        if 'params_by_type' in product_data and product_data['params_by_type']:
            st.subheader("Optimal RPM by Material")
            
            rpm_data = []
            for material, params in product_data['params_by_type'].items():
                if 'RPM' in params:
                    rpm_data.append({
                        'Material': material,
                        'Actual RPM': params['RPM'],
                        'Recommended RPM': params.get('recommended_rpm', params['RPM'] * 0.9)  # Placeholder if no recommended RPM
                    })
            
            if rpm_data:
                df_rpm = pd.DataFrame(rpm_data)
                
                fig = px.bar(
                    df_rpm,
                    x='Material',
                    y=['Actual RPM', 'Recommended RPM'],
                    barmode='group',
                    title="Actual vs Recommended RPM by Material",
                    labels={'value': 'RPM', 'variable': 'Type'}
                )
                fig.update_layout(
                    height=400,
                    paper_bgcolor="#1f2937",
                    plot_bgcolor="#1f2937",
                    font={'color': "white"}
                )
                st.plotly_chart(fig, use_container_width=True)

# Main function
def main():
    # Initialize session state
    if 'view' not in st.session_state:
        st.session_state.view = "dashboard"
    if 'selected_lathe' not in st.session_state:
        st.session_state.selected_lathe = None
        
    # Navigation
    if st.session_state.view == "dashboard":
        show_dashboard()
    elif st.session_state.view == "lathe_details":
        show_lathe_details()

if __name__ == "__main__":
    main()