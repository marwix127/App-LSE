"""SignCam sidecar — pipeline de reconocimiento pensado para ser lanzado por Electron.

Protocolo de comunicacion:
- ENTRADA: argumentos de linea de comandos (config) + comandos por stdin (una palabra
  por linea, p.ej. "stop").
- SALIDA: eventos JSON por stdout, uno por linea (NDJSON). Los logs/warnings de
  TensorFlow y MediaPipe van a stderr, asi stdout queda limpio para que Electron parsee.

Eventos emitidos por stdout:
  {"type": "init", "stage": "loading_models"}
  {"type": "init", "stage": "camera_opened"}
  {"type": "ready", "virtual_camera": "...", "width": W, "height": H}
  {"type": "status", "letter": "A", "is_movement": false, "fps": 28.3}
  {"type": "error", "message": "..."}
  {"type": "stopped"}
"""

import os
import sys
import json

# Modo rápido "--list-cameras": lista las cámaras y sale ANTES de importar cv2,
# mediapipe, etc. (que tardan segundos). Solo usa pygrabber (ligero). Así Electron
# puebla el desplegable al instante, tanto con Python como con el .exe empaquetado.
if "--list-cameras" in sys.argv:
    EXCLUIR = ("OBS Virtual Camera", "SignCam")
    try:
        from pygrabber.dshow_graph import FilterGraph
        nombres = FilterGraph().get_input_devices()
        devices = [
            {"index": i, "name": n}
            for i, n in enumerate(nombres)
            if not any(x in n for x in EXCLUIR)
        ]
        sys.stdout.write(json.dumps({"devices": devices}))
    except Exception as e:  # noqa: BLE001
        sys.stdout.write(json.dumps({"devices": [], "error": str(e)}))
    sys.exit(0)

import time
import pickle
import argparse
import threading

# IMPORTANTE: importar sklearn ANTES de inicializar COM (MTA). Al cargar el MLP con
# pickle, sklearn importa de forma diferida su backend de hilos (OpenMP/joblib), que
# choca con la inicialización MTA de COM y produce un deadlock permanente al "cargar
# modelos". Forzando el import aquí, ese backend se inicializa antes que COM. No quitar.
import sklearn  # noqa: F401
import sklearn.neural_network  # noqa: F401


# Inicializa COM en modo MULTITHREADED (MTA) antes de tocar la cámara. Lanzado como
# proceso hijo de Electron, el hilo entra por defecto en STA, que necesita un bucle de
# mensajes que el sidecar no tiene (está en el bucle de captura) -> deadlock de COM
# (ventana "OleMainThreadWndName Not Responding"). En MTA no hace falta ese bucle.
if sys.platform == "win32":
    import ctypes
    COINIT_MULTITHREADED = 0x0
    ctypes.windll.ole32.CoInitializeEx(None, COINIT_MULTITHREADED)

import cv2
import numpy as np
import pyvirtualcam
from pyvirtualcam import PixelFormat
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
import onnxruntime as ort
from landmarks_utils import normalizar


def recurso(nombre):
    """Resuelve la ruta de un archivo de datos (modelos).

    - Empaquetado con PyInstaller: los datos van a la carpeta temporal sys._MEIPASS.
    - En desarrollo: junto a este script.
    Así funciona igual ejecutado con Python o como .exe, sin rutas absolutas.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, nombre)


MODEL_PATH = recurso("hand_landmarker.task")
MLP_PATH = recurso("mlp_signos.pkl")
LSTM_PATH = recurso("lstm_signos.onnx")
LSTM_ENCODER_PATH = recurso("lstm_encoder.pkl")

ANCHO, ALTO, FPS = 1280, 720, 30
BUFFER_SIZE = 30
CONF_MIN = 0.95
MIN_TIEMPO_ENTRE_CAMBIOS = 0.5

_stop = threading.Event()


def emit(obj):
    """Emite un evento JSON por stdout (una linea) y hace flush para tiempo real."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def escuchar_stdin():
    """Hilo que lee comandos de Electron por stdin. 'stop' detiene el bucle."""
    for linea in sys.stdin:
        if linea.strip().lower() == "stop":
            _stop.set()
            return


def crear_landmarker():
    opts = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return HandLandmarker.create_from_options(opts)


def cargar_mlp():
    with open(MLP_PATH, "rb") as f:
        datos = pickle.load(f)
    return datos["model"], datos["encoder"]


def cargar_lstm():
    sesion = ort.InferenceSession(LSTM_PATH, providers=["CPUExecutionProvider"])
    entrada = sesion.get_inputs()[0].name
    with open(LSTM_ENCODER_PATH, "rb") as f:
        le = pickle.load(f)
    return sesion, entrada, le


def dibujar_landmarks(frame, resultado):
    if not resultado.hand_landmarks:
        return
    h, w = frame.shape[:2]
    conexiones = mp.tasks.vision.HandLandmarksConnections.HAND_CONNECTIONS
    for mano in resultado.hand_landmarks:
        puntos = [(int(lm.x * w), int(lm.y * h)) for lm in mano]
        for c in conexiones:
            cv2.line(frame, puntos[c.start], puntos[c.end], (0, 200, 0), 2)
        for x, y in puntos:
            cv2.circle(frame, (x, y), 4, (255, 255, 255), -1)


def clasificar_signo(resultado, clf, le):
    if not resultado.hand_landmarks:
        return "", 0.0
    es_izquierda = resultado.handedness[0][0].category_name == "Left"
    landmarks = normalizar(resultado.hand_landmarks[0], es_izquierda)
    pred_probs = clf.predict_proba([landmarks])[0]
    clase_idx = np.argmax(pred_probs)
    confianza = pred_probs[clase_idx]
    if confianza < CONF_MIN:
        return "", confianza
    return le.inverse_transform([clase_idx])[0], confianza


def hay_movimiento(buffer):
    if len(buffer) < BUFFER_SIZE:
        return False
    seq = np.array(buffer[-BUFFER_SIZE:])
    movimiento = np.mean(np.std(seq, axis=0))
    return movimiento > 0.03


def clasificar_secuencia(buffer, lstm_sesion, lstm_entrada, lstm_le):
    if len(buffer) < BUFFER_SIZE or not hay_movimiento(buffer):
        return ""
    seq = np.expand_dims(np.array(buffer[-BUFFER_SIZE:], dtype=np.float32), axis=0)
    pred = lstm_sesion.run(None, {lstm_entrada: seq})[0]
    clase = np.argmax(pred)
    if pred[0, clase] < CONF_MIN:
        return ""
    return lstm_le.inverse_transform([clase])[0]


def dibujar_subtitulo(frame, texto, escala, posicion):
    banda_h = int(120 * escala)
    banda = np.zeros((banda_h, frame.shape[1], 3), dtype=np.uint8)
    if texto:
        y = int(banda_h * 0.7)
        cv2.putText(banda, texto, (40, y), cv2.FONT_HERSHEY_SIMPLEX,
                    3.0 * escala, (255, 255, 255), max(2, int(4 * escala)))
    if posicion == "top":
        return np.vstack([banda, frame])
    return np.vstack([frame, banda])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--subtitle-scale", type=float, default=1.0)
    parser.add_argument("--subtitle-position", choices=["top", "bottom"], default="bottom")
    args = parser.parse_args()

    threading.Thread(target=escuchar_stdin, daemon=True).start()

    try:
        emit({"type": "init", "stage": "opening_camera"})
        # Backend por defecto (MSMF en Windows): estable dentro de Electron.
        # DirectShow (CAP_DSHOW) se colgaba al abrir DroidCam desde el proceso hijo.
        cap = cv2.VideoCapture(args.camera)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)
        if not cap.isOpened():
            emit({"type": "error", "message": f"No se pudo abrir la camara {args.camera}"})
            return
        emit({"type": "init", "stage": "camera_opened"})

        emit({"type": "init", "stage": "loading_models"})
        clf, le = cargar_mlp()
        lstm_sesion, lstm_entrada, lstm_le = cargar_lstm()

        banda_h = int(120 * args.subtitle_scale)
        emit({"type": "init", "stage": "loading_landmarker"})
        landmarker = crear_landmarker()
        emit({"type": "init", "stage": "opening_virtualcam"})
        with landmarker, \
             pyvirtualcam.Camera(width=ANCHO, height=ALTO + banda_h, fps=FPS,
                                 fmt=PixelFormat.BGR) as cam:

            emit({"type": "ready", "virtual_camera": cam.device,
                  "width": ANCHO, "height": ALTO + banda_h})

            ts_ms = 0
            buffer = []
            texto_anterior = ""
            tiempo_ultimo_cambio = 0.0
            t_fps = time.time()
            fps_real = 0.0

            while not _stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    emit({"type": "error", "message": "Fallo al leer frame de la camara"})
                    break

                frame = cv2.resize(frame, (ANCHO, ALTO))
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                ts_ms += int(1000 / FPS)
                resultado = landmarker.detect_for_video(mp_image, ts_ms)
                dibujar_landmarks(frame, resultado)

                tiempo_actual = time.time()
                texto = texto_anterior  # solo la letra limpia, sin prefijos

                if resultado.hand_landmarks:
                    es_izquierda = resultado.handedness[0][0].category_name == "Left"
                    landmarks = normalizar(resultado.hand_landmarks[0], es_izquierda)
                    buffer.append(landmarks)
                    if len(buffer) > BUFFER_SIZE:
                        buffer.pop(0)

                    if tiempo_actual - tiempo_ultimo_cambio >= MIN_TIEMPO_ENTRE_CAMBIOS:
                        letra_lstm = clasificar_secuencia(buffer, lstm_sesion, lstm_entrada, lstm_le)
                        if letra_lstm:
                            letra_nueva, es_movimiento = letra_lstm, True
                        else:
                            letra_nueva, _ = clasificar_signo(resultado, clf, le)
                            es_movimiento = False

                        if letra_nueva and letra_nueva != texto_anterior:
                            texto = letra_nueva
                            texto_anterior = letra_nueva
                            tiempo_ultimo_cambio = tiempo_actual
                            # is_movement va a la app por JSON, pero NO se quema en el vídeo
                            emit({"type": "status", "letter": letra_nueva,
                                  "is_movement": es_movimiento, "fps": round(fps_real, 1)})
                else:
                    buffer = []
                    if texto_anterior:
                        texto = ""
                        texto_anterior = ""
                        emit({"type": "status", "letter": "", "is_movement": False,
                              "fps": round(fps_real, 1)})

                frame_out = dibujar_subtitulo(frame, texto, args.subtitle_scale,
                                              args.subtitle_position)
                cam.send(frame_out)
                cam.sleep_until_next_frame()

                # FPS real suavizado
                ahora = time.time()
                dt = ahora - t_fps
                t_fps = ahora
                if dt > 0:
                    fps_real = 0.9 * fps_real + 0.1 * (1.0 / dt)

        cap.release()
        emit({"type": "stopped"})

    except Exception as e:  # noqa: BLE001 - reportamos cualquier fallo a Electron
        emit({"type": "error", "message": str(e)})
        raise


if __name__ == "__main__":
    main()
