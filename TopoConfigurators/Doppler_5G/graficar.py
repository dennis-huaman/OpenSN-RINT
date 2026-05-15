import pandas as pd
import matplotlib.pyplot as plt

# 1. Leer el archivo JSONL
df = pd.read_json("telemetry_log.json", lines=True)

# 2. Separar los datos por tipo de evento
df_vuelo = df[df["event"] == "flight_progress"]
df_satelites = df[df["event"] == "satellite_eval"]

# 3. Graficar la elevación del satélite X a lo largo del tiempo
sat_x = df_satelites[df_satelites["sat_id"] == "a4c14728"]
plt.plot(sat_x["timestamp"], sat_x["elevation_deg"])
plt.title("Elevación de Satélite a4c14728 durante el pase")
plt.show()