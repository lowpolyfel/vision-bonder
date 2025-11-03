import mysql.connector

class DBManager:
    def __init__(self, config):
        self.config = config
        self.cnx = None
        self.cursor = None
        self.conectar()

    def conectar(self):
        try:
            self.cnx = mysql.connector.connect(**self.config)
            self.cursor = self.cnx.cursor()
            print("✅ Conexión a la base de datos establecida.")
        except mysql.connector.Error as err:
            print(f"❌ Error de conexión a BD: {err}")
            self.cnx = None

    def _siguiente_id(self, tabla, pk_col):
        """Fallback si no hay AUTO_INCREMENT."""
        self.cursor.execute(f"SELECT COALESCE(MAX({pk_col}), 0) + 1 FROM {tabla}")
        (next_id,) = self.cursor.fetchone()
        return int(next_id)

    def registrar_evento_completo(self, id_maquina, fecha_inicio, fecha_fin, estatus):
        """
        Inserta una operación base y su estado asociado.
        estatus: 1=ACTIVO, 0=IDLE
        """
        if not self.cnx or not self.cnx.is_connected():
            print("❌ Sin conexión activa. Abortando registro.")
            return

        try:
            self.cnx.start_transaction()

            # 1) operacion_maquina (dummy mínima para satisfacer FK)
            sql_operacion = """
                INSERT INTO operacion_maquina (
                    id_maquina, id_operador, id_reel, id_tecnico, id_work_order,
                    fecha_inicio, fecha_fin
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            valores_op = (id_maquina, 1, 1, 1, 1, fecha_inicio, fecha_fin)
            self.cursor.execute(sql_operacion, valores_op)
            id_operacion_generada = self.cursor.lastrowid

            # 2) estado_maquina (AI o PK manual)
            duracion_seg = int((fecha_fin - fecha_inicio).total_seconds())
            sql_estado_sin_pk = """
                INSERT INTO estado_maquina (
                    id_operacion, id_maquina, estatus, fecha_inicio, fecha_fin, duracion_seg
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            valores_estado = (id_operacion_generada, id_maquina, estatus, fecha_inicio, fecha_fin, duracion_seg)

            try:
                self.cursor.execute(sql_estado_sin_pk, valores_estado)
            except mysql.connector.Error as e:
                print(f"⚠️ Insert estado_maquina sin PK falló: {e}")
                next_id = self._siguiente_id("estado_maquina", "id_estado_maquina")
                sql_estado_con_pk = """
                    INSERT INTO estado_maquina (
                        id_estado_maquina, id_operacion, id_maquina, estatus, fecha_inicio, fecha_fin, duracion_seg
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                valores_estado_con_pk = (next_id,) + valores_estado
                self.cursor.execute(sql_estado_con_pk, valores_estado_con_pk)

            self.cnx.commit()

        except mysql.connector.Error as err:
            print(f"❌ Error SQL (rollback): {err}")
            try:
                self.cnx.rollback()
            except Exception:
                pass

    def cerrar(self):
        if self.cnx and self.cnx.is_connected():
            self.cursor.close()
            self.cnx.close()
            print("🔒 Conexión a BD cerrada.")

