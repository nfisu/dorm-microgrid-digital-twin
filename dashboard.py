import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Dorm Microgrid Digital Twin", layout="wide")
st.title("🏢 Dorm Microgrid Digital Twin")

API_URL = "http://127.0.0.1:8000"

# Fetch current state from the API
response = requests.get(f"{API_URL}/telemetry/current-state")
data = response.json()

# --- KPI Cards ---
summary = requests.get(f"{API_URL}/telemetry/summary").json()

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Current Hour", f"{data['hour_index']}:00")

with col2:
    st.metric("Battery SoC", f"{data['battery_soc_kwh']:.1f} kWh")

with col3:
    st.metric("Grid Import", f"{data['grid_import_kw']:.1f} kW")

with col4:
    st.metric("Electricity Price", f"${data['price']:.2f}/kWh")

with col5:
    st.metric("Optimized Daily Cost", f"${summary['total_cost_optimized']:.2f}")

st.divider()

# --- Fetch full day data for charts ---
full_day = requests.get(f"{API_URL}/telemetry/full-day").json()

chart_df = pd.DataFrame({
    "timestamp": pd.to_datetime(full_day["timestamps"]),
    "Load (kW)": full_day["load_kw"],
    "Solar (kW)": full_day["solar_kw"],
    "Battery SoC (kWh)": full_day["battery_soc_kwh"],
    "Grid Import (kW)": full_day["grid_import_kw"],
    "Price ($/kWh)": full_day["price"]
}).set_index("timestamp")

st.subheader("📈 Load vs Solar Generation")
st.line_chart(chart_df[["Load (kW)", "Solar (kW)"]])

st.subheader("🔋 Battery State of Charge")
st.line_chart(chart_df[["Battery SoC (kWh)"]])

st.subheader("⚡ Grid Usage vs Price")
col_chart1, col_chart2 = st.columns(2)
with col_chart1:
    st.line_chart(chart_df[["Grid Import (kW)"]])
with col_chart2:
    st.line_chart(chart_df[["Price ($/kWh)"]])

# --- Controls ---
st.subheader("Simulation Controls")

col_a, col_b = st.columns(2)

with col_a:
    if st.button("⏭️ Advance 1 Hour"):
        requests.post(f"{API_URL}/telemetry/advance-hour")
        st.rerun()

with col_b:
    with st.form("battery_override"):
        st.write("Manual Battery Override")
        action = st.selectbox("Action", ["charge", "discharge"])
        amount = st.number_input("Amount (kW)", min_value=0.0, max_value=50.0, value=10.0)
        submitted = st.form_submit_button("Apply Override")
        if submitted:
            requests.post(f"{API_URL}/control/dispatch-battery", json={"action": action, "amount_kw": amount})
            st.rerun()
