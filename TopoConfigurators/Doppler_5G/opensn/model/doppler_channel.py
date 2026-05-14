import math
from opensn.const.const_var import LIGHT_SPEED_M_S

class NR5GDopplerModel:
    def __init__(self, carrier_frequency=2e9, scs=15e3, gnss_error_margin=0.05):
        """
        Modelo 5G NTN basado en CP-OFDM.
        carrier_frequency: Banda S (~2 GHz) o Banda Ku (~12 GHz)
        scs: Subcarrier Spacing (ej. 15kHz, 30kHz, 60kHz)
        gnss_error_margin: % de error en la pre-compensación del equipo (ej. 5% = 0.05)
        """
        self.c = LIGHT_SPEED_M_S
        self.f_c = carrier_frequency
        self.scs = scs
        self.gnss_error = gnss_error_margin

    def calculate_raw_doppler(self, range_velocity):
        # Doppler bruto generado por el movimiento del satélite
        return abs((range_velocity / self.c) * self.f_c)

    def evaluate_5g_limits(self, raw_doppler):
        """
        Evalúa si la conexión 5G soporta el Doppler actual.
        Basado en "Integration of Satellites in 5G through LEO Constellations"
        """
        # 1. El módem aplica la pre-compensación usando su GNSS
        # En la realidad perfecta, el residual sería 0. En la práctica, queda un error.
        residual_doppler = raw_doppler * self.gnss_error
        
        # 2. Límite de Interferencia Inter-Portadora (ICI) en OFDM
        # La regla general en 3GPP es que el desvío no debe superar ~10% del SCS
        ici_limit = 0.10 * self.scs
        
        # 3. Decisión de pérdida
        if residual_doppler >= ici_limit:
            return 100.0 # Pierde sincronización OFDM (Fallo total de enlace)
        
        return 0.0 # El módem 5G NTN compensó exitosamente el Doppler