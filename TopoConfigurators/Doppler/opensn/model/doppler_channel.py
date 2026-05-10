# Archivo: TopoConfigurators/Standard/opensn/model/doppler_channel.py

import math
# ¡Importamos la velocidad de la luz y el radio de la Tierra desde las constantes del repositorio!
from opensn.const.const_var import LIGHT_SPEED_M_S, R_EARTH 

class LoRaDopplerModel:
    def __init__(self, carrier_frequency=868e6, bandwidth=125e3, sf=10, ldro=False):
        # Asignamos la constante oficial de OpenSN a nuestra variable c
        self.c = LIGHT_SPEED_M_S 
        self.carrier_freq = carrier_frequency
        self.bw = bandwidth
        self.sf = sf
        self.ldro = ldro

    def calculate_doppler_shift(self, range_velocity):
        """
        Calcula el desfase Doppler (Hz) usando la velocidad relativa 
        y la velocidad de la luz nativa del emulador.
        """
        return (range_velocity / self.c) * self.carrier_freq

    def calculate_packet_loss(self, doppler_start, doppler_end):
        """
        Implementación de las ecuaciones del paper:
        "Understanding the Limits of LoRa Direct-to-Satellite"
        """
        # 1. Doppler Estático (Umbral = 25% del Ancho de Banda)
        f_static_limit = 0.25 * self.bw
        l_static = 1 if abs(doppler_start) >= f_static_limit else 0
        
        # 2. Doppler Dinámico (Variación durante el ToA)
        L = 16 if self.ldro else 1
        f_dynamic_limit = (L * self.bw) / (3 * (2**self.sf))
        delta_f_e = abs(doppler_start - doppler_end)
        l_dynamic = 1 if delta_f_e >= f_dynamic_limit else 0
        
        # 3. Decisión de pérdida (100% de pérdida si falla cualquier umbral)
        if l_static == 1 or l_dynamic == 1:
            return 100.0
        return 0.0