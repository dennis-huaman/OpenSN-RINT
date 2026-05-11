# # Archivo: TopoConfigurators/Standard/opensn/model/doppler_channel.py

# import math
# # ¡Importamos la velocidad de la luz y el radio de la Tierra desde las constantes del repositorio!
# from opensn.const.const_var import LIGHT_SPEED_M_S, R_EARTH 

# class LoRaDopplerModel:
#     def __init__(self, carrier_frequency=868e6, bandwidth=125e3, sf=10, ldro=False):
#         # Asignamos la constante oficial de OpenSN a nuestra variable c
#         self.c = LIGHT_SPEED_M_S 
#         self.carrier_freq = carrier_frequency
#         self.bw = bandwidth
#         self.sf = sf
#         self.ldro = ldro

#     def calculate_doppler_shift(self, range_velocity):
#         """
#         Calcula el desfase Doppler (Hz) usando la velocidad relativa 
#         y la velocidad de la luz nativa del emulador.
#         """
#         return (range_velocity / self.c) * self.carrier_freq

#     def calculate_packet_loss(self, doppler_start, doppler_end):
#         """
#         Implementación de las ecuaciones del paper:
#         "Understanding the Limits of LoRa Direct-to-Satellite"
#         """
#         # 1. Doppler Estático (Umbral = 25% del Ancho de Banda)
#         f_static_limit = 0.25 * self.bw
#         l_static = 1 if abs(doppler_start) >= f_static_limit else 0
        
#         # 2. Doppler Dinámico (Variación durante el ToA)
#         L = 16 if self.ldro else 1
#         f_dynamic_limit = (L * self.bw) / (3 * (2**self.sf))
#         delta_f_e = abs(doppler_start - doppler_end)
#         l_dynamic = 1 if delta_f_e >= f_dynamic_limit else 0
        
#         # 3. Decisión de pérdida (100% de pérdida si falla cualquier umbral)
#         if l_static == 1 or l_dynamic == 1:
#             return 100.0
#         return 0.0



# Archivo: TopoConfigurators/Standard/opensn/model/doppler_channel.py

# Archivo: TopoConfigurators/Standard/opensn/model/doppler_channel.py

import math
from opensn.const.const_var import LIGHT_SPEED_M_S

class LoRaDopplerModel:
    def __init__(self, carrier_frequency=868e6, bandwidth=125e3, sf=12, ldro=True):
        self.c = LIGHT_SPEED_M_S 
        self.f_c = carrier_frequency
        self.bw = bandwidth
        self.sf = sf
        self.ldro = ldro

    def calculate_doppler_shift(self, range_velocity):
        """
        Ecuación del Doppler Shift (F_D) del Apartado B.
        F_D(t) = -(V_r(t) / c) * f_c
        (El signo negativo asume que si V_r es negativo (acercándose), el Doppler es positivo).
        """
        # range_velocity es negativa al acercarse en ephem, por lo que -V_r/c da un Doppler Shift positivo.
        doppler_shift = - (range_velocity / self.c) * self.f_c
        return doppler_shift

    def calculate_doppler_rate(self, doppler_t1, doppler_t2, time_delta_seconds):
        """
        Ecuación del Doppler Rate (R_D) del Apartado B.
        R_D(t) = d(F_D) / dt
        En un emulador discreto, usamos diferencias finitas: (F_D2 - F_D1) / Δt
        Devuelve el valor absoluto en Hz/s.
        """
        doppler_rate = abs(doppler_t2 - doppler_t1) / time_delta_seconds
        return doppler_rate

    def evaluate_lora_limits(self, doppler_shift, doppler_rate, time_on_air):
        """
        Evalúa si la física calculada rompe los límites del módem LoRa.
        """
        # 1. Límite del Doppler Estático (F_static)
        f_static_limit = 0.25 * self.bw
        l_static = 1 if abs(doppler_shift) >= f_static_limit else 0
        
        # 2. Límite del Doppler Dinámico basado en el Rate (F_dynamic)
        L = 16 if self.ldro else 1
        f_dynamic_limit = (L * self.bw) / (3 * (2**self.sf))
        
        # El cambio de frecuencia total DURANTE el paquete es (Rate * ToA)
        delta_f_e = doppler_rate * time_on_air 
        l_dynamic = 1 if delta_f_e >= f_dynamic_limit else 0
        
        # 3. Resultado de pérdida
        return 100.0 if (l_static == 1 or l_dynamic == 1) else 0.0

    def get_time_on_air(self, payload_bytes=10):
        """Aproximación simple del ToA en segundos para LoRa. (Puede ser sustituido por la fórmula exacta)"""
        # Para SF12 y BW 125kHz, un paquete de 10 bytes tarda aprox ~1.31 segundos.
        if self.sf == 12: return 1.31
        elif self.sf == 11: return 0.65
        elif self.sf == 10: return 0.32
        else: return 0.16 # ...etc