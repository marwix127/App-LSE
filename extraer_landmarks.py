import csv
import os
import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

DATASET_DIR = r"F:\Downloads\asl_alphabet_train\asl_alphabet_train"
LETRAS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
OUTPUT_CSV = "landmarks_dataset.csv"
MODEL_PATH = r"F:\App LSE\hand_landmarker.task"

COLUMNAS = ["letra"] + [f"{eje}{i}" for i in range(21) for eje in ("x", "y", "z")]


def normalizar(landmarks_raw, es_izquierda=False):
    base_x, base_y, base_z = landmarks_raw[0].x, landmarks_raw[0].y, landmarks_raw[0].z
    coords = []
    for lm in landmarks_raw:
        x = lm.x - base_x
        coords += [-x if es_izquierda else x, lm.y - base_y, lm.z - base_z]
    max_val = max(abs(v) for v in coords) or 1.0
    return [v / max_val for v in coords]


def extraer_landmarks_imagen(landmarker, ruta):
    img = cv2.imread(ruta)
    if img is None:
        return None
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    resultado = landmarker.detect(mp_img)
    if not resultado.hand_landmarks:
        return None
    es_izquierda = resultado.handedness[0][0].category_name == "Left"
    return normalizar(resultado.hand_landmarks[0], es_izquierda)


def main():
    opts = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.IMAGE,
        num_hands=1,
    )

    total = 0
    saltadas = 0

    with HandLandmarker.create_from_options(opts) as landmarker, \
         open(OUTPUT_CSV, "w", newline="") as f:

        writer = csv.writer(f)
        writer.writerow(COLUMNAS)

        for letra in LETRAS:
            carpeta = os.path.join(DATASET_DIR, letra)
            archivos = [a for a in os.listdir(carpeta) if a.lower().endswith((".jpg", ".jpeg", ".png"))]
            print(f"{letra.upper()}: {len(archivos)} imágenes", end="", flush=True)

            ok = 0
            for nombre in archivos:
                ruta = os.path.join(carpeta, nombre)
                landmarks = extraer_landmarks_imagen(landmarker, ruta)
                if landmarks is None:
                    saltadas += 1
                    continue
                writer.writerow([letra] + landmarks)
                ok += 1

            print(f" → {ok} landmarks extraídos")
            total += ok

    print(f"\nTotal: {total} filas guardadas en {OUTPUT_CSV} ({saltadas} imágenes sin mano detectada)")


if __name__ == "__main__":
    main()
