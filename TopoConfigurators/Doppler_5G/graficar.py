import os
import matplotlib.pyplot as plt
import pandas as pd

# 1. Leer el archivo JSONL
df = pd.read_json("telemetry_log.json", lines=True)

# 2. Separar los eventos necesarios
# Dataframe con todas las evaluaciones geométricas
df_evals = df[df["event"] == "satellite_eval"]

# Dataframe con las decisiones de handover (satélite activo en cada instante)
df_handovers = df[df["event"] == "handover"][
    ["timestamp", "gs_id", "selected_sat_id"]
]

# 3. Cruzar los datos para obtener SOLO el satélite conectado por tiempo y GS
df_conectados = pd.merge(
    df_evals,
    df_handovers,
    left_on=["timestamp", "gs_id", "sat_id"],
    right_on=["timestamp", "gs_id", "selected_sat_id"],
)

# Asegurar que la carpeta 'figs' exista
os.makedirs("figs", exist_ok=True)

# 4. Iterar automáticamente sobre cada Ground Station (GS / TU) presente en los datos
gs_unicas = df_conectados["gs_id"].unique()

print(f"Se detectaron {len(gs_unicas)} estaciones terrenas (GS) únicas.")
print("Generando perfiles de conexión activa...")

for gs_id in gs_unicas:
    # Filtrar datos de la GS actual y ordenar cronológicamente
    gs_data = df_conectados[df_conectados["gs_id"] == gs_id].sort_values(
        "timestamp"
    )

    if gs_data.empty:
        continue

    # --- GRÁFICA 1: VELOCIDAD RELATIVA (Perfil para Estudio Doppler) ---
    plt.figure(figsize=(10, 5))

    # Línea continua de la velocidad relativa de la conexión activa
    plt.plot(
        gs_data["timestamp"],
        gs_data["rel_vel_m_s"],
        color="black",
        linestyle="--",
        alpha=0.5,
    )

    # Colorear los puntos de forma distinta según el satélite conectado (identifica Handovers)
    for sat_id in gs_data["sat_id"].unique():
        sat_segment = gs_data[gs_data["sat_id"] == sat_id]
        plt.scatter(
            sat_segment["timestamp"],
            sat_segment["rel_vel_m_s"],
            label=f"Sat: {sat_id}",
            s=25,
        )

    plt.title(f"Perfil Doppler (Velocidad Relativa) - Conexión Activa GS {gs_id}")
    plt.xlabel("Tiempo")
    plt.ylabel("Velocidad Relativa (m/s)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.xticks(rotation=30)
    plt.legend(title="Satélite Activo", loc="upper right")

    plt.savefig(f"figs/gs_{gs_id}_doppler_activo.png", bbox_inches="tight")
    plt.close()

    # --- GRÁFICA 2: ELEVACIÓN DEL SATÉLITE CONECTADO ---
    plt.figure(figsize=(10, 5))

    plt.plot(
        gs_data["timestamp"],
        gs_data["elevation_deg"],
        color="black",
        linestyle="--",
        alpha=0.5,
    )

    for sat_id in gs_data["sat_id"].unique():
        sat_segment = gs_data[gs_data["sat_id"] == sat_id]
        plt.scatter(
            sat_segment["timestamp"],
            sat_segment["elevation_deg"],
            label=f"Sat: {sat_id}",
            s=25,
        )

    plt.title(f"Trayectoria de Elevación - Conexión Activa GS {gs_id}")
    plt.xlabel("Tiempo")
    plt.ylabel("Elevación (grados)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.xticks(rotation=30)
    plt.legend(title="Satélite Activo", loc="lower right")

    plt.savefig(f"figs/gs_{gs_id}_elevacion_activa.png", bbox_inches="tight")
    plt.close()

print("Proceso completado. Gráficas guardadas en la carpeta 'figs/'.")