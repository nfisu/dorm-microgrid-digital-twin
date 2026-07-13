from fastapi import FastAPI
import pandas as pd
import pypsa
from pydantic import BaseModel

app = FastAPI()

class BatteryCommand(BaseModel):
    action: str      # "charge" or "discharge"
    amount_kw: float # how much power to charge/discharge

# Load the dorm's data once when the server starts
dorm_data = pd.read_csv("data/dorm_day1.csv", index_col="timestamp", parse_dates=True)

# Rebuild and re-optimize the same network from grid_model.py
network = pypsa.Network()
network.set_snapshots(dorm_data.index)
network.add("Bus", "dorm_bus")
network.add("Load", "dorm_load", bus="dorm_bus", p_set=dorm_data["load_kw"])
network.add("Generator", "solar_pv", bus="dorm_bus", p_nom=50,
            p_max_pu=dorm_data["solar_kw"] / 50, marginal_cost=0)
network.add("Generator", "grid_import", bus="dorm_bus", p_nom=200,
            marginal_cost=dorm_data["price"])
network.add("StorageUnit", "battery", bus="dorm_bus", p_nom=50, max_hours=2,
            efficiency_store=0.9, efficiency_dispatch=0.9, cyclic_state_of_charge=True)

network.optimize(solver_name="highs")

# Track which hour we're "currently" at - starts at hour 0
current_hour_index = 0

# Manual override state
manual_override_active = False
manual_soc = None

@app.get("/")
def read_root():
    return {"message": "Dorm microgrid digital twin API is running"}

@app.get("/telemetry/current-state")
def get_current_state():
    global current_hour_index
    timestamp = dorm_data.index[current_hour_index]

    return {
        "timestamp": str(timestamp),
        "hour_index": current_hour_index,
        "load_kw": float(dorm_data.iloc[current_hour_index]["load_kw"]),
        "solar_kw": float(dorm_data.iloc[current_hour_index]["solar_kw"]),
        "price": float(dorm_data.iloc[current_hour_index]["price"]),
        "battery_soc_kwh": float(manual_soc) if manual_override_active else float(network.storage_units_t.state_of_charge["battery"].iloc[current_hour_index]),
        "grid_import_kw": float(network.generators_t.p["grid_import"].iloc[current_hour_index])
    }

@app.post("/telemetry/advance-hour")
def advance_hour():
    global current_hour_index
    if current_hour_index < len(dorm_data) - 1:
        current_hour_index += 1
    else:
        current_hour_index = 0
    return {"message": f"Advanced to hour {current_hour_index}"}

@app.post("/control/dispatch-battery")
def dispatch_battery(command: BatteryCommand):
    global manual_override_active, manual_soc

    if manual_soc is None:
        manual_soc = network.storage_units_t.state_of_charge["battery"].iloc[current_hour_index]

    if command.action == "charge":
        manual_soc = min(100, manual_soc + command.amount_kw)
    elif command.action == "discharge":
        manual_soc = max(0, manual_soc - command.amount_kw)
    else:
        return {"error": "action must be 'charge' or 'discharge'"}

    manual_override_active = True

    return {
        "message": f"Manual {command.action} of {command.amount_kw} kW applied",
        "battery_soc_kwh": manual_soc
    }

@app.get("/telemetry/full-day")
def get_full_day():
    return {
        "timestamps": [str(t) for t in dorm_data.index],
        "load_kw": dorm_data["load_kw"].tolist(),
        "solar_kw": dorm_data["solar_kw"].tolist(),
        "price": dorm_data["price"].tolist(),
        "battery_soc_kwh": network.storage_units_t.state_of_charge["battery"].tolist(),
        "grid_import_kw": network.generators_t.p["grid_import"].tolist()
    }

@app.get("/telemetry/summary")
def get_summary():
    return {
        "total_cost_optimized": float(network.objective),
        "battery_capacity_kwh": 100,
        "solar_capacity_kw": 50
    }
