import pandas as pd
import matplotlib.pyplot as plt

# 1. Cargar el archivo JSONL
archivo_json = "telemetry_log.json"
df = pd.read_json(archivo_json, lines=True)

# Convertir el timestamp a formato de fecha
df['timestamp'] = pd.to_datetime(df['timestamp'])

# 2. Obtener todas las Ground Stations (GS) únicas
gs_unicas = df['gs_id'].dropna().unique()
print(f"Se encontraron {len(gs_unicas)} Ground Stations: {gs_unicas}")

# 3. Iterar y graficar independientemente para cada GS
for gs in gs_unicas:
    print(f"\nGenerando gráficas para GS: {gs}...")
    
    # Filtrar solo las filas que pertenecen a esta GS
    df_gs = df[df['gs_id'] == gs]
    
    # Separar los datos por el tipo de evento
    df_satelites = df_gs[df_gs['event'] == 'satellite_eval']
    df_vuelo = df_gs[df_gs['event'] == 'flight_progress']
    df_loss = df_gs[df_gs['event'] == '5g_doppler_loss'] # <-- NUEVO: Captura la pérdida
    
    # =========================================================
    # GRÁFICA 1: Elevación, Velocidad Relativa y Pérdida 5G
    # =========================================================
    if not df_satelites.empty:
        # AHORA CREAMOS 3 SUBPLOTS
        fig, axs = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
        fig.suptitle(f"Análisis Físico y de Red 5G-NTN - GS: {gs}", fontsize=16, fontweight='bold')
        
        # Agrupar los datos del escáner (trajectory.py)
        for sat_id, sat_data in df_satelites.groupby('sat_id'):
            axs[0].plot(sat_data['timestamp'], sat_data['elevation_deg'], marker='.', label=f"Sat {sat_id}")
            axs[1].plot(sat_data['timestamp'], sat_data['rel_vel_m_s'], marker='.', label=f"Sat {sat_id}")
            
        # Agrupar los datos de la red activa (main.py)
        if not df_loss.empty:
            for sat_id, loss_data in df_loss.groupby('sat_id'):
                axs[2].plot(loss_data['timestamp'], loss_data['loss_pct'], marker='s', linestyle='-', linewidth=2, label=f"Enlace Activo ({sat_id})")
            
        # Configuraciones Subplot 0 (Elevación)
        axs[0].set_title("Elevación de Satélites Evaluados")
        axs[0].set_ylabel("Elevación (Grados)")
        axs[0].axhline(y=10, color='red', linestyle='--', alpha=0.7, label="Umbral $E_{min}$ (10°)")
        axs[0].grid(True, linestyle=':', alpha=0.6)
        axs[0].legend(loc='upper right', bbox_to_anchor=(1.15, 1.0))
        
        # Configuraciones Subplot 1 (Velocidad Relativa / Doppler Bruto)
        axs[1].set_title("Velocidad Relativa (Impacto Doppler)")
        axs[1].set_ylabel("Velocidad (m/s)")
        axs[1].axhline(y=0, color='black', linestyle='-', alpha=0.3)
        axs[1].grid(True, linestyle=':', alpha=0.6)
        
        # Configuraciones Subplot 2 (Pérdida de Paquetes)
        axs[2].set_title("Pérdida de Paquetes 5G (Efecto Cascada)")
        axs[2].set_ylabel("Pérdida (%)")
        axs[2].set_xlabel("Tiempo de Simulación")
        axs[2].set_ylim(-5, 105) # Fijar la gráfica de 0 a 100%
        axs[2].grid(True, linestyle=':', alpha=0.6)
        
        # Solo mostrar leyenda si hubo conexión activa
        if not df_loss.empty:
            axs[2].legend(loc='upper right', bbox_to_anchor=(1.15, 1.0))
        else:
            axs[2].text(0.5, 0.5, 'Sin enlace 5G activo en este periodo', horizontalalignment='center', verticalalignment='center', transform=axs[2].transAxes, fontsize=12, color='gray')
        
        plt.tight_layout()
        nombre_archivo_sat = f"Analisis_Satelites_GS_{gs}.png"
        plt.savefig(nombre_archivo_sat, bbox_inches='tight')
        plt.close()
        print(f" -> Guardado: {nombre_archivo_sat}")

    # ==========================================
    # GRÁFICA 2: Trayectoria de Vuelo (Igual que antes)
    # ==========================================
    if not df_vuelo.empty and (df_vuelo['lon_deg'].nunique() > 1 or df_vuelo['lat_deg'].nunique() > 1):
        plt.figure(figsize=(8, 6))
        plt.plot(df_vuelo['lon_deg'], df_vuelo['lat_deg'], color='blue', linewidth=2, zorder=1)
        plt.scatter(df_vuelo['lon_deg'].iloc[0], df_vuelo['lat_deg'].iloc[0], color='green', s=100, label='Inicio', zorder=2)
        plt.scatter(df_vuelo['lon_deg'].iloc[-1], df_vuelo['lat_deg'].iloc[-1], color='red', s=100, label='Posición Actual', zorder=2)
        plt.title(f"Trayectoria de Vuelo (Círculo Máximo) - GS: {gs}", fontsize=14)
        plt.xlabel("Longitud (°)")
        plt.ylabel("Latitud (°)")
        plt.grid(True, linestyle='--')
        plt.legend()
        nombre_archivo_vuelo = f"Trayectoria_Vuelo_GS_{gs}.png"
        plt.savefig(nombre_archivo_vuelo)
        plt.close()
        print(f" -> Guardado: {nombre_archivo_vuelo}")