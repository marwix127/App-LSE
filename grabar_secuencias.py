import os
import pickle
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
from landmarks_utils import normalizar

MODEL_PATH = r"F:\App LSE\hand_landmarker.task"
OUTPUT_PKL = r"F:\App LSE\lstm_sequences.pkl"
FRAMES_POR_SECUENCIA = 30


def main():
    print("Letras con movimiento: J, Z")
    letra = input("¿Qué letra quieres grabar? (J/Z): ").strip().upper()
    if letra not in ["J", "Z"]:
        print("Letra inválida")
        return

    num_secuencias = int(input(f"¿Cuántas secuencias de {letra} quieres grabar? "))

    if os.path.exists(OUTPUT_PKL):
        with open(OUTPUT_PKL, "rb") as f:
            secuencias = pickle.load(f)
    else:
        secuencias = {"J": [], "Z": []}

    opts = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    cap = cv2.VideoCapture(0)
    ts_ms = 0

    with HandLandmarker.create_from_options(opts) as landmarker:
        for i in range(num_secuencias):
            secuencia = []
            grabando = False
            frames_capturados = 0

            print(f"\nSecuencia {i+1}/{num_secuencias} — Pulsa ESPACIO cuando estés listo para grabar")

            while True:
                ok, frame = cap.read()
                if not ok:
                    break

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                ts_ms += 33
                resultado = landmarker.detect_for_video(mp_img, ts_ms)

                detectada = bool(resultado.hand_landmarks)

                estado = f"Grabando: {frames_capturados}/{FRAMES_POR_SECUENCIA}" if grabando else "Pulsa ESPACIO"
                color = (0, 200, 0) if detectada else (0, 0, 200)
                cv2.putText(frame, f"{letra} - {estado}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                cv2.imshow("Grabacion secuencias", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == 32:
                    grabando = True
                if key == ord("q"):
                    break

                if grabando and detectada:
                    es_izquierda = resultado.handedness[0][0].category_name == "Left"
                    landmarks = normalizar(resultado.hand_landmarks[0], es_izquierda)
                    secuencia.append(landmarks)
                    frames_capturados += 1

                    if frames_capturados >= FRAMES_POR_SECUENCIA:
                        break

            if len(secuencia) == FRAMES_POR_SECUENCIA:
                secuencias[letra].append(np.array(secuencia))
                print(f"  ✓ Secuencia {i+1} guardada ({len(secuencia)} frames)")
            else:
                print(f"  ✗ Secuencia {i+1} incompleta ({len(secuencia)} frames)")

    cap.release()
    cv2.destroyAllWindows()

    with open(OUTPUT_PKL, "wb") as f:
        pickle.dump(secuencias, f)

    print(f"\nSecuencias guardadas en {OUTPUT_PKL}")
    print(f"J: {len(secuencias['J'])}, Z: {len(secuencias['Z'])}")


if __name__ == "__main__":
    main()
