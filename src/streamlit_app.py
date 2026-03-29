"""
Streamlit Dashboard for Race Strategy Simulation

Run with: streamlit run src/streamlit_app.py
"""

import streamlit as st
from streamlit_folium import st_folium
import os
from pathlib import Path
import sys
import copy

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gui.streamlit_stuff.graph import create_plotly_chart, get_available_metrics, create_master_chart, get_metric_name
from src.gui.streamlit_stuff.simulator import SimulationConfig, simulate
from src.gui.streamlit_stuff.database import get_placemarks
from src.gui.services.kml_service import upload_kml

st.set_page_config(page_title="Race Strategy Dashboard", page_icon="🏎️", layout="wide", initial_sidebar_state="expanded")

st.title("Race Strategy Dashboard")


def init_session():
    defaults = {
        "intervals": None,
        "master_interval": None,
        "route_map": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def run():
    # Sidebar controls
    with st.sidebar:
        st.header("Configuration")

        # KML upload
        kml_file = st.file_uploader("KML File", type=["kml"], key="kml_upload")
        if kml_file is not None:
            Path("tmp").mkdir(exist_ok=True)
            kml_path = Path("tmp", kml_file.name)
            with open(kml_path, "wb") as f:
                f.write(kml_file.getbuffer())

            if st.session_state.get("last_kml") != kml_file.name:
                with st.spinner("Processing KML file..."):
                    try:
                        upload_kml(kml_path.as_posix(), db_path=Path(kml_path).with_suffix(".sqlite").as_posix())
                        st.session_state.last_kml = kml_file.name
                        st.success("KML loaded")
                    except Exception as e:
                        st.error(f"KML upload failed: {e}")
                        st.stop()
                        raise e

        # SQLite upload
        sqlite_file = st.file_uploader("SQLite Database", type=["sqlite"], key="sqlite_upload")
        Path("tmp").mkdir(exist_ok=True)
        if sqlite_file is not None:
            upload_db_path = Path("tmp", sqlite_file.name)
            with open(upload_db_path, "wb") as f:
                f.write(sqlite_file.getbuffer())

        # Database selection
        db_files = [f"tmp/{f.name}" for f in Path("tmp").iterdir() if f.suffix == ".sqlite"]
        if not db_files:
            st.warning("Please upload a SQLite database file")
            st.stop()
        db_path = st.selectbox("Database", db_files, index=0 if "ASC_2024.sqlite" not in db_files else db_files.index("ASC_2024.sqlite"))
        db_path = Path(db_path)

        # Get available placemarks
        try:
            placemarks = get_placemarks(db_path.as_posix())
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
        split_at_stops = st.checkbox("Split at stops", value=True, help="Split route into intervals at stop signs")
        time_step = st.slider("Time step (s)", 0.1, 2.0, 0.5, 0.1, help="Simulation time step in seconds")
        velocity_step = st.slider("Velocity step (m/s)", 0.1, 2.0, 1.0, 0.1, help="Velocity step for adaptive timestep")

        st.divider()

        # Chart settings
        st.subheader("Chart Settings")
        metrics = get_available_metrics()

        col1, col2 = st.columns(2)
        with col1:
            x_field = st.selectbox("X-axis", metrics, index=metrics.index("dist") if "dist" in metrics else 0)
        with col2:
            y_field = st.selectbox("Y-axis", metrics, index=metrics.index("speed.kmph") if "speed.kmph" in metrics else 0)

        show_braking = st.checkbox("Show braking curves", value=True)

        st.divider()

        # Run simulation button
        run_simulation = st.button("Run Simulation", type="primary", width="stretch")

    # Initialize session state
    init_session()

    # Run simulation when button is clicked
    if run_simulation:
        with st.spinner(f"Running simulation for {placemark}..."):
            try:
                config = SimulationConfig(placemark=placemark, db_path=db_path, time_step=time_step, velocity_step=velocity_step, split_at_stops=split_at_stops, hover=True)
                import sqlite3

                conn = sqlite3.connect(db_path.as_posix())
                count = conn.execute("SELECT COUNT(*) FROM route_data WHERE placemark_name = ?", (placemark,)).fetchone()[0]
                conn.close()
                st.write(f"DB path: {db_path.as_posix()}")
                st.write(f"Rows for '{placemark}': {count}")
                result = simulate(config)

                st.session_state.intervals = result.intervals
                st.session_state.master_interval = result.master_interval
                st.session_state.route_map = result.route_map

                st.success(f"Simulation complete! {len(result.intervals)} intervals processed.")
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
                st_folium(copy.deepcopy(route_map.folium_map), height=500, use_container_width=True, returned_objects=[])

        with tab_master:
            st.subheader("Master Route Analysis")

            if master_interval is not None:
                # Summary stats
                col1, col2, col3, col4 = st.columns(4)

                if hasattr(master_interval, "time_nodes") and master_interval.time_nodes:
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
                    [y_field, "segment.v_eff.kmph"] if y_field == "speed.kmph" else [y_field],
                    f"Master Route: {get_metric_name(y_field)} vs {get_metric_name(x_field)}",
                    show_braking=show_braking,
                )
                st.plotly_chart(fig, width="stretch")

                # Second chart with different metrics
                col1, col2 = st.columns(2)
                with col1:
                    x2 = st.selectbox("X-axis (Chart 2)", metrics, index=metrics.index("time") if "time" in metrics else 0, key="x2")
                with col2:
                    y2 = st.selectbox("Y-axis (Chart 2)", metrics, index=metrics.index("soc") if "soc" in metrics else 0, key="y2")

                fig2 = create_master_chart(master_interval, x2, [y2], f"Master Route: {get_metric_name( y2)} vs {get_metric_name( x2)}", show_braking=False)
                st.plotly_chart(fig2, width="stretch")

        with tab_intervals:
            st.subheader("Individual Interval Analysis")

            # Interval selector
            interval_idx = st.slider("Select Interval", 0, len(intervals), 1, help=f"Browse through {len(intervals)} intervals") - 1

            selected_interval = intervals[interval_idx]

            # Interval info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Interval", f"{interval_idx + 1} of {len(intervals)}")
            with col2:
                if hasattr(selected_interval, "time_nodes") and selected_interval.time_nodes:
                    dist = selected_interval.time_nodes[-1].dist - selected_interval.time_nodes[0].dist
                    st.metric("Distance", f"{dist/1000:.2f} km")
            with col3:
                if hasattr(selected_interval, "time_nodes") and selected_interval.time_nodes:
                    time_taken = selected_interval.time_nodes[-1].time - selected_interval.time_nodes[0].time
                    st.metric("Duration", f"{time_taken:.1f} s")

            # Single interval chart
            fig = create_plotly_chart(
                [selected_interval],
                x_field,
                y_field,
                f"Interval {interval_idx + 1}: {get_metric_name(y_field)} vs {get_metric_name(x_field)}",
                show_braking=show_braking,
            )
            st.plotly_chart(fig, width="stretch")

            # All intervals comparison
            st.subheader("All Intervals Comparison")

            # Limit to first 20 intervals for performance
            display_intervals = intervals[:20] if len(intervals) > 20 else intervals
            if len(intervals) > 20:
                st.info(f"Showing first 20 of {len(intervals)} intervals for performance")

            fig_all = create_plotly_chart(display_intervals, x_field, y_field, f"All Intervals: {get_metric_name(y_field)} vs {get_metric_name(x_field)}", show_braking=False)
            st.plotly_chart(fig_all, width="stretch")

    else:
        st.info("👈 Configure settings in the sidebar and click 'Run Simulation' to begin")

        # Debug info
        st.caption(f"Session state: intervals={st.session_state.intervals is not None}, master={st.session_state.master_interval is not None}, map={st.session_state.route_map is not None}")

        # Show a preview of available data
        st.subheader("Available Data")
        try:
            placemarks = get_placemarks(db_path)
            st.write(f"Found **{len(placemarks)}** placemarks in `{db_path}`:")
            for pm in placemarks[:10]:
                st.write(f"  - {pm}")
            if len(placemarks) > 10:
                st.write(f"  ... and {len(placemarks) - 10} more")
        except Exception as e:
            st.error(f"Could not load placemarks: {e}")


if __name__ == "__main__":
    run()
