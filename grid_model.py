import pandas as pd
import pypsa

# Load the data you created earlier
dorm_data = pd.read_csv("data/dorm_day1.csv", index_col="timestamp", parse_dates=True)

# Create an empty network - this is the container for your whole microgrid
network = pypsa.Network()

# Set the network's timeline to match your 24 hours of data
network.set_snapshots(dorm_data.index)

# Add a "bus" - think of this as the electrical wire everything plugs into
network.add("Bus", "dorm_bus")

# Add the Load - the dorm's electricity demand
network.add(
    "Load",
    "dorm_load",
    bus="dorm_bus",
    p_set=dorm_data["load_kw"]
)

# Add the Generator - solar panels
network.add(
    "Generator",
    "solar_pv",
    bus="dorm_bus",
    p_nom=50,                          # max capacity in kW (matches your peak solar of 50)
    p_max_pu=dorm_data["solar_kw"] / 50,  # hour-by-hour output as a % of max capacity
    marginal_cost=0                    # solar has no fuel cost - it's "free" once built
)

# Add the Grid connection - can supply unlimited power, but costs money per hour
network.add(
    "Generator",
    "grid_import",
    bus="dorm_bus",
    p_nom=200,                         # assume grid can supply up to 200 kW if needed
    marginal_cost=dorm_data["price"]   # this is what makes grid power "expensive" - your price data
)

# Add the Battery (StorageUnit) - the Lithium-ion BESS
network.add(
    "StorageUnit",
    "battery",
    bus="dorm_bus",
    p_nom=50,              # max charge/discharge rate in kW (how fast it can charge/discharge)
    max_hours=2,           # battery can run at full power for 2 hours -> 50kW * 2h = 100 kWh capacity
    efficiency_store=0.9,      # 90% efficient when charging (some energy lost as heat)
    efficiency_dispatch=0.9,   # 90% efficient when discharging
    cyclic_state_of_charge=True  # battery must end the day at the same charge level it started
)

print("Network created successfully!")
print(network)
print("\nSnapshots (timeline):")
print(network.snapshots)
print("\nLoad data attached:")
print(network.loads_t.p_set)

print("\nGenerators added:")
print(network.generators)

print("\nSolar availability (p_max_pu):")
print(network.generators_t.p_max_pu)

print("\nStorage units added:")
print(network.storage_units)

# --- Run the optimizer ---
print("\n" + "="*50)
print("Running optimization...")
print("="*50)

network.optimize(solver_name="highs")

print("\nOptimization complete!")

print("\n--- Battery behavior (optimized) ---")
print(network.storage_units_t.state_of_charge)

print("\n--- Grid power used each hour ---")
print(network.generators_t.p["grid_import"])

print("\n--- Total cost ---")
print(network.objective)

# --- Visualize the results ---
import matplotlib.pyplot as plt

fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

# Top chart: Load vs Solar
axes[0].plot(dorm_data.index, dorm_data["load_kw"], label="Dorm Load (kW)", color="tab:red")
axes[0].plot(dorm_data.index, dorm_data["solar_kw"], label="Solar Generation (kW)", color="tab:orange")
axes[0].set_ylabel("kW")
axes[0].set_title("Load vs Solar Generation")
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# Middle chart: Battery State of Charge
battery_soc = network.storage_units_t.state_of_charge["battery"]
axes[1].plot(dorm_data.index, battery_soc, label="Battery SoC (kWh)", color="tab:green")
axes[1].set_ylabel("kWh")
axes[1].set_title("Battery State of Charge (Optimized)")
axes[1].legend()
axes[1].grid(True, alpha=0.3)

# Bottom chart: Grid Import vs Price
grid_used = network.generators_t.p["grid_import"]
ax2 = axes[2].twinx()
axes[2].plot(dorm_data.index, grid_used, label="Grid Power Used (kW)", color="tab:blue")
ax2.plot(dorm_data.index, dorm_data["price"], label="Price ($/kWh)", color="black", linestyle="--")
axes[2].set_ylabel("kW", color="tab:blue")
ax2.set_ylabel("$/kWh", color="black")
axes[2].set_title("Grid Usage vs Price")
axes[2].legend(loc="upper left")
ax2.legend(loc="upper right")
axes[2].grid(True, alpha=0.3)

plt.xlabel("Hour")
plt.tight_layout()
plt.savefig("dorm_optimization_result.png", dpi=150)
print("\nChart saved to dorm_optimization_result.png")
