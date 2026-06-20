"""Lista las cámaras de entrada con su nombre, en el orden de índice de OpenCV.

Lo usa Electron para poblar el selector de cámara. Salida: JSON por stdout.
Usa pygrabber (DirectShow), cuyo orden coincide con cv2.VideoCapture(i, CAP_DSHOW).
Se excluye la cámara virtual de salida para no crear un bucle.
"""

import sys
import json

EXCLUIR = ("OBS Virtual Camera", "SignCam")


def main():
    try:
        from pygrabber.dshow_graph import FilterGraph
        nombres = FilterGraph().get_input_devices()
    except Exception as e:  # noqa: BLE001
        sys.stdout.write(json.dumps({"devices": [], "error": str(e)}))
        return

    devices = [
        {"index": i, "name": nombre}
        for i, nombre in enumerate(nombres)
        if not any(x in nombre for x in EXCLUIR)
    ]
    sys.stdout.write(json.dumps({"devices": devices}))


if __name__ == "__main__":
    main()
