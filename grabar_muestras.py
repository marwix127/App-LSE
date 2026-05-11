import os
import csv
import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

MODEL_PATH = r"F:\App LSE\hand_landmarker.task"
OUTPUT_CSV = r"F:\App LSE\muestras_propias.csv"
LETRAS_OBJETIVO = ["F"]
MUESTRAS_POR_LETRA = 50

COLUMNAS = ["letra"] + [f"{eje}{i}" for i in range(21) for eje in ("x", "y", "z")]


def normalizar(landmarks_raw, es_izquierda=False):
    base_x, base_y, base_z = landmarks_raw[0].x, landmarks_raw[0].y, landmarks_raw[0].z
    coords = []
    for lm in landmarks_raw:
        x = lm.x - base_x
        coords += [-x if es_izquierda else x, lm.y - base_y, lm.z - base_z]
    max_val = max(abs(v) for v in coords) or 1.0
    return [v / max_val for v in coords]


def main():
    opts = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    ya_existe = os.path.exists(OUTPUT_CSV)
    csv_file = open(OUTPUT_CSV, "a", newline="")
    writer = csv.writer(csv_file)
    if not ya_existe:
        writer.writerow(COLUMNAS)

    cap = cv2.VideoCapture(0)
    ts_ms = 0

    with HandLandmarker.create_from_options(opts) as landmarker:
        for letra in LETRAS_OBJETIVO:
            guardadas = 0
            grabando = False

            print(f"\nLetra: {letra} — Pon la mano en posición y pulsa ESPACIO para grabar {MUESTRAS_POR_LETRA} muestras. Q para saltar.")

            while guardadas < MUESTRAS_POR_LETRA:
                ok, frame = cap.read()
                if not ok:
                    break

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                ts_ms += 33
                resultado = landmarker.detect_for_video(mp_img, ts_ms)

                detectada = bool(resultado.hand_landmarks)

                estado = f"Grabando: {guardadas}/{MUESTRAS_POR_LETRA}" if grabando else "Pulsa ESPACIO para empezar"
                color = (0, 200, 0) if detectada else (0, 0, 200)
                cv2.putText(frame, f"Letra: {letra}  |  {estado}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                cv2.putText(frame, "Mano detectada" if detectada else "Sin mano", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                cv2.imshow("Grabacion", frame)

                key = cv2.waitKey(1) & 0xFF
                if key != 0xFF:
                    print(f"Tecla recibida: {key}")
                if key == ord("q"):
                    break
                if key == 32:
                    grabando = True
                    print("ESPACIO detectado")

                if grabando and detectada:
                    es_izquierda = resultado.handedness[0][0].category_name == "Left"
                    landmarks = normalizar(resultado.hand_landmarks[0], es_izquierda)
                    writer.writerow([letra] + landmarks)
                    guardadas += 1
                    grabando = False
                    print(f"  Muestra {guardadas}/{MUESTRAS_POR_LETRA} — suelta y vuelve a hacer el signo, luego ESPACIO")

            print(f"  → {guardadas} muestras guardadas para {letra}")

    cap.release()
    cv2.destroyAllWindows()
    csv_file.close()
    print(f"\nMuestras guardadas en {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
