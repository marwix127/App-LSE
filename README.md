# SignCam

SignCam es una cámara virtual que subtitula en tiempo real el alfabeto dactilológico. Captura la webcam, detecta las manos con MediaPipe, reconoce la letra que se está signando y la escribe como subtítulo sobre el vídeo. El resultado se publica como una cámara virtual, de modo que se puede elegir en Teams, Google Meet, Zoom o cualquier otra aplicación de videollamada.

Reconoce las 26 letras del alfabeto: las estáticas frame a frame y las dos que llevan movimiento, J y Z, a partir de una secuencia de frames.

> Los modelos actuales se han entrenado con el alfabeto **ASL** (lengua de signos americana) y con grabaciones propias. El objetivo del proyecto es llegar a LSE/LSC, pero de momento no están entrenados con ellas.

## Cómo funciona

```
Webcam real --> Sidecar Python --------------> Cámara virtual --> Teams / Meet / Zoom
                (MediaPipe + MLP/LSTM)              |
                      |                             +--> Preview en la app
                      | eventos JSON (letra, fps)
                      v
                Electron (main) --IPC--> Interfaz React
```

- **Sidecar Python** (`signcam_sidecar.py`). Es el pipeline de reconocimiento y el único proceso que abre la webcam física. Por cada frame hace lo siguiente:
  1. Extrae 21 landmarks de la mano.
  2. Los normaliza: quita la posición y la escala y espeja la mano izquierda.
  3. Clasifica la letra.
  4. Dibuja el subtítulo y envía el frame a la cámara virtual.

  Se comunica con Electron por stdin/stdout: los ajustes llegan como argumentos y los eventos salen en JSON, uno por línea.
- **Clasificación híbrida.** Un MLP (scikit-learn) clasifica las letras estáticas a partir de un solo frame. Un LSTM (exportado a ONNX) clasifica J y Z a partir de los últimos 30 frames, pero solo cuando detecta que la mano se está moviendo.
- **App de escritorio** (`app/`, Electron + React). Arranca y detiene el sidecar y muestra la letra detectada y los fps. Tiene un panel de ajustes para elegir la cámara de entrada y el tamaño y la posición del subtítulo. El preview lee la cámara *virtual*, así que muestra exactamente lo que verán los demás en la videollamada.

## Requisitos

- Windows 10 u 11.
- **Python 3.12.** No sirven versiones más nuevas, porque mediapipe no tiene paquetes para 3.14.
- **Node.js 18 o superior** (para la app de escritorio).
- **OBS Studio**, que proporciona el driver de cámara virtual. Basta con instalarlo una vez; no hace falta tenerlo abierto mientras se usa SignCam.

## Instalación

```powershell
git clone https://github.com/marwix127/App-LSE.git
cd App-LSE

# Entorno de Python
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Modelo de detección de manos de MediaPipe (no se versiona)
git restore --source=c2385bf -- hand_landmarker.task

# App de escritorio
cd app
npm install
```

El comando `git restore` recupera del historial exactamente el mismo modelo con el que se generaron los datos de entrenamiento. Si prefieres descargarlo, está en https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task y hay que guardarlo en la raíz del proyecto.

## Uso

### Arrancar la app (desarrollo)

Desde la carpeta `app/`:

```powershell
npm run dev
```

Se abren Vite y Electron. La app lanza el sidecar con el Python de `venv/`. Pulsa **Iniciar cámara**, espera a que el estado pase a "En marcha" y elige la cámara virtual (aparece como "OBS Virtual Camera") en tu aplicación de videollamada.

Los ajustes se guardan entre sesiones. Solo se aplican al iniciar la cámara, así que para cambiarlos hay que detenerla antes.

### Modo producción (sin Python instalado)

Primero hay que empaquetar el sidecar como ejecutable, desde la raíz del proyecto:

```powershell
venv\Scripts\pyinstaller signcam_sidecar.spec
```

Esto genera `dist\signcam_sidecar\signcam_sidecar.exe`. Después, desde `app/`:

```powershell
npm run prod
```

Este comando compila la interfaz y abre Electron usando el `.exe` en lugar del venv.

### Ejecutar el sidecar sin la app

Es útil para depurar el pipeline. Desde la raíz, con el venv activado:

```powershell
python signcam_sidecar.py --list-cameras
python -u signcam_sidecar.py --camera 0 --subtitle-scale 1.0 --subtitle-position bottom
```

El segundo comando se detiene escribiendo `stop` y pulsando Enter.

| Argumento | Valores | Por defecto |
|---|---|---|
| `--camera` | índice de la cámara en OpenCV | `0` |
| `--subtitle-scale` | `0.5`, `1.0`, `1.5`... | `1.0` |
| `--subtitle-position` | `top`, `bottom` | `bottom` |

Si no sabes qué índice corresponde a cada cámara, `python probe_camaras.py` prueba los índices 0 a 4. Para cada uno indica si abre y si da imagen o un frame negro.

## Entrenar los modelos

Los modelos entrenados ya vienen en el repositorio (`mlp_signos.pkl`, `lstm_signos.onnx` y `lstm_encoder.pkl`). Solo hace falta reentrenarlos si quieres añadir datos o cambiar el modelo.

| Paso | Script | Genera |
|---|---|---|
| Extraer landmarks del dataset ASL Alphabet | `extraer_landmarks.py` | `landmarks_dataset.csv` |
| Grabar muestras propias de letras estáticas | `grabar_muestras.py` | `muestras_propias.csv` |
| Entrenar el MLP | `entrenar_mlp.py` | `mlp_signos.pkl` |
| Extraer secuencias de J y Z del dataset SigNN | `extraer_secuencias_video.py` | `lstm_sequences.pkl` |
| Grabar secuencias propias de J y Z | `grabar_secuencias.py` | `lstm_sequences.pkl` |
| Entrenar el LSTM | `entrenar_lstm.py` | `lstm_signos.h5`, `lstm_encoder.pkl` |
| Convertir el LSTM a ONNX | `convertir_lstm_onnx.py` | `lstm_signos.onnx` |

Notas:

- **Datasets externos** (Kaggle):
  - *ASL Alphabet*: fotos de cada letra, organizadas en carpetas `A` a `Z`.
  - *SigNN Video Data*: vídeos `.avi` organizados en carpetas `J` y `Z`.

  Su ubicación está en la constante `DATASET_DIR` de cada script de extracción; ajústala a donde los hayas descargado.
- **El LSTM necesita TensorFlow.** Solo se usa para entrenar y convertir; la app no lo necesita en ejecución. Para instalarlo: `pip install -r requirements-entrenamiento.txt`.
- **Scripts de grabación.** Usan la cámara 0. Colocas la mano y pulsas `ESPACIO` para grabar; `Q` salta la letra o la secuencia actual. Los datos nuevos se añaden a los que ya existen.
- **`extraer_secuencias_video.py` también añade** a `lstm_sequences.pkl`, no lo sobrescribe. Si lo ejecutas dos veces sobre el mismo dataset, las secuencias quedan duplicadas.
- **Datos no regenerables.** `muestras_propias.csv` y `lstm_sequences.pkl` contienen grabaciones propias que no se pueden regenerar. Conviene hacer una copia antes de experimentar con ellos.
- **La normalización es común a todo.** Entrenamiento e inferencia comparten la misma función (`landmarks_utils.normalizar`). Si la cambias, hay que volver a extraer todos los datos y reentrenar los dos modelos.
- **La versión de scikit-learn está fijada** (`1.8.0`), porque los modelos se guardan con pickle. Si la cambias, reentrena el MLP.

## Estructura del proyecto

```
signcam_sidecar.py        Pipeline de reconocimiento usado por la app
signcam_sidecar.spec      Receta de PyInstaller para empaquetar el sidecar
landmarks_utils.py        Normalización de landmarks (compartida por todos los scripts)
probe_camaras.py          Diagnóstico de índices de cámara
signcam_poc.py            Prueba de concepto original (ventana OpenCV, usa TensorFlow)
extraer_*.py, grabar_*.py, entrenar_*.py, convertir_lstm_onnx.py
                          Pipeline de datos y entrenamiento
app/electron/             Proceso principal de Electron y preload
app/src/                  Interfaz React
```

## Solución de problemas

- **La cámara no se libera, o la app no vuelve a arrancar.** Puede haberse quedado colgado un sidecar anterior. Ciérralo con `taskkill /F /IM python.exe` (en desarrollo) o `taskkill /F /IM signcam_sidecar.exe` (en producción).
- **El preview sale en negro o la cámara aparece como "en uso".** En Windows, la webcam física solo puede usarla un proceso a la vez. Cierra cualquier otra aplicación que la esté usando.
- **La cámara elegida no es la que se abre.** Comprueba los índices con `python probe_camaras.py`.
- **`UnicodeEncodeError` al ejecutar scripts en la consola.** Activa UTF-8 con `$env:PYTHONUTF8 = "1"` (PowerShell).
- **`npm` no encuentra `package.json`.** Los comandos de npm se ejecutan desde la carpeta `app/`, no desde la raíz.

## Estado y limitaciones

- Reconoce letras sueltas del alfabeto, no palabras ni frases.
- Solo clasifica la primera mano que detecta.
- La cámara de entrada se elige por índice de OpenCV.
- Pendiente:
  - un instalador (electron-builder) que incluya el sidecar empaquetado;
  - registrar el driver de cámara virtual sin necesidad de instalar OBS Studio.
