# import pandas as pd
# import matplotlib.pyplot as plt

# # 1. Leer el archivo JSONL
# df = pd.read_json("telemetry_log.json", lines=True)

# # 2. Separar los datos por tipo de evento
# df_vuelo = df[df["event"] == "flight_progress"]
# df_satelites = df[df["event"] == "satellite_eval"]

# # 3. Graficar la elevación del satélite X a lo largo del tiempo
# sat_x = df_satelites[df_satelites["sat_id"] == "a4c14728"]
# plt.plot(sat_x["timestamp"], sat_x["elevation_deg"])
# plt.title("Elevación de Satélite a4c14728 durante el pase")
# plt.show()

import pandas as pd
import matplotlib.pyplot as plt

# 1. Leer el archivo general
df = pd.read_json("telemetry_log.json", lines=True)

# 2. Filtrar SOLO los eventos de red 5G
df_5g = df[df["event"] == "5g_doppler_loss"]

# Convertir el timestamp a formato de fecha y hora para el eje X
df_5g['timestamp'] = pd.to_datetime(df_5g['timestamp'])

# 3. Dibujar la gráfica
plt.figure(figsize=(10, 5))

# Eje X: Tiempo | Eje Y: Porcentaje de Pérdida
plt.plot(df_5g["timestamp"], df_5g["loss_pct"], color='red', linewidth=2, label="Pérdida de Paquetes (%)")

# (Opcional) Graficar también el Doppler Residual en un eje secundario
ax2 = plt.twinx()
ax2.plot(df_5g["timestamp"], df_5g["residual_doppler_hz"], color='blue', linestyle='--', alpha=0.5, label="Doppler Residual (Hz)")

plt.title("Impacto del Efecto Doppler en Enlace 5G-NTN")
plt.xlabel("Tiempo de Simulación")
plt.ylabel("Pérdida de Paquetes (%)")
ax2.set_ylabel("Hertz (Hz)")

# Mostrar la leyenda
plt.legend(loc="upper left")
ax2.legend(loc="upper right")

plt.grid(True)
plt.tight_layout()
plt.savefig("5g_doppler_loss.png")