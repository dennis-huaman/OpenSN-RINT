
import math
import ephem
import datetime
import json
from opensn.const.const_var import R_EARTH,LIGHT_SPEED_M_S
from opensn.model.position import Position
from instance_types import TYPE_SATELLITE,TYPE_GROUND_STATION
from instance_types import EX_TLE0_KEY,EX_TLE1_KEY,EX_TLE2_KEY,EX_LATITUDE_KEY,EX_LONGITUDE_KEY,EX_ALTITUDE_KEY
from opensn.model.instance import Instance

sim_base_time = None

# --- NUEVA FUNCIÓN DE TELEMETRÍA ---
def save_telemetry_to_json(data_dict):
    """
    Guarda los diccionarios en un archivo JSONL (JSON Lines).
    Modo 'a' (append) añade la línea al final sin borrar lo anterior.
    """
    with open("telemetry_log.json", "a", encoding="utf-8") as f:
        f.write(json.dumps(data_dict) + "\n")
# -----------------------------------


def deg2rad(deg: float) -> float:
    return deg / 180 * math.pi
        
def calculate_postion(instance: Instance,time:datetime.datetime) -> Position:
    ret = Position()
    if instance.type == TYPE_SATELLITE and instance.start:
        ephem_time = ephem.Date(time)
        ephem_obj = ephem.readtle(
            instance.extra[EX_TLE0_KEY],
            instance.extra[EX_TLE1_KEY],
            instance.extra[EX_TLE2_KEY],
        )
        ephem_obj.compute(ephem_time)
        ret.latitude = ephem_obj.sublat
        ret.longitude = ephem_obj.sublong
        ret.altitude = ephem_obj.elevation
    elif instance.type == TYPE_GROUND_STATION:
        ret.latitude = deg2rad(float(instance.extra[EX_LATITUDE_KEY]))
        ret.longitude = deg2rad(float(instance.extra[EX_LONGITUDE_KEY]))
        ret.altitude = deg2rad(float(instance.extra[EX_ALTITUDE_KEY]))
    return ret

def distance_meter(one:Position,another:Position) -> float: # meter
    z1 = (one.altitude+R_EARTH) * math.sin(one.latitude)
    base1 = (one.altitude+R_EARTH) * math.cos(one.latitude)
    x1 = base1 * math.cos(one.longitude)
    y1 = base1 * math.sin(one.longitude)
    z2 = (another.altitude+R_EARTH) * math.sin(another.latitude)
    base2 = (another.altitude+R_EARTH) * math.cos(another.latitude)
    x2 = base2 * math.cos(another.longitude)
    y2 = base2 * math.sin(another.longitude)
    return math.sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)

def get_propagation_delay_s(distance_meter:float) -> float: # second
    return distance_meter / LIGHT_SPEED_M_S

def select_closest_satellite(
        ground_station:Instance,
        position_map:dict[str,Position],
        instance_map:dict[str,Instance]
    ) -> (str,bool) :
    closet_distance = math.inf
    select_satellite_id = ""
    change = True
    for instance_id,instance_info in instance_map.items():
        if instance_info.type != TYPE_SATELLITE:
            continue
        new_distance = distance_meter(
            position_map[instance_id],
            position_map[ground_station.instance_id],
        )
        if new_distance < closet_distance:
            closet_distance = new_distance
            select_satellite_id = instance_id
    if len(ground_station.connections) < 0 and select_satellite_id == "":
        return "",False
    
    for end_info in ground_station.connections.values():
        if select_satellite_id == end_info.instance_id:
            change = False
    return select_satellite_id,change


# Funciones implementadas
# def evaluate_link_geometry(sat_instance, gs_instance, current_time: datetime.datetime):
#     """
#     Implementa las ecuaciones geométricas (Apartado A) del paper LoRa.
#     Calcula la distancia oblicua (Slant Range) y el ángulo de elevación (Elevation).
#     """
#     # 1. Configurar la Ground Station como el Observador
#     gs_observer = ephem.Observer()
#     # ephem requiere las coordenadas en radianes o formato string ('grados:minutos:segundos')
#     gs_observer.lat = math.radians(float(gs_instance.extra[EX_LATITUDE_KEY]))
#     gs_observer.lon = math.radians(float(gs_instance.extra[EX_LONGITUDE_KEY]))
#     gs_observer.elevation = float(gs_instance.extra[EX_ALTITUDE_KEY])
#     gs_observer.date = ephem.Date(current_time)

#     # 2. Configurar el satélite LEO
#     sat_ephem = ephem.readtle(
#         sat_instance.extra[EX_TLE0_KEY],
#         sat_instance.extra[EX_TLE1_KEY],
#         sat_instance.extra[EX_TLE2_KEY],
#     )
    
#     # 3. Calcular la geometría relativa
#     sat_ephem.compute(gs_observer)

#     # 4. Extraer los valores requeridos por las ecuaciones
#     elevation_angle_rad = sat_ephem.alt
#     elevation_angle_deg = math.degrees(elevation_angle_rad)
    
#     slant_range_meters = sat_ephem.range # Distancia d(t)
#     range_velocity_ms = sat_ephem.range_velocity # Velocidad de acercamiento (Para Doppler)

#     return elevation_angle_deg, slant_range_meters, range_velocity_ms
def evaluate_link_geometry(sat_instance, gs_instance, current_time: datetime.datetime):
    """
    Calcula la distancia oblicua y elevación.
    Soporta Nodos Móviles consultando 'calculate_postion' en tiempo real.
    """
    gs_observer = ephem.Observer()
    
    # --- LA CORRECCIÓN CLAVE ---
    # 1. Le pedimos a tu algoritmo de vuelo dónde está el avión EXACTAMENTE en este milisegundo
    current_gs_pos = calculate_postion(gs_instance, current_time)
    
    # 2. Le pasamos estas coordenadas dinámicas a la librería ephem.
    # (Nota de seguridad: ephem es muy exigente. Transformarlo a string en grados 
    # asegura que jamás confunda radianes con grados flotantes)
    gs_observer.lat = str(math.degrees(current_gs_pos.latitude))
    gs_observer.lon = str(math.degrees(current_gs_pos.longitude))
    # ---------------------------

    gs_observer.elevation = float(gs_instance.extra[EX_ALTITUDE_KEY])
    gs_observer.date = ephem.Date(current_time)

    # Configurar el satélite LEO
    sat_ephem = ephem.readtle(
        sat_instance.extra[EX_TLE0_KEY],
        sat_instance.extra[EX_TLE1_KEY],
        sat_instance.extra[EX_TLE2_KEY],
    )
    
    # Calcular la geometría relativa
    sat_ephem.compute(gs_observer)

    # Extraer los valores requeridos
    elevation_angle_rad = sat_ephem.alt
    elevation_angle_deg = math.degrees(elevation_angle_rad)
    
    slant_range_meters = sat_ephem.range 
    range_velocity_ms = sat_ephem.range_velocity 

    return elevation_angle_deg, slant_range_meters, range_velocity_ms


def select_satellite_with_Emin(ground_station, instance_map, current_time: datetime.datetime, e_min_deg=15.0):
    """
    Reemplazo de 'select_closest_satellite' en OpenSN.
    Realiza el handover SOLO si el satélite está por encima de Emin.
    """
    closest_distance = math.inf
    select_satellite_id = ""
    change = True
    
    print(f"\n--- Evaluando enlaces para GS: {ground_station.instance_id} en {current_time} ---")

    for instance_id, instance_info in instance_map.items():
        if instance_info.type != TYPE_SATELLITE:
            continue
            
        # Calcular los valores del Apartado A para cada satélite
        elevation_deg, slant_range, rel_vel = evaluate_link_geometry(instance_info, ground_station, current_time)
        
        # Imprimir los valores para tu evaluación
        print(f"Satélite: {instance_id} | Elevación: {elevation_deg:.2f}° | Distancia: {slant_range/1000:.2f} km | Vel. Relativa: {rel_vel:.2f} m/s")

        save_telemetry_to_json({
            "timestamp": str(current_time),
            "event": "satellite_eval",
            "gs_id": ground_station.instance_id,
            "sat_id": instance_id,
            "elevation_deg": round(elevation_deg, 2),
            "distance_km": round(slant_range / 1000, 2),
            "rel_vel_m_s": round(rel_vel, 2)
        })

        # FILTRO DE HANDOVER: Solo consideramos satélites por encima de E_min
        if elevation_deg >= e_min_deg:
            # Entre los satélites visibles, elegimos el que tenga el Slant Range más corto
            if slant_range < closest_distance:
                closest_distance = slant_range
                select_satellite_id = instance_id

    if len(ground_station.connections) > 0 and select_satellite_id == "":
        return "", True # Se perdió cobertura total (ninguno supera Emin)
    elif len(ground_station.connections) == 0 and select_satellite_id == "":
        return "", False # Seguimos sin cobertura
        
    for end_info in ground_station.connections.values():
        if select_satellite_id == end_info.instance_id:
            change = False # No hay necesidad de handover, sigue siendo el óptimo
            
    if select_satellite_id != "":
        print(f">>> Handover decidido hacia: {select_satellite_id} (Elevación superior a {e_min_deg}°) <<<")
        save_telemetry_to_json({
            "timestamp": str(current_time),
            "event": "handover",
            "gs_id": ground_station.instance_id,
            "selected_sat_id": select_satellite_id,
            "e_min_deg": e_min_deg
        })
        # -------------------------------------------
        
    return select_satellite_id, change


def great_circle_interpolate(lat1_deg, lon1_deg, lat2_deg, lon2_deg, fraction):
    """
    Calcula la posición exacta en la superficie terrestre (Círculo Máximo) 
    dado un porcentaje de progreso (fraction) entre dos puntos.
    """
    if fraction <= 0.0: return lat1_deg, lon1_deg
    if fraction >= 1.0: return lat2_deg, lon2_deg

    # Convertir a radianes
    lat1, lon1 = math.radians(lat1_deg), math.radians(lon1_deg)
    lat2, lon2 = math.radians(lat2_deg), math.radians(lon2_deg)

    # Distancia angular entre los dos puntos
    cos_d = math.sin(lat1)*math.sin(lat2) + math.cos(lat1)*math.cos(lat2)*math.cos(lon2 - lon1)
    # Evitar errores de dominio por precisión de punto flotante (ej. 1.0000000002)
    cos_d = max(-1.0, min(1.0, cos_d)) 
    d = math.acos(cos_d)

    if d == 0:
        return lat1_deg, lon1_deg

    # Interpolar en la esfera
    a = math.sin((1.0 - fraction) * d) / math.sin(d)
    b = math.sin(fraction * d) / math.sin(d)

    x = a * math.cos(lat1) * math.cos(lon1) + b * math.cos(lat2) * math.cos(lon2)
    y = a * math.cos(lat1) * math.sin(lon1) + b * math.cos(lat2) * math.sin(lon2)
    z = a * math.sin(lat1) + b * math.sin(lat2)

    lat_i = math.atan2(z, math.sqrt(x**2 + y**2))
    lon_i = math.atan2(y, x)

    return math.degrees(lat_i), math.degrees(lon_i)



def calculate_postion(instance: Instance, current_time: datetime.datetime) -> Position:
    global sim_base_time
    
    if sim_base_time is None:
        sim_base_time = current_time

    ret = Position()
    
    # --- 1. LÓGICA DE SATELLITES ---
    if instance.type == TYPE_SATELLITE and instance.start:
        ephem_time = ephem.Date(current_time)
        ephem_obj = ephem.readtle(
            instance.extra[EX_TLE0_KEY],
            instance.extra[EX_TLE1_KEY],
            instance.extra[EX_TLE2_KEY],
        )
        ephem_obj.compute(ephem_time)
        ret.latitude = ephem_obj.sublat
        ret.longitude = ephem_obj.sublong
        ret.altitude = ephem_obj.elevation
        
    # --- 2. LÓGICA DE GROUND STATIONS Y AVIONES ---
    elif instance.type == TYPE_GROUND_STATION:
        if instance.extra.get("IsMobile") == "true":
            # Extraer parámetros de vuelo en grados
            lat_a = float(instance.extra[EX_LATITUDE_KEY])
            lon_a = float(instance.extra[EX_LONGITUDE_KEY])
            lat_b = float(instance.extra["Lat_End"])
            lon_b = float(instance.extra["Lon_End"])
            
            # --- NUEVO: Calcular Distancia y Tiempo basado en Velocidad ---
            # 1. Calculamos la distancia angular entre A y B
            lat1_rad, lon1_rad = math.radians(lat_a), math.radians(lon_a)
            lat2_rad, lon2_rad = math.radians(lat_b), math.radians(lon_b)
            cos_d = math.sin(lat1_rad)*math.sin(lat2_rad) + math.cos(lat1_rad)*math.cos(lat2_rad)*math.cos(lon2_rad - lon1_rad)
            cos_d = max(-1.0, min(1.0, cos_d))
            d_rad = math.acos(cos_d)
            
            # 2. Multiplicamos por el radio de la Tierra para obtener metros (Arco de circunferencia)
            distancia_total_m = d_rad * R_EARTH
            
            # 3. Leer velocidad y deducir el tiempo de viaje (t = d / v)
            velocidad_m_s = float(instance.extra.get("Velocity_m_s", 250.0))
            
            if velocidad_m_s > 0 and distancia_total_m > 0:
                t_viaje = distancia_total_m / velocidad_m_s
            else:
                t_viaje = 1.0 # Evitar división por cero si la distancia o velocidad es 0

            # --- FIN DEL NUEVO CÁLCULO ---

            delta_t = (current_time - sim_base_time).total_seconds()
            
            # Continuamos con la lógica de ciclo usando el tiempo calculado
            if distancia_total_m > 0:
                ciclo = delta_t % (2 * t_viaje)
                
                # Reemplazamos la interpolación lineal 2D por la esférica 3D
                if ciclo <= t_viaje:
                    # FASE IDA
                    progreso = ciclo / t_viaje
                    lat_actual, lon_actual = great_circle_interpolate(lat_a, lon_a, lat_b, lon_b, progreso)
                else:
                    # FASE REGRESO
                    progreso = (ciclo - t_viaje) / t_viaje
                    lat_actual, lon_actual = great_circle_interpolate(lat_b, lon_b, lat_a, lon_a, progreso)
            else:
                # Si A y B son las mismas coordenadas
                lat_actual, lon_actual = lat_a, lon_a
            
            # deg2rad asumo que es tu función para convertir a radianes, requerida por el ret.latitude
            ret.latitude = deg2rad(lat_actual)
            ret.longitude = deg2rad(lon_actual)
            print(f"[VUELO] Tiempo: {delta_t:.1f}s | Progreso: {(progreso*100):.4f}% | Lon Actual: {lon_actual:.6f}° | Lat Actual: {lat_actual:.6f}°")
            # --- NUEVO: Guardar ruta de vuelo ---
            save_telemetry_to_json({
                "timestamp": str(current_time),
                "event": "flight_progress",
                "gs_id": instance.instance_id,
                "flight_time_s": round(delta_t, 1),
                "progress_pct": round(progreso * 100, 4),
                "lon_deg": round(lon_actual, 6),
                "lat_deg": round(lat_actual, 6)
            })
            # ------------------------------------
        else:
            # Comportamiento estático
            ret.latitude = deg2rad(float(instance.extra[EX_LATITUDE_KEY]))
            ret.longitude = deg2rad(float(instance.extra[EX_LONGITUDE_KEY]))
        
        ret.altitude = float(instance.extra[EX_ALTITUDE_KEY])
        
    return ret

