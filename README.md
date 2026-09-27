# SignCam

Cámara virtual que reconoce el alfabeto dactilológico con la webcam y lo muestra como subtítulo en el vídeo. La cámara virtual se puede usar en Teams, Meet, Zoom, etc.

Reconoce las 26 letras. J y Z, que llevan movimiento, se reconocen con un LSTM a partir de los últimos 30 frames; el resto con un MLP frame a frame. Los modelos están entrenados con el alfabeto ASL y grabaciones propias, todavía no con LSE.

## Funcionamiento

```
Webcam -> signcam_sidecar.py -> cámara virtual -> Teams / Meet / Zoom
               |                      |
               | JSON por stdout      +-> preview en la app
               v
          Electron -> React
```

- `signcam_sidecar.py` abre la webcam, detecta la mano con MediaPipe, clasifica la letra, pinta el subtítulo y manda el frame a la cámara virtual.
- `app/` es la interfaz (Electron + React). Arranca y para el sidecar, muestra la letra y los fps y permite elegir cámara, tamaño y posición del subtítulo.

## Requisitos

- Windows 10/11
- Python 3.12 (mediapipe no funciona en 3.14)
- Node.js 18 o superior
- OBS Studio instalado, para el driver de cámara virtual. No hace falta tenerlo abierto.

## Instalación

```powershell
git clone https://github.com/marwix127/App-LSE.git
cd App-LSE

py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# modelo de manos de MediaPipe
git restore --source=c2385bf -- hand_landmarker.task

cd app
npm install
```

El modelo de MediaPipe también se puede descargar de https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task y dejarlo en la raíz.

## Uso

Desde `app/`:

```powershell
npm run dev
```

Pulsar "Iniciar cámara" y, cuando ponga "En marcha", elegir "OBS Virtual Camera" en la aplicación de videollamada. Los ajustes se aplican al volver a iniciar la cámara.

### Versión empaquetada

```powershell
# desde la raíz
venv\Scripts\pyinstaller signcam_sidecar.spec

# desde app/
npm run prod
```

`npm run prod` usa `dist\signcam_sidecar\signcam_sidecar.exe` en vez de Python.

### Sidecar sin la app

```powershell
python signcam_sidecar.py --list-cameras
python -u signcam_sidecar.py --camera 0 --subtitle-scale 1.0 --subtitle-position bottom
```

Se para escribiendo `stop`. `--subtitle-position` puede ser `top` o `bottom`. Para saber qué índice es cada cámara: `python probe_camaras.py`.

## Entrenamiento

Los modelos entrenados ya están en el repositorio. Para volver a entrenarlos:

| Script | Qué hace |
|---|---|
| `extraer_landmarks.py` | landmarks del dataset ASL Alphabet -> `landmarks_dataset.csv` |
| `grabar_muestras.py` | graba muestras propias con la webcam -> `muestras_propias.csv` |
| `entrenar_mlp.py` | entrena el MLP -> `mlp_signos.pkl` |
| `extraer_secuencias_video.py` | secuencias de J y Z del dataset SigNN -> `lstm_sequences.pkl` |
| `grabar_secuencias.py` | graba secuencias propias de J y Z -> `lstm_sequences.pkl` |
| `entrenar_lstm.py` | entrena el LSTM -> `lstm_signos.h5`, `lstm_encoder.pkl` |
| `convertir_lstm_onnx.py` | convierte el LSTM a ONNX -> `lstm_signos.onnx` |

- Los datasets (ASL Alphabet y SigNN Video Data) son de Kaggle. La ruta se cambia en `DATASET_DIR` en cada script.
- El LSTM necesita TensorFlow: `pip install -r requirements-entrenamiento.txt`.
- Los scripts de grabación usan la cámara 0. ESPACIO graba, Q salta.
- Los scripts de grabación y `extraer_secuencias_video.py` añaden a los datos existentes, no los sustituyen. Ejecutar dos veces la extracción duplica las secuencias.
- `muestras_propias.csv` y `lstm_sequences.pkl` tienen grabaciones propias que no se pueden regenerar.
- Si se cambia `landmarks_utils.normalizar` hay que volver a extraer los datos y reentrenar los dos modelos.
- scikit-learn está fijado a 1.8.0 porque los modelos se guardan con pickle.

## Problemas conocidos

- Si la cámara se queda ocupada después de cerrar la app, puede haber un sidecar colgado: `taskkill /F /IM python.exe` (o `signcam_sidecar.exe` en la versión empaquetada).
- La webcam solo la puede usar una aplicación a la vez; si otra la tiene abierta, el sidecar no arranca.
- `UnicodeEncodeError` en consola: `$env:PYTHONUTF8 = "1"`.
- Los comandos de npm se ejecutan desde `app/`.

## Pendiente

- Solo reconoce letras sueltas y la primera mano detectada.
- La cámara se elige por índice de OpenCV.
- Falta un instalador (electron-builder) y que el driver de cámara virtual no dependa de OBS.
