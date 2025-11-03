class EventRecorder:
    """
    Traductor de segmentos a estatus 0/1 y escritura en BD.
    """
    def __init__(self, db_manager, id_maquina):
        self.db = db_manager
        self.id_maquina = id_maquina

    def on_segment(self, estado, inicio, fin):
        estatus = 1 if estado == "ACTIVO" else 0
        self.db.registrar_evento_completo(self.id_maquina, inicio, fin, estatus)

