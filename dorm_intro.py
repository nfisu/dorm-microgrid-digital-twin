import pandas as pd

# 24 fake hours for one day, starting at midnight
hours = pd.date_range(start="2026-01-01 00:00", periods=24, freq="h")

# Electricity load (same as before)
load_kw = [
    30, 28, 27, 27, 28, 35,   # 12am - 5am
    55, 70, 60, 45, 40, 38,   # 6am - 11am
    36, 38, 40, 42, 45, 55,   # 12pm - 5pm
    75, 85, 80, 65, 50, 35    # 6pm - 11pm
]

# Solar generation: zero at night, peaks around noon
solar_kw = [
    0, 0, 0, 0, 0, 0,         # 12am - 5am (dark)
    2, 8, 18, 28, 38, 45,     # 6am - 11am (sun rising)
    50, 48, 42, 33, 22, 10,   # 12pm - 5pm (peak then falling)
    2, 0, 0, 0, 0, 0          # 6pm - 11pm (dark again)
]

# Electricity price ($/kWh): cheaper at night, expensive during evening peak demand
price = [
    0.08, 0.08, 0.08, 0.08, 0.08, 0.08,   # 12am - 5am (off-peak)
    0.10, 0.12, 0.12, 0.10, 0.10, 0.10,   # 6am - 11am (mid)
    0.10, 0.10, 0.10, 0.10, 0.12, 0.15,   # 12pm - 5pm (mid, rising)
    0.20, 0.22, 0.20, 0.15, 0.10, 0.08    # 6pm - 11pm (peak, then falling)
]

# Combine all three into one table
dorm_data = pd.DataFrame({
    "timestamp": hours,
    "load_kw": load_kw,
    "solar_kw": solar_kw,
    "price": price
})

print(dorm_data)

# Save it as a real CSV file so we can reuse it later
dorm_data.to_csv("data/dorm_day1.csv", index=False)
print("\nSaved to data/dorm_day1.csv")

# --- Simple manual battery simulation ---

battery_capacity = 100   # max energy the battery can hold, in kWh
battery_soc = 50         # starting charge level (State of Charge), in kWh - starts half full
battery_log = []         # we'll record what the battery does each hour

for i in range(len(dorm_data)):
    hour = dorm_data.loc[i, "timestamp"]
    load = dorm_data.loc[i, "load_kw"]
    solar = dorm_data.loc[i, "solar_kw"]
    price = dorm_data.loc[i, "price"]

    net = solar - load  # positive = extra solar, negative = dorm needs more than solar gives

    if net > 0 and battery_soc < battery_capacity:
        # extra solar available -> charge the battery
        charge_amount = min(net, battery_capacity - battery_soc)
        battery_soc += charge_amount
        action = f"CHARGE +{charge_amount:.0f} kWh"
    elif price >= 0.20 and battery_soc > 0:
        # expensive hour -> discharge the battery to help cover load
        discharge_amount = min(20, battery_soc)  # discharge up to 20 kWh at a time
        battery_soc -= discharge_amount
        action = f"DISCHARGE -{discharge_amount:.0f} kWh"
    else:
        action = "idle"

    battery_log.append({
        "timestamp": hour,
        "battery_soc": battery_soc,
        "action": action
    })

battery_df = pd.DataFrame(battery_log)
print("\n--- Battery behavior ---")
print(battery_df)

# --- Calculate total cost of the hand-written rule-based strategy ---

total_cost_manual = 0
grid_log = []

battery_soc = 50  # reset to starting point to replay the same logic
for i in range(len(dorm_data)):
    load = dorm_data.loc[i, "load_kw"]
    solar = dorm_data.loc[i, "solar_kw"]
    price = dorm_data.loc[i, "price"]

    net = solar - load

    if net > 0 and battery_soc < battery_capacity:
        charge_amount = min(net, battery_capacity - battery_soc)
        battery_soc += charge_amount
        battery_output = 0  # charging doesn't reduce grid draw, it just stores surplus
    elif price >= 0.20 and battery_soc > 0:
        discharge_amount = min(20, battery_soc)
        battery_soc -= discharge_amount
        battery_output = discharge_amount
    else:
        battery_output = 0

    grid_power = max(0, load - solar - battery_output)
    hour_cost = grid_power * price
    total_cost_manual += hour_cost

    grid_log.append({"grid_kw": grid_power, "cost": hour_cost})

print(f"\n--- Hand-written rule-based strategy ---")
print(f"Total cost: ${total_cost_manual:.2f}")
