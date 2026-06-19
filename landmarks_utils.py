"""Utilidades compartidas para procesar landmarks de MediaPipe.

IMPORTANTE: si cambias `normalizar`, hay que re-extraer los datasets y
reentrenar todos los modelos (MLP y LSTM), porque deben usar exactamente
la misma normalización en entrenamiento e inferencia.
"""


def normalizar(landmarks_raw, es_izquierda=False):
    """Normaliza una mano de MediaPipe a 63 valores invariantes a posición,
    escala y lado de la mano.

    - Resta la muñeca (punto 0) para quitar la posición en el frame.
    - Divide por el valor absoluto máximo para quitar la escala (distancia/zoom).
    - Espeja la coordenada X para la mano izquierda, así ambas manos se tratan igual.
    """
    base_x, base_y, base_z = landmarks_raw[0].x, landmarks_raw[0].y, landmarks_raw[0].z
    coords = []
    for lm in landmarks_raw:
        x = lm.x - base_x
        coords += [-x if es_izquierda else x, lm.y - base_y, lm.z - base_z]
    max_val = max(abs(v) for v in coords) or 1.0
    return [v / max_val for v in coords]
