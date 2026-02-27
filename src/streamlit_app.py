"""
Streamlit Dashboard for Race Strategy Simulation

Run with: streamlit run src/streamlit_app.py
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.fetch_route_intervals import fetch_route_intervals
from src.gui.services.db_service import get_segment_ids, db_exists
from src.gui.route_map import RouteMap
from src.engine.interval_simulator import SSInterval, join_intervals
from src.engine.nodes import TimeNode

st.set_page_config(
    page_title="Race Strategy Dashboard",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Race Strategy Dashboard")


def get_available_metrics():
    """Get list of plottable metrics from TimeNode."""
    return list(TimeNode.NUMERICAL_METRICS.keys())


def resolve_attr(obj, attr_path):
    """Resolve dot-notation attribute path (e.g., 'speed.kmph')."""
    for attr in attr_path.split('.'):
        obj = getattr(obj, attr)
    return obj


def extract_data_from_nodes(nodes: list, x_field: str, y_field: str):
    """Extract x and y data from a list of TimeNodes."""
    x_data = []
    y_data = []
    for node in nodes:
        try:
            x_val = resolve_attr(node, x_field)
            y_val = resolve_attr(node, y_field)
            if x_val is not None and y_val is not None:
                x_data.append(x_val)
                y_data.append(y_val)
        except (AttributeError, TypeError):
            continue
    return x_data, y_data


def create_plotly_chart(intervals: list[SSInterval], x_field: str, y_field: str, 
                        title: str, show_braking: bool = True):
    """Create an interactive Plotly chart from simulation data."""
    fig = go.Figure()
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    for i, interval in enumerate(intervals):
        if not hasattr(interval, 'time_nodes'):
            continue
            
        color = colors[i % len(colors)]
        
        x_data, y_data = extract_data_from_nodes(interval.time_nodes, x_field, y_field)
        if x_data and y_data:
            fig.add_trace(go.Scatter(
                x=x_data, y=y_data,
                mode='lines',
                name=f'Interval {i+1}',
                line=dict(color=color, width=2),
                hovertemplate=f'{x_field}: %{{x:.2f}}<br>{y_field}: %{{y:.2f}}<extra>Interval {i+1}</extra>'
            ))
        
        if show_braking and hasattr(interval, 'brakingNodes'):
            x_brake, y_brake = extract_data_from_nodes(interval.brakingNodes, x_field, y_field)
            if x_brake and y_brake:
                fig.add_trace(go.Scatter(
                    x=x_brake, y=y_brake,
                    mode='lines',
                    name=f'Braking {i+1}',
                    line=dict(color=color, width=1, dash='dash'),
                    hovertemplate=f'{x_field}: %{{x:.2f}}<br>{y_field}: %{{y:.2f}}<extra>Braking {i+1}</extra>'
                ))
    
    x_label = TimeNode.NUMERICAL_METRICS.get(x_field, x_field)
    y_label = TimeNode.NUMERICAL_METRICS.get(y_field, y_field)
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        hovermode='closest',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=60, b=60)
    )
    
    return fig


def create_master_chart(master_interval: SSInterval, x_field: str, y_fields: list[str], 
                        title: str, show_braking: bool = False):
    """Create a chart for the master (joined) interval with multiple y-fields."""
    fig = go.Figure()
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    if hasattr(master_interval, 'time_nodes'):
        for j, y_field in enumerate(y_fields):
            x_data, y_data = extract_data_from_nodes(master_interval.time_nodes, x_field, y_field)
            if x_data and y_data:
                y_label = TimeNode.NUMERICAL_METRICS.get(y_field, y_field)
                fig.add_trace(go.Scatter(
                    x=x_data, y=y_data,
                    mode='lines',
                    name=y_label,
                    line=dict(color=colors[j % len(colors)], width=2),
                    hovertemplate=f'{x_field}: %{{x:.2f}}<br>{y_field}: %{{y:.2f}}<extra>{y_label}</extra>'
                ))
        
        if show_braking and hasattr(master_interval, 'brakingNodes'):
            for j, y_field in enumerate(y_fields):
                x_brake, y_brake = extract_data_from_nodes(master_interval.brakingNodes, x_field, y_field)
                if x_brake and y_brake:
                    fig.add_trace(go.Scatter(
                        x=x_brake, y=y_brake,
                        mode='lines',
                        name=f'Braking - {y_field}',
                        line=dict(color=colors[j % len(colors)], width=1, dash='dash'),
                    ))
    
    x_label = TimeNode.NUMERICAL_METRICS.get(x_field, x_field)
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title="Value",
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=60, b=60)
    )
    
    return fig


# Sidebar controls
with st.sidebar:
    st.header("Configuration")
    
    # Database selection
    db_files = [f for f in os.listdir('.') if f.endswith('.sqlite')]
    if not db_files:
        st.error("No SQLite database files found in current directory")
        st.stop()
    
    db_path = st.selectbox("Database", db_files, index=0 if 'ASC_2024.sqlite' not in db_files else db_files.index('ASC_2024.sqlite'))
    
    # Get available placemarks
    try:
        placemarks = get_segment_ids(db_path)
    except Exception as e:
        st.error(f"Error loading database: {e}")
        st.stop()
    
    if not placemarks:
        st.warning("No placemarks found in database")
        st.stop()
    
    placemark = st.selectbox("Placemark", placemarks)
    
    st.divider()
    
    # Simulation settings
    st.subheader("Simulation Settings")
    split_at_stops = st.checkbox("Split at stops", value=True, 
                                  help="Split route into intervals at stop signs")
    time_step = st.slider("Time step (s)", 0.1, 2.0, 0.5, 0.1,
                          help="Simulation time step in seconds")
    velocity_step = st.slider("Velocity step (m/s)", 0.1, 2.0, 1.0, 0.1,
                              help="Velocity step for adaptive timestep")
    
    st.divider()
    
    # Chart settings
    st.subheader("Chart Settings")
    metrics = get_available_metrics()
    
    col1, col2 = st.columns(2)
    with col1:
        x_field = st.selectbox("X-axis", metrics, index=metrics.index('dist') if 'dist' in metrics else 0)
    with col2:
        y_field = st.selectbox("Y-axis", metrics, index=metrics.index('speed.kmph') if 'speed.kmph' in metrics else 0)
    
    show_braking = st.checkbox("Show braking curves", value=True)
    
    st.divider()
    
    # Run simulation button
    run_simulation = st.button("Run Simulation", type="primary", use_container_width=True)


# Initialize session state
if 'intervals' not in st.session_state:
    st.session_state.intervals = None
if 'master_interval' not in st.session_state:
    st.session_state.master_interval = None
if 'route_map' not in st.session_state:
    st.session_state.route_map = None


# Run simulation when button is clicked
if run_simulation:
    with st.spinner(f"Running simulation for {placemark}..."):
        try:
            # Fetch route intervals
            intervals = fetch_route_intervals(
                placemark, 
                split_at_stops=split_at_stops, 
                db_path=db_path
            )
            
            # Ensure intervals is a list
            if isinstance(intervals, SSInterval):
                intervals = [intervals]
            
            # Run simulation for each interval
            from src.engine.kinematics import Speed
            progress_bar = st.progress(0)
            for i, interval in enumerate(intervals):
                interval.simulate_interval(TIME_STEP=time_step, VELOCITY_STEP=Speed(mps=velocity_step))
                progress_bar.progress((i + 1) / len(intervals))
            
            # Join intervals into master
            master_interval = join_intervals(intervals)
            
            # Generate map
            route_map = RouteMap()
            route_map.generate_simulation_map(
                placemark, 
                time_step=time_step,
                velocity_step=velocity_step,
                hover=True, 
                db_path=db_path, 
                split_at_stops=split_at_stops
            )
            
            # Store in session state
            st.session_state.intervals = intervals
            st.session_state.master_interval = master_interval
            st.session_state.route_map = route_map
            
            st.success(f"Simulation complete! {len(intervals)} intervals processed.")
            st.rerun()
            
        except Exception as e:
            st.error(f"Simulation failed: {e}")
            import traceback
            st.code(traceback.format_exc())


# Display results
if st.session_state.intervals is not None:
    intervals = st.session_state.intervals
    master_interval = st.session_state.master_interval
    route_map = st.session_state.route_map
    
    # Create tabs for different views
    tab_map, tab_master, tab_intervals = st.tabs(["Map", "Master View", "Individual Intervals"])
    
    with tab_map:
        st.subheader("Route Map")
        if route_map is not None:
            try:
                from streamlit_folium import st_folium
                st_folium(route_map.folium_map, width=None, height=500, use_container_width=True)
            except ImportError:
                st.warning("Install streamlit-folium for map display: pip install streamlit-folium")
                # Fallback: save and display as iframe
                map_path = "temp_map.html"
                route_map.save_map(map_path.replace('.html', ''))
                st.components.v1.html(open(f"{map_path}").read(), height=500)
    
    with tab_master:
        st.subheader("Master Route Analysis")
        
        if master_interval is not None:
            # Summary stats
            col1, col2, col3, col4 = st.columns(4)
            
            if hasattr(master_interval, 'time_nodes') and master_interval.time_nodes:
                last_node = master_interval.time_nodes[-1]
                with col1:
                    st.metric("Total Distance", f"{last_node.dist/1000:.2f} km")
                with col2:
                    st.metric("Total Time", f"{last_node.time/60:.1f} min")
                with col3:
                    max_speed = max(n.speed.kmph for n in master_interval.time_nodes)
                    st.metric("Max Speed", f"{max_speed:.1f} km/h")
                with col4:
                    st.metric("Intervals", len(intervals))
            
            # Master chart
            fig = create_master_chart(
                master_interval,
                x_field,
                [y_field, 'segment.v_eff.kmph'] if y_field == 'speed.kmph' else [y_field],
                f"Master Route: {TimeNode.NUMERICAL_METRICS.get(y_field, y_field)} vs {TimeNode.NUMERICAL_METRICS.get(x_field, x_field)}",
                show_braking=show_braking
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Second chart with different metrics
            col1, col2 = st.columns(2)
            with col1:
                x2 = st.selectbox("X-axis (Chart 2)", metrics, index=metrics.index('time') if 'time' in metrics else 0, key='x2')
            with col2:
                y2 = st.selectbox("Y-axis (Chart 2)", metrics, index=metrics.index('soc') if 'soc' in metrics else 0, key='y2')
            
            fig2 = create_master_chart(
                master_interval,
                x2,
                [y2],
                f"Master Route: {TimeNode.NUMERICAL_METRICS.get(y2, y2)} vs {TimeNode.NUMERICAL_METRICS.get(x2, x2)}",
                show_braking=False
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    with tab_intervals:
        st.subheader("Individual Interval Analysis")
        
        # Interval selector
        interval_idx = st.slider(
            "Select Interval", 
            1, len(intervals), 1,
            help=f"Browse through {len(intervals)} intervals"
        ) - 1
        
        selected_interval = intervals[interval_idx]
        
        # Interval info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Interval", f"{interval_idx + 1} of {len(intervals)}")
        with col2:
            if hasattr(selected_interval, 'time_nodes') and selected_interval.time_nodes:
                dist = selected_interval.time_nodes[-1].dist - selected_interval.time_nodes[0].dist
                st.metric("Distance", f"{dist/1000:.2f} km")
        with col3:
            if hasattr(selected_interval, 'time_nodes') and selected_interval.time_nodes:
                time_taken = selected_interval.time_nodes[-1].time - selected_interval.time_nodes[0].time
                st.metric("Duration", f"{time_taken:.1f} s")
        
        # Single interval chart
        fig = create_plotly_chart(
            [selected_interval],
            x_field,
            y_field,
            f"Interval {interval_idx + 1}: {TimeNode.NUMERICAL_METRICS.get(y_field, y_field)} vs {TimeNode.NUMERICAL_METRICS.get(x_field, x_field)}",
            show_braking=show_braking
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # All intervals comparison
        st.subheader("All Intervals Comparison")
        
        # Limit to first 20 intervals for performance
        display_intervals = intervals[:20] if len(intervals) > 20 else intervals
        if len(intervals) > 20:
            st.info(f"Showing first 20 of {len(intervals)} intervals for performance")
        
        fig_all = create_plotly_chart(
            display_intervals,
            x_field,
            y_field,
            f"All Intervals: {TimeNode.NUMERICAL_METRICS.get(y_field, y_field)} vs {TimeNode.NUMERICAL_METRICS.get(x_field, x_field)}",
            show_braking=False
        )
        st.plotly_chart(fig_all, use_container_width=True)

else:
    st.info("👈 Configure settings in the sidebar and click 'Run Simulation' to begin")
    
    # Debug info
    st.caption(f"Session state: intervals={st.session_state.intervals is not None}, master={st.session_state.master_interval is not None}, map={st.session_state.route_map is not None}")
    
    # Show a preview of available data
    st.subheader("Available Data")
    try:
        placemarks = get_segment_ids(db_path)
        st.write(f"Found **{len(placemarks)}** placemarks in `{db_path}`:")
        for pm in placemarks[:10]:
            st.write(f"  - {pm}")
        if len(placemarks) > 10:
            st.write(f"  ... and {len(placemarks) - 10} more")
    except Exception as e:
        st.error(f"Could not load placemarks: {e}")
