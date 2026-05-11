import pickle
import cv2
import numpy as np
import pyvirtualcam
from pyvirtualcam import PixelFormat
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

MODEL_PATH = r"F:\App LSE\hand_landmarker.task"
MLP_PATH = r"F:\App LSE\mlp_signos.pkl"
ANCHO, ALTO, FPS = 1280, 720, 30
BANDA_H = 120


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


def normalizar(landmarks_raw, es_izquierda=False):
    base_x, base_y, base_z = landmarks_raw[0].x, landmarks_raw[0].y, landmarks_raw[0].z
    coords = []
    for lm in landmarks_raw:
        x = lm.x - base_x
        coords += [-x if es_izquierda else x, lm.y - base_y, lm.z - base_z]
    max_val = max(abs(v) for v in coords) or 1.0
    return [v / max_val for v in coords]


def clasificar_signo(resultado, clf, le):
    if not resultado.hand_landmarks:
        return ""
    es_izquierda = resultado.handedness[0][0].category_name == "Left"
    landmarks = normalizar(resultado.hand_landmarks[0], es_izquierda)
    pred = clf.predict([landmarks])
    return le.inverse_transform(pred)[0]


def dibujar_subtitulo(frame, texto):
    banda = np.zeros((BANDA_H, frame.shape[1], 3), dtype=np.uint8)
    if texto:
        cv2.putText(banda, texto, (40, 85), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (255, 255, 255), 4)
    return np.vstack([frame, banda])


def main():
    clf, le = cargar_mlp()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)

    with crear_landmarker() as landmarker, \
         pyvirtualcam.Camera(width=ANCHO, height=ALTO + BANDA_H, fps=FPS,
                             fmt=PixelFormat.BGR) as cam:

        print(f"Camara virtual: {cam.device}")
        print("Presiona Q para salir.")
        ts_ms = 0

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
            texto = clasificar_signo(resultado, clf, le)
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
