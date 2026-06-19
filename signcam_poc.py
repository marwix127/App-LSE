import pickle
import cv2
import numpy as np
import pyvirtualcam
from pyvirtualcam import PixelFormat
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
import tensorflow as tf
from landmarks_utils import normalizar

MODEL_PATH = r"F:\App LSE\hand_landmarker.task"
MLP_PATH = r"F:\App LSE\mlp_signos.pkl"
LSTM_PATH = r"F:\App LSE\lstm_signos.h5"
LSTM_ENCODER_PATH = r"F:\App LSE\lstm_encoder.pkl"
ANCHO, ALTO, FPS = 1280, 720, 30
BANDA_H = 120
BUFFER_SIZE = 30


def crear_landmarker():
    opts = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return HandLandmarker.create_from_options(opts)


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


def cargar_mlp():
    with open(MLP_PATH, "rb") as f:
        datos = pickle.load(f)
    return datos["model"], datos["encoder"]


def cargar_lstm():
    model = tf.keras.models.load_model(LSTM_PATH)
    with open(LSTM_ENCODER_PATH, "rb") as f:
        le = pickle.load(f)
    return model, le


def clasificar_signo(resultado, clf, le):
    if not resultado.hand_landmarks:
        return "", 0.0
    es_izquierda = resultado.handedness[0][0].category_name == "Left"
    landmarks = normalizar(resultado.hand_landmarks[0], es_izquierda)
    pred_probs = clf.predict_proba([landmarks])[0]
    clase_idx = np.argmax(pred_probs)
    confianza = pred_probs[clase_idx]
    if confianza < 0.95:
        return "", confianza
    return le.inverse_transform([clase_idx])[0], confianza


def hay_movimiento(buffer):
    if len(buffer) < BUFFER_SIZE:
        return False
    seq = np.array(buffer[-BUFFER_SIZE:])
    # std a lo largo del tiempo (eje 0) por cada coordenada, promediado.
    # Mano quieta -> cercano a 0; movimiento (J/Z) -> alto.
    movimiento = np.mean(np.std(seq, axis=0))
    return movimiento > 0.03


def clasificar_secuencia(buffer, lstm_model, lstm_le):
    if len(buffer) < BUFFER_SIZE or not hay_movimiento(buffer):
        return ""
    seq = np.array(buffer[-BUFFER_SIZE:])
    seq = np.expand_dims(seq, axis=0)
    pred = lstm_model.predict(seq, verbose=0)
    clase = np.argmax(pred)
    confianza = pred[0, clase]
    if confianza < 0.95:
        return ""
    return lstm_le.inverse_transform([clase])[0]


def dibujar_subtitulo(frame, texto):
    banda = np.zeros((BANDA_H, frame.shape[1], 3), dtype=np.uint8)
    if texto:
        cv2.putText(banda, texto, (40, 85), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (255, 255, 255), 4)
    return np.vstack([frame, banda])


def main():
    clf, le = cargar_mlp()
    lstm_model, lstm_le = cargar_lstm()

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)

    with crear_landmarker() as landmarker, \
         pyvirtualcam.Camera(width=ANCHO, height=ALTO + BANDA_H, fps=FPS,
                             fmt=PixelFormat.BGR) as cam:

        print(f"Camara virtual: {cam.device}")
        print("Presiona Q para salir.")
        ts_ms = 0
        buffer = []
        texto_anterior = ""
        tiempo_ultimo_cambio = 0
        MIN_TIEMPO_ENTRE_CAMBIOS = 0.5

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.resize(frame, (ANCHO, ALTO))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            ts_ms += int(1000 / FPS)
            resultado = landmarker.detect_for_video(mp_image, ts_ms)

            dibujar_landmarks(frame, resultado)

            tiempo_actual = ts_ms / 1000.0
            texto = texto_anterior

            if resultado.hand_landmarks:
                es_izquierda = resultado.handedness[0][0].category_name == "Left"
                landmarks = normalizar(resultado.hand_landmarks[0], es_izquierda)

                buffer.append(landmarks)
                if len(buffer) > BUFFER_SIZE:
                    buffer.pop(0)

                if tiempo_actual - tiempo_ultimo_cambio >= MIN_TIEMPO_ENTRE_CAMBIOS:
                    texto_lstm = clasificar_secuencia(buffer, lstm_model, lstm_le)
                    if texto_lstm:
                        texto_nuevo = f"[MOVIMIENTO] {texto_lstm}"
                    else:
                        texto_nuevo, conf = clasificar_signo(resultado, clf, le)

                    if texto_nuevo and texto_nuevo != texto_anterior:
                        texto = texto_nuevo
                        texto_anterior = texto_nuevo
                        tiempo_ultimo_cambio = tiempo_actual
            else:
                buffer = []
                if texto_anterior:
                    texto = ""
                    texto_anterior = ""

            frame_out = dibujar_subtitulo(frame, texto)

            cam.send(frame_out)
            cam.sleep_until_next_frame()

            cv2.imshow("SignCam Preview", frame_out)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
