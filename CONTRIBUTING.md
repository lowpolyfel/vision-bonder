# Guía de Contribución

¡Gracias por tu interés en mejorar Monitoreo Industrial! Este documento resume el flujo de trabajo y las expectativas para colaborar de manera efectiva.

## 🧭 Principios generales

- **Respeto y comunicación clara.** Describe el problema y la solución propuesta en detalle.
- **Pequeños cambios, revisiones ágiles.** Prefiere _pull requests_ enfocados a un objetivo específico.
- **Calidad antes que cantidad.** Mantén la consistencia con el estilo y patrones existentes.

## 🛠️ Requisitos previos

1. Python 3.10 o superior.
2. Entorno virtual activado (`python -m venv .venv && source .venv/bin/activate`).
3. Dependencias instaladas:
   ```bash
   pip install -r requirements-dev.txt
   ```
4. Acceso a una instancia de MySQL para pruebas integrales (opcional pero recomendado).

## 🚀 Flujo de trabajo propuesto

1. **Fork y rama de trabajo**
   - Haz fork del repositorio y crea una rama descriptiva (`feature/deteccion-mejorada`, `fix/mysql-retry`, etc.).
2. **Configura el entorno**
   - Ajusta `config/settings.py` con credenciales locales.
   - Crea bases de datos o mocks según tus pruebas.
3. **Escribe código y pruebas**
   - Sigue el estilo PEP 8.
   - Ejecuta linters y pruebas antes de enviar el cambio:
     ```bash
     black .
     flake8
     pytest
     ```
4. **Actualiza documentación**
   - Si tu cambio afecta la configuración, dependencias o uso del sistema, actualiza `README.md` o crea notas en `docs/`.
5. **Prepara tu Pull Request**
   - Completa la plantilla de PR (resumen, pruebas realizadas, riesgos conocidos).
   - Adjunta capturas de pantalla o clips si el cambio afecta la UI.
   - Solicita revisión a un mantenedor.

## ✅ Criterios de aceptación

- Código formateado con `black` y sin errores de `flake8`.
- Pruebas relevantes agregadas y/o existentes pasan.
- Documentación actualizada.
- Commits con mensajes descriptivos (imperativo, ≤ 72 caracteres).

## 📣 Comunicación

- Usa los _issues_ para reportar bugs o proponer mejoras.
- Emplea etiquetas (`bug`, `enhancement`, `help wanted`) para facilitar el triage.
- Para dudas rápidas, utiliza el canal de chat definido por tu equipo (Slack, Teams, etc.).

¡Felices contribuciones! 🚀

