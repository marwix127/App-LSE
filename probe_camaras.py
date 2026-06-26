"""Sondea los indices 0-4 con el backend por defecto (MSMF) y reporta cuales
abren y si dan imagen real (no negra). Sirve para saber que indice usar."""

import cv2
import numpy as np

for i in range(5):
    cap = cv2.VideoCapture(i)
    if not cap.isOpened():
        print(f"indice {i}: NO abre")
        cap.release()
        continue
    ok, frame = cap.read()
    if not ok or frame is None:
        print(f"indice {i}: abre pero NO da frame")
    else:
        brillo = float(np.mean(frame))
        estado = "NEGRA" if brillo < 5 else "con imagen"
        print(f"indice {i}: OK {frame.shape[1]}x{frame.shape[0]} brillo={brillo:.1f} ({estado})")
    cap.release()
