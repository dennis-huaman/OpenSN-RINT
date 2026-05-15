from opensn.operator.emulator_operator import EmulatorOperator
from opensn.model.instance import Instance
from opensn.model.position import Position
from opensn.const.dict_fields import PARAMETER_KEY_CONNECT,PARAMETER_KEY_DELAY,PARAMETER_KEY_BANDWIDTH,PARAMETER_KEY_LOSS
from opensn.model.link import LinkBase
from opensn.utils.tools import dec2ra
from config import ADDR,PORT
from datetime import datetime, timedelta
from opensn.model.doppler_channel import NR5GDopplerModel
from trajectory import calculate_postion,distance_meter,select_closest_satellite,get_propagation_delay_s, select_satellite_with_Emin, evaluate_link_geometry
from instance_types import TYPE_GROUND_STATION, TYPE_SATELLITE, EX_ORBIT_INDEX,EX_ALTITUDE_KEY,EX_LATITUDE_KEY,EX_LONGITUDE_KEY, EX_AREA_KEY, EX_TLE0_KEY, EX_TLE1_KEY, EX_TLE2_KEY
from address_type import LINK_V4_ADDR_KEY
from time import sleep
from address_allocator import alloc_ipv4,format_ipv4
from loguru import logger
import trajectory
import json, math, ephem
step_second = 1
# VER VARIABLE TIME_MULTIPLIER # 60x de velocidad (1 seg real = 1 minuto en simulación)

polar_threshold = dec2ra(66.5)

def genenrate_config(cli:EmulatorOperator,node_index:int,instance_id:str):
    instance_info = cli.get_instance(node_index,instance_id)
    config_map = {
        "instance_id": instance_id,
        "link_infos": {},
        "end_infos": {},
    }
    if instance_info.type == TYPE_SATELLITE:
        config_map['area'] = instance_info.extra[EX_AREA_KEY]
    for k,v in instance_info.connections.items():
        instance_index = -1
        link_info = cli.get_link(node_index,k)
        for end_index in range(len(link_info.end_infos)):
            if link_info.end_infos[end_index].instance_id == instance_id:
                instance_index = end_index
        if instance_index < 0:
            return {}
        another_instance_info = cli.get_instance(link_info.end_infos[1-instance_index].end_node_index,link_info.end_infos[1-instance_index].instance_id)
        config_map["link_infos"][k] = link_info.address_infos[instance_index]
        config_map["end_infos"][k] = {
            "instance_id": v.instance_id,
            "type": v.instance_type,
        }
        if another_instance_info.type == TYPE_SATELLITE:
            config_map["end_infos"][k]['area'] = another_instance_info.extra[EX_AREA_KEY]
    return config_map

if __name__ == "__main__":

    instance_config_updated:dict[str,str] = {}
    
    cli = EmulatorOperator(ADDR,PORT)
    
    base_time = None
    real_start_time = None

    previous_distance_map = {}
    f_c = 20e9 # Frecuencia portadora Banda Ka
    c = 3e8 # Velocidad de la luz

    # Se debe cambiar el bandwidth para verificar la pérdida de paquetes por Doppler. Para LoRa, típicamente se usan 125 kHz, 250 kHz o 500 kHz. 

    ntn_channel = NR5GDopplerModel(carrier_frequency=2e9, numerology_mu=1, gnss_error_margin=0.05)
    # ora_channel = LoRaDopplerModel(carrier_frequency=868e6, bandwidth=125e3, sf=12, ldro=True)

    # Create Emulator Operator
    while True:
        node_list = cli.get_node_map()
        all_instance_map: dict[str,Instance] = {}
        node_link_map: dict[int,dict[str,LinkBase]] = {}
        ground_station_list:list[Instance] = []
        for node_index,node in node_list.items():
            instance_map = cli.get_instance_map(node_index)
            for instance_id,instance in instance_map.items():
                all_instance_map[instance_id] = instance
                if instance.type == TYPE_GROUND_STATION:
                    ground_station_list.append(instance)
                    gs_position = Position()
                    gs_position.latitude = float(instance.extra[EX_LATITUDE_KEY]) / 180 * math.pi
                    gs_position.longitude = float(instance.extra[EX_LONGITUDE_KEY]) / 180 * math.pi
                    gs_position.altitude = float(instance.extra[EX_ALTITUDE_KEY])
                    cli.put_position(instance_id,gs_position)

        address_map = {}
        for node_index,node in node_list.items():
            node_link_map[node_index] = {}
            link_map = cli.get_link_map(node_index)
            for link_id,link_info in link_map.items():
                if LINK_V4_ADDR_KEY not in link_info.address_infos[0] or \
                    LINK_V4_ADDR_KEY not in link_info.address_infos[1] is None:
                    if link_id not in address_map.keys():
                        address_map[link_id] = alloc_ipv4(30)
                    
                    subnet = address_map[link_id]
                    link_info.address_infos = [{
                        LINK_V4_ADDR_KEY: format_ipv4(subnet[1],30)
                    },
                    {
                        LINK_V4_ADDR_KEY: format_ipv4(subnet[2],30)
                    }]
                    cli.put_link(link_info)
                node_link_map[node_index][link_id] = link_info
                

        position_map: dict[str,Position] = {"":Position()}
        if base_time is None:
            for instance_id, instance_info in all_instance_map.items():
                if instance_info.type == TYPE_SATELLITE:
                    try:
                        ephem_obj = ephem.readtle(
                            instance_info.extra[EX_TLE0_KEY],
                            instance_info.extra[EX_TLE1_KEY],
                            instance_info.extra[EX_TLE2_KEY],
                        )
                        base_time = ephem_obj._epoch.datetime()
                        real_start_time = datetime.now()
                        break
                    except Exception:
                        pass
            TIME_MULTIPLIER = 1
            if base_time is None:
                time_now = datetime.now()
            else:
                time_now = base_time + (datetime.now() - real_start_time) * TIME_MULTIPLIER
        else:
            time_now = base_time + (datetime.now() - real_start_time) * TIME_MULTIPLIER

        for instance_id,instance_info in all_instance_map.items():
            if instance_info.start:
                new_postion = calculate_postion(instance_info,time_now)
                cli.put_position(instance_id,new_postion)
            else:
                new_postion = Position()
            position_map[instance_id] = new_postion
        # Do Ground Station Reconnect
    

        for ground_station in ground_station_list:
            if not ground_station.start:
                continue
            gs_position = position_map[ground_station.instance_id]
            # satellite_id,change = select_closest_satellite(
            #     ground_station,
            #     position_map,
            #     all_instance_map
            # )
            e_min_threshold = 1.0 # Umbral de elevación en grados
            satellite_id,change = select_satellite_with_Emin(
                ground_station, 
                instance_map, 
                time_now, 
                e_min_deg=e_min_threshold
            )

            if change:
                # 1. Primero manejamos la desconexión del satélite viejo (esto ya lo tienes)
                address1 = {}
                address2 = {}
                old_link_id = ""
                for key in ground_station.connections.keys():
                    old_link_id = key
                    break
                
                if old_link_id != "":
                    old_link = cli.disable_link_between(
                        ground_station.node_index,
                        ground_station.instance_id,
                        ground_station.connections[old_link_id].end_node_index,
                        ground_station.connections[old_link_id].instance_id
                    )
                    logger.info("Desconectando GS %s de Sat %s (Fuera de Emin)"%(
                        ground_station.instance_id,
                        ground_station.connections[old_link_id].instance_id
                    ))

                # --- EL CAMBIO CRÍTICO ESTÁ AQUÍ ---
                # Solo intentamos conectar si hay un satélite visible que supere Emin
                if satellite_id != "":
                    if old_link_id == "": # Es una conexión nueva (antes no tenía nada)
                        subnet = alloc_ipv4(30)
                        address1 = {LINK_V4_ADDR_KEY:format_ipv4(subnet[1],30)}
                        address2 = {LINK_V4_ADDR_KEY:format_ipv4(subnet[2],30)}
                    elif len(old_link) > 0: # Reutilizamos IPs del handover
                        address1 = old_link[old_link_id].address_infos[0]
                        address2 = old_link[old_link_id].address_infos[1]

                    cli.enable_link_between(
                        ground_station.node_index,
                        ground_station.instance_id,
                        all_instance_map[satellite_id].node_index,
                        all_instance_map[satellite_id].instance_id,
                        address_info1=address1,
                        address_info2=address2,
                    )
                    # Actualizar configs
                    gs_config = genenrate_config(cli, ground_station.node_index, ground_station.instance_id)
                    cli.put_instance_config(ground_station.node_index, ground_station.instance_id, json.dumps(gs_config))
                    sat_config = genenrate_config(cli, all_instance_map[satellite_id].node_index, all_instance_map[satellite_id].instance_id)
                    cli.put_instance_config(all_instance_map[satellite_id].node_index, all_instance_map[satellite_id].instance_id, json.dumps(sat_config))
                    
                    logger.info(f"Nuevo enlace establecido con: {satellite_id}")
                else:
                    # Si satellite_id es "", simplemente informamos que la GS se quedó sin satélites
                    logger.warning(f"GS {ground_station.instance_id} ha entrado en zona de sombra (Sin cobertura).")



            # if change:
            #     address1 = {}
            #     address2 = {}
                
            #     old_link_id = ""
            #     for key in ground_station.connections.keys():
            #         old_link_id = key
            #         break
            #     if old_link_id != "":
            #         old_link = cli.disable_link_between(
            #             ground_station.node_index,
            #             ground_station.instance_id,
            #             ground_station.connections[key].end_node_index,
            #             ground_station.connections[key].instance_id
            #         )
            #         logger.info("Switch %s from %s to %s"%(
            #             ground_station.instance_id,
            #             ground_station.connections[old_link_id].instance_id,
            #             satellite_id
            #         ))
            #         old_sat_config = genenrate_config(cli,ground_station.connections[old_link_id].end_node_index,ground_station.connections[old_link_id].instance_id)
            #         cli.put_instance_config(ground_station.connections[old_link_id].end_node_index,ground_station.connections[old_link_id].instance_id,json.dumps(old_sat_config))

            #         # config_map = genenrate_config(
            #         #     satellite_id,all_instance_map[ground_station.connections[key].instance_id],node_link_map)
            #         if len(old_link) > 0:
            #             address1 = old_link[old_link_id].address_infos[0]
            #             address2 = old_link[old_link_id].address_infos[1]
            #     else:
            #         subnet = alloc_ipv4(30)
            #         address1 = {LINK_V4_ADDR_KEY:format_ipv4(subnet[1],30)}
            #         address2 = {LINK_V4_ADDR_KEY:format_ipv4(subnet[2],30)}
            #         logger.info("Switch %s from %s to %s"%(
            #             ground_station.instance_id,
            #             "None",
            #             satellite_id
            #         ))
            #     cli.enable_link_between(
            #         ground_station.node_index,
            #         ground_station.instance_id,
            #         all_instance_map[satellite_id].node_index,
            #         all_instance_map[satellite_id].instance_id,
            #         address_info1=address1,
            #         address_info2=address2,
            #     )
            #     gs_config = genenrate_config(cli,ground_station.node_index,ground_station.instance_id)
            #     # print(gs_config)
            #     cli.put_instance_config(ground_station.node_index,ground_station.instance_id,json.dumps(gs_config))
            #     sat_config = genenrate_config(cli,all_instance_map[satellite_id].node_index,all_instance_map[satellite_id].instance_id)
            #     # print(sat_config)
            #     cli.put_instance_config(all_instance_map[satellite_id].node_index,all_instance_map[satellite_id].instance_id,json.dumps(sat_config))

        
        print(70*'#')
        for node_index,link_map in node_link_map.items():
            for link_id,link_info in link_map.items():
                if link_info.parameter is None:
                    link_info.parameter = {}
                if link_info.end_infos[0].instance_id=="" or link_info.end_infos[1].instance_id == "":
                    continue
                if not link_info.enable:
                    continue
                if link_info.end_infos[0].instance_type == TYPE_SATELLITE and \
                    link_info.end_infos[1].instance_type == TYPE_SATELLITE and \
                    all_instance_map[link_info.end_infos[1].instance_id].extra[EX_ORBIT_INDEX] != \
                    all_instance_map[link_info.end_infos[0].instance_id].extra[EX_ORBIT_INDEX] and \
                    (abs(position_map[link_info.end_infos[0].instance_id].latitude) > polar_threshold or \
                    abs(position_map[link_info.end_infos[1].instance_id].latitude) > polar_threshold):
                        # if PARAMETER_KEY_CONNECT in link_info.parameter.keys() and link_info.parameter[PARAMETER_KEY_CONNECT]==1:
                        #     logger.info("connect %s"%link_id)
                        link_info.parameter[PARAMETER_KEY_CONNECT] = 0
                else:
                    # if PARAMETER_KEY_CONNECT not in link_info.parameter.keys() or link_info.parameter[PARAMETER_KEY_CONNECT]==0:
                    #         logger.info("disconnect %s"%link_id)
                    link_info.parameter[PARAMETER_KEY_CONNECT] = 1

                if link_info.end_infos[0].instance_type == "" :
                    continue

                distance = distance_meter(
                    position_map[link_info.end_infos[0].instance_id],
                    position_map[link_info.end_infos[1].instance_id]
                )
                delay = int(get_propagation_delay_s(distance)*1000000)
                link_info.parameter[PARAMETER_KEY_DELAY] = delay
                link_info.parameter[PARAMETER_KEY_BANDWIDTH] = 1000000
                # link_info.parameter[PARAMETER_KEY_LOSS] = 150 # Pérdida base (puede ser ajustada según el tipo de enlace o la distancia), el código de  # --- INICIO LÓGICA DOPPLER ---- puede ser descomentado



                ##### INICIO LOGICA 1 PARA EL PARAMETER_KEY_LOSS
                # # --- INICIO LÓGICA DOPPLER ---
                # # 1. Calcular velocidad radial (v_r) en m/s
                # if link_id in previous_distance_map:
                #     # El tiempo simulado transcurrido es step_second * TIME_MULTIPLIER
                #     simulated_elapsed_time = step_second * TIME_MULTIPLIER
                #     v_r = (distance - previous_distance_map[link_id]) / simulated_elapsed_time
                # else:
                #     v_r = 0.0
                
                # # Guardamos la distancia actual para el ciclo siguiente
                # previous_distance_map[link_id] = distance
                
                # # 2. Calcular desvío de frecuencia (f_d) en Hz
                # # Si v_r es positivo, la distancia aumenta (se aleja).
                # f_d = - f_c * (v_r / c)
                
                # # 3. Modelo Matemático de Pérdida
                # # Asumimos que el Doppler máximo es 500,000 Hz. 
                # # Mapeamos eso linealmente a un valor de pérdida (ej: max 500).
                # loss_val = int((abs(f_d) / 500000.0) * 500)
                
                # # Opcional: Descomenta el print para ver los datos en la terminal

                # iid_A = link_info.end_infos[0].instance_id
                # iid_B = link_info.end_infos[1].instance_id
                # # print(f"Enlace [{nodo_A} <---> {nodo_B}]: v_r = {v_r:.2f} m/s | Doppler = {f_d:.2f} Hz | Pérdida = {loss_val}")
                # # print(f"Link {link_id}: v_r = {v_r:.2f} m/s | Doppler = {f_d:.2f} Hz | Perdida de Paquetes = {loss_val}")

                # # Extraer los nombres legibles desde la configuración
                # def get_name(inst_id):
                #     info = all_instance_map.get(inst_id)
                #     if info:
                #         if info.type == "Satellite":
                #             # return info.extra.get("TLE_0", inst_id) # Ej: NODE_0_0
                #             return info.extra.get("TLE_0", inst_id) + " - SAT"
                #         elif info.type == "GroundStation":
                #             return "GS_" + str(info.extra.get("GroundStationIndex", inst_id)) # Ej: GS_0
                #     return inst_id
                # nodo_A = get_name(link_info.end_infos[0].instance_id)
                # nodo_B = get_name(link_info.end_infos[1].instance_id)
                
                # # Imprimir con los nombres legibles
                # # print(f"Enlace [{nodo_A} ({iid_A}) <---> {nodo_B} ({iid_B})]: v_r = {v_r:.2f} m/s | Doppler = {f_d:.2f} Hz | Pérdida = {loss_val}")



                # link_info.parameter[PARAMETER_KEY_LOSS] = loss_val
                # # --- FIN LÓGICA DOPPLER ---

                ##### FIN LOGICA 1 PARA EL PARAMETER_KEY_LOSS


                ##### INICIO LOGICA 2 PARA EL PARAMETER_KEY_LOSS EN LORA
                
                # --- LÓGICA DOPPLER (ESTÁNDAR 5G NTN) ---
                inst_A = all_instance_map[link_info.end_infos[0].instance_id]
                inst_B = all_instance_map[link_info.end_infos[1].instance_id]
                
                if inst_A.type != inst_B.type:
                    sat_inst = inst_A if inst_A.type == TYPE_SATELLITE else inst_B
                    gs_inst = inst_B if inst_B.type == TYPE_GROUND_STATION else inst_A
                    
                    # 1. Obtener la velocidad relativa (solo necesitamos 1 instante)
                    elevacion, distancia, v_r = trajectory.evaluate_link_geometry(sat_inst, gs_inst, time_now)

                    # 2. Calcular Doppler Bruto
                    raw_doppler = ntn_channel.calculate_raw_doppler(v_r)

                    packet_loss_percentage = ntn_channel.evaluate_5g_loss_gradual(raw_doppler, steepness=0.08)

                    # Convertir el porcentaje (ej. 25.4%) al formato de ETCD de OpenSN (ej. 2540)
                    loss_val = int(packet_loss_percentage * 100)

                    # 3. Evaluar los límites de la forma de onda OFDM 5G
                    packet_loss = ntn_channel.evaluate_5g_limits(raw_doppler)
                    
                    #loss_val = 10000 if packet_loss == 100.0 else 0 

                    # print(f"[{sat_inst.instance_id} 5G-NTN]: Doppler Bruto = {raw_doppler/1000:.2f} kHz | Pérdida: {packet_loss}%")
                    print(f"[{sat_inst.instance_id} 5G-NTN]: Doppler Res. = {(raw_doppler * ntn_channel.gnss_error):.0f} Hz | Límite = {ntn_channel.scs*0.10} Hz | Pérdida Gradual: {packet_loss_percentage:.2f}%")
                else:
                    loss_val = 0 

                link_info.parameter[PARAMETER_KEY_LOSS] = loss_val
                # --- FIN LÓGICA 5G NTN ---

                ##### FIN LOGICA 2 PARA EL PARAMETER_KEY_LOSS EN 5G



                cli.put_link_parameter(link_info.node_index,link_info.link_id,link_info.parameter)
                
        for instance_id,instance_info in all_instance_map.items():
            if not instance_info.start:
                continue
            config_map = genenrate_config(cli,instance_info.node_index,instance_id)
            cli.put_instance_config_if_not_exist(instance_info.node_index,instance_id,json.dumps(config_map))
        sleep(step_second)
