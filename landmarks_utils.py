# Si se cambia normalizar() hay que volver a extraer los datos y reentrenar MLP y LSTM.


def normalizar(landmarks_raw, es_izquierda=False):
    # relativo a la muñeca, escalado a [-1, 1] y con X espejada en la mano izquierda
    base_x, base_y, base_z = landmarks_raw[0].x, landmarks_raw[0].y, landmarks_raw[0].z
    coords = []
    for lm in landmarks_raw:
        x = lm.x - base_x
        coords += [-x if es_izquierda else x, lm.y - base_y, lm.z - base_z]
    max_val = max(abs(v) for v in coords) or 1.0
    return [v / max_val for v in coords]
