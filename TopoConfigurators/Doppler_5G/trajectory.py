
import math
import ephem
import datetime
from opensn.const.const_var import R_EARTH,LIGHT_SPEED_M_S
from opensn.model.position import Position
from instance_types import TYPE_SATELLITE,TYPE_GROUND_STATION
from instance_types import EX_TLE0_KEY,EX_TLE1_KEY,EX_TLE2_KEY,EX_LATITUDE_KEY,EX_LONGITUDE_KEY,EX_ALTITUDE_KEY
from opensn.model.instance import Instance

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
def evaluate_link_geometry(sat_instance, gs_instance, current_time: datetime.datetime):
    """
    Implementa las ecuaciones geométricas (Apartado A) del paper LoRa.
    Calcula la distancia oblicua (Slant Range) y el ángulo de elevación (Elevation).
    """
    # 1. Configurar la Ground Station como el Observador
    gs_observer = ephem.Observer()
    # ephem requiere las coordenadas en radianes o formato string ('grados:minutos:segundos')
    gs_observer.lat = math.radians(float(gs_instance.extra[EX_LATITUDE_KEY]))
    gs_observer.lon = math.radians(float(gs_instance.extra[EX_LONGITUDE_KEY]))
    gs_observer.elevation = float(gs_instance.extra[EX_ALTITUDE_KEY])
    gs_observer.date = ephem.Date(current_time)

    # 2. Configurar el satélite LEO
    sat_ephem = ephem.readtle(
        sat_instance.extra[EX_TLE0_KEY],
        sat_instance.extra[EX_TLE1_KEY],
        sat_instance.extra[EX_TLE2_KEY],
    )
    
    # 3. Calcular la geometría relativa
    sat_ephem.compute(gs_observer)

    # 4. Extraer los valores requeridos por las ecuaciones
    elevation_angle_rad = sat_ephem.alt
    elevation_angle_deg = math.degrees(elevation_angle_rad)
    
    slant_range_meters = sat_ephem.range # Distancia d(t)
    range_velocity_ms = sat_ephem.range_velocity # Velocidad de acercamiento (Para Doppler)

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
        
    return select_satellite_id, change