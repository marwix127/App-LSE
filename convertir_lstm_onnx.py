"""Convierte el LSTM entrenado (Keras .h5) a ONNX (uso unico, en desarrollo).

El sidecar de produccion usa onnxruntime (ligero) en vez de TensorFlow, lo que
hace el empaquetado con PyInstaller mucho mas pequeno y fiable.

Tras convertir, verifica que ONNX y Keras dan la misma prediccion.
"""

import os
import sys
import subprocess
import tempfile
import numpy as np
import tensorflow as tf
import onnxruntime as ort

H5_PATH = r"F:\App LSE\lstm_signos.h5"
ONNX_PATH = r"F:\App LSE\lstm_signos.onnx"
FRAMES, FEATURES = 30, 63


def main():
    print("Cargando modelo Keras...")
    model = tf.keras.models.load_model(H5_PATH)

    # Keras 3 + tf2onnx no convierten bien directamente: exportamos a SavedModel
    # y convertimos eso con la CLI de tf2onnx (vía robusta).
    saved_dir = os.path.join(tempfile.gettempdir(), "signcam_lstm_savedmodel")
    print(f"Exportando SavedModel a {saved_dir}...")
    model.export(saved_dir)

    print("Convirtiendo SavedModel a ONNX...")
    subprocess.run(
        [sys.executable, "-m", "tf2onnx.convert", "--saved-model", saved_dir,
         "--output", ONNX_PATH, "--opset", "15"],
        check=True,
    )
    print(f"Guardado en {ONNX_PATH}")

    print("Verificando equivalencia Keras vs ONNX...")
    muestra = np.random.rand(1, FRAMES, FEATURES).astype(np.float32)
    pred_keras = model.predict(muestra, verbose=0)

    sess = ort.InferenceSession(ONNX_PATH)
    entrada = sess.get_inputs()[0].name
    pred_onnx = sess.run(None, {entrada: muestra})[0]

    diff = np.max(np.abs(pred_keras - pred_onnx))
    print(f"Keras: {pred_keras}")
    print(f"ONNX:  {pred_onnx}")
    print(f"Diferencia maxima: {diff:.2e}")
    print("OK - equivalentes" if diff < 1e-4 else "ATENCION: difieren demasiado")


if __name__ == "__main__":
    main()
