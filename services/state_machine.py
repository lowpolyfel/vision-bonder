import time

class StateMachine:
    """
    Controla transiciones IDLE/ACTIVO con tolerancia para IDLE.
    No registra la tolerancia: solo confirma cambios.
    Llama al callback on_segment(prev_estado, inicio, fin) al cerrar cada tramo.
    """

    def __init__(self, base_datetime, tolerancia_idle_segundos, on_segment_callback):
        self.base_datetime = base_datetime      # t0 para anclar el primer tramo
        self.tolerancia = tolerancia_idle_segundos
        self.on_segment = on_segment_callback   # function(prev_estado, inicio, fin)
        self.estado_actual = None               # "IDLE" o "ACTIVO"
        self.inicio_estado_timestamp = None
        self.tiempo_inicio_idle_pendiente = None  # reloj del sistema (time.time)

    def process(self, estado_detectado, ts_actual):
        """
        estado_detectado: "IDLE" o "ACTIVO"
        ts_actual: datetime (según auditoría en tiempo real)
        """
        # Inicialización: primer estado se ancla a t0 del video
        if self.estado_actual is None:
            self.estado_actual = estado_detectado
            self.inicio_estado_timestamp = self.base_datetime
            return None  # no hay segmento cerrado aún

        # Transiciones
        if self.estado_actual == "IDLE":
            if estado_detectado == "ACTIVO":
                # Cierra IDLE [inicio .. ts_actual] y abre ACTIVO
                self._cerrar_tramo_y_cambiar("ACTIVO", ts_actual)
        else:  # estado_actual == "ACTIVO"
            if estado_detectado == "IDLE":
                # Tolerancia: confirmar vuelta a IDLE
                if self.tiempo_inicio_idle_pendiente is None:
                    self.tiempo_inicio_idle_pendiente = time.time()
                else:
                    if time.time() - self.tiempo_inicio_idle_pendiente >= self.tolerancia:
                        self._cerrar_tramo_y_cambiar("IDLE", ts_actual)
                        self.tiempo_inicio_idle_pendiente = None
            else:
                # sigue ACTIVO, cancelar conteo si lo había
                self.tiempo_inicio_idle_pendiente = None

        # No retorna nada; reporta segmentos vía callback

    def _cerrar_tramo_y_cambiar(self, nuevo_estado, ts_corte):
        # Notificar tramo cerrado del estado previo
        if self.inicio_estado_timestamp is not None and self.estado_actual is not None:
            self.on_segment(self.estado_actual, self.inicio_estado_timestamp, ts_corte)
        # Abrir nuevo tramo
        self.estado_actual = nuevo_estado
        self.inicio_estado_timestamp = ts_corte

    def close_final(self, ts_fin):
        """Cierra el tramo vigente al terminar el video o al cerrar la app."""
        if self.estado_actual is not None and self.inicio_estado_timestamp is not None:
            self.on_segment(self.estado_actual, self.inicio_estado_timestamp, ts_fin)

    # Helpers para UI (contador tolerancia)
    def get_tolerancia_restante(self):
        if self.tiempo_inicio_idle_pendiente is None:
            return None
        restante = int(self.tolerancia - (time.time() - self.tiempo_inicio_idle_pendiente))
        return max(0, restante)

