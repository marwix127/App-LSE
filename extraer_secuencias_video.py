import os
import pickle
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
from landmarks_utils import normalizar

MODEL_PATH = r"F:\App LSE\hand_landmarker.task"
DATASET_DIR = r"F:\Downloads\SigNN Video Data"
OUTPUT_PKL = r"F:\App LSE\lstm_sequences.pkl"
LETRAS = ["J", "Z"]
FRAMES_POR_SECUENCIA = 30


def remuestrear(secuencia, n=FRAMES_POR_SECUENCIA):
    """Remuestrea una secuencia de longitud variable a exactamente n frames."""
    seq = np.array(secuencia)
    if len(seq) == n:
        return seq
    indices = np.linspace(0, len(seq) - 1, n).astype(int)
    return seq[indices]


def extraer_secuencia_video(landmarker, ruta, ts_base):
    cap = cv2.VideoCapture(ruta)
    secuencia = []
    ts = ts_base
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        ts += 50
        resultado = landmarker.detect_for_video(mp_img, ts)
        if resultado.hand_landmarks:
            es_izquierda = resultado.handedness[0][0].category_name == "Left"
            secuencia.append(normalizar(resultado.hand_landmarks[0], es_izquierda))
    cap.release()
    return secuencia, ts


def main():
    if os.path.exists(OUTPUT_PKL):
        with open(OUTPUT_PKL, "rb") as f:
            secuencias = pickle.load(f)
        print(f"Cargado existente — J: {len(secuencias['J'])}, Z: {len(secuencias['Z'])}")
    else:
        secuencias = {"J": [], "Z": []}

    opts = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    ts = 0
    with HandLandmarker.create_from_options(opts) as landmarker:
        for letra in LETRAS:
            carpeta = os.path.join(DATASET_DIR, letra)
            videos = [v for v in os.listdir(carpeta) if v.lower().endswith(".avi")]
            print(f"\n{letra}: {len(videos)} videos")

            ok_count, saltados = 0, 0
            for i, nombre in enumerate(videos):
                ruta = os.path.join(carpeta, nombre)
                secuencia, ts = extraer_secuencia_video(landmarker, ruta, ts)

                if len(secuencia) < 10:
                    saltados += 1
                    continue

                secuencias[letra].append(remuestrear(secuencia))
                ok_count += 1

                if (i + 1) % 50 == 0:
                    print(f"  {i+1}/{len(videos)} procesados...")

            print(f"  -> {ok_count} secuencias anadidas, {saltados} saltadas (pocas detecciones)")

    with open(OUTPUT_PKL, "wb") as f:
        pickle.dump(secuencias, f)

    print(f"\nGuardado en {OUTPUT_PKL}")
    print(f"Total — J: {len(secuencias['J'])}, Z: {len(secuencias['Z'])}")


if __name__ == "__main__":
    main()
