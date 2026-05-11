# SignCam — Cámara virtual con subtítulos de lengua de signos

## Objetivo del proyecto
App que captura la webcam del usuario, detecta lengua de signos (LSE/LSC) en tiempo real con MediaPipe + modelo clasificador, superpone subtítulos en el vídeo, y lo expone como cámara virtual para que funcione en cualquier app de videollamada (Teams, Meet, Zoom).

## Stack
- Python 3.12 (no 3.14 — mediapipe no tiene wheels para 3.14)
- MediaPipe Holistic / Hands para extracción de landmarks
- OpenCV para captura y composición de frames
- pyvirtualcam para exponer la cámara virtual al SO
- Driver: OBS Virtual Camera (se instala una vez, no requiere OBS abierto)

## Entorno de desarrollo
- Windows 10/11
- Entorno virtual en `venv/` usando `py -3.12 -m venv venv`
- Activar con `venv\Scripts\activate`
- Instalar dependencias con `pip install -r requirements.txt`

## Archivos principales
- `signcam_poc.py` — script de prueba de concepto (pipeline completo con clasificador dummy)
- `requirements.txt` — dependencias Python

## Fases del proyecto
1. PoC: pipeline cámara → landmarks → subtítulo dummy → cámara virtual ✅
2. Clasificador real: modelo ONNX entrenado con gestos LSE/LSC
3. UI: app Electron + React con panel de configuración
4. Empaquetado: instalador que incluye el driver de cámara virtual sin OBS

## Notas importantes
- pyvirtualcam en Windows usa el driver de OBS Virtual Camera. Para desarrollo, instalar OBS Studio una vez para registrar el driver, luego se puede cerrar OBS.
- La resolución de salida es 1280x(720+60) — los 60px extra son la banda de subtítulos.
- El clasificador real (fase 2) sustituye la función `detectar_signo_fake()`.
