# SignCam — Historial de desarrollo

## Fase 1: PoC — Pipeline completo con clasificador dummy ✅
**Completado: 2026-04-21**

### Objetivo
Validar que el pipeline completo funciona de extremo a extremo:
cámara real → detección de manos → subtítulo → cámara virtual consumible por Teams/Zoom/Meet.

### Decisiones tomadas
- **Stack**: Python 3.12 + MediaPipe Tasks API + OpenCV + pyvirtualcam
- **Sin Electron/Rust por ahora**: empezamos con un script standalone para validar el pipeline antes de añadir UI
- **Driver de cámara virtual**: OBS Virtual Camera (se instala con OBS Studio, no requiere tenerlo abierto)
- **API de MediaPipe**: usamos la nueva Tasks API (`mediapipe.tasks.python.vision.HandLandmarker`) ya que la versión 0.10+ eliminó `mp.solutions`

### Problemas encontrados y soluciones
| Problema | Causa | Solución |
|---|---|---|
| `AttributeError: module 'mediapipe' has no attribute 'solutions'` | MediaPipe 0.10+ eliminó la API legacy | Migrar a `mediapipe.tasks.python.vision.HandLandmarker` |
| `OSError: [WinError 32]` al instalar dependencias | Antivirus bloqueó un DLL recién descargado | Reintentar `pip install` |
| `TypeError: cannot unpack non-iterable Connection object` | En la nueva API, `Connection` usa `.start`/`.end` en vez de unpacking | `for c in conexiones: c.start, c.end` |
| `NORM_RECT without IMAGE_DIMENSIONS` (warning) | Warning informativo de MediaPipe, no afecta al funcionamiento | Ignorar |

### Archivos del proyecto
- `signcam_poc.py` — script principal del PoC
- `requirements.txt` — dependencias Python
- `hand_landmarker.task` — modelo de detección de manos (descargado de Google)
- `CLAUDE.md` — contexto para el agente de desarrollo

### Resultado
Pipeline funcionando: la cámara virtual aparece en Teams/Zoom como "OBS Virtual Camera", dibuja los landmarks de las manos en tiempo real y muestra una banda de subtítulos con texto dummy.

---

## Fase 2: Clasificador MLP — letras A-J ✅
**Completado: 2026-04-22**

### Objetivo
Sustituir el clasificador dummy por un modelo real que detecte las letras A-J del alfabeto.

### Decisiones tomadas
- **Dataset**: ASL Alphabet (grassknoted, Kaggle) — 3000 imágenes reales por letra, carpetas A-J
- **Modelo**: MLP (MLPClassifier de scikit-learn) con capas (128, 64) y activación ReLU
- **Input**: 63 valores (21 landmarks × 3 coordenadas) normalizados
- **Descartado**: dataset `processed_combine_asl_dataset` — tenía landmarks dibujados como imagen, no fotos reales

### Normalización de landmarks
Se aplicaron dos rondas de mejora:
1. **Posición y escala**: restar la muñeca (punto 0) y dividir por el valor máximo → el modelo aprende la forma, no la posición en el frame
2. **Espejado de mano izquierda**: negar la coordenada X para la mano izquierda → el modelo trata ambas manos igual

### Problemas encontrados y soluciones
| Problema | Causa | Solución |
|---|---|---|
| 0 landmarks extraídos del dataset | Las imágenes tenían landmarks ya dibujados, no manos reales | Cambiar al dataset ASL Alphabet con fotos reales |
| Detección dependía de la posición en el frame | Landmarks en coordenadas absolutas | Normalización por posición y escala |
| A solo funcionaba con mano izquierda | Dataset ASL mayoritariamente con mano derecha | Espejado de coordenada X para mano izquierda |
| C y D se confunden entre sí | Formas muy similares en ASL, poca variedad en dataset | Pendiente: añadir grabaciones propias |

### Archivos del proyecto
- `extraer_landmarks.py` — extrae landmarks del dataset y los guarda en CSV normalizado
- `entrenar_mlp.py` — entrena el MLP y guarda el modelo en `mlp_signos.pkl`
- `landmarks_dataset.csv` — 23.735 ejemplos de landmarks normalizados (A-J)
- `mlp_signos.pkl` — modelo MLP entrenado (99% precisión en test)

### Resultado
99% de precisión en test. En uso real funciona bien para la mayoría de letras. C y F siguen dando problemas — se confunden con D principalmente. Siguiente paso: grabar muestras propias para esas letras.

---

## Fase 2b: Mejora con grabaciones propias ✅
**Completado: 2026-04-22**

### Objetivo
Mejorar la detección de letras problemáticas (C, F) añadiendo muestras propias al entrenamiento.

### Proceso
- Script `grabar_muestras.py`: graba landmarks normalizados directamente desde la webcam, 1 muestra por pulsación de ESPACIO para forzar variedad
- 200 muestras de C + 50 muestras de F grabadas y añadidas al entrenamiento
- Combinadas con el dataset ASL en `entrenar_mlp.py` usando dos CSVs

### Resultado
Mejora notable en C y F. El modelo generaliza bien a diferentes posiciones y ángulos de la mano gracias a la combinación de dataset genérico + muestras propias.

## Fase 2c: Data augmentation y alfabeto completo ✅
**Completado: 2026-06-19**

- Extracción ampliada a las 26 letras (A-Z) del dataset ASL
- Data augmentation en `entrenar_mlp.py`: `aumentar_datos()` añade ruido gaussiano (factor 2) para más robustez
- Script `grabar_muestras.py` mejorado: pregunta qué letra(s) grabar al inicio (una o varias separadas por comas)

## Fase 2d: Clasificador LSTM para letras dinámicas (J, Z) ✅
**Completado: 2026-06-19**

### Objetivo
Reconocer letras con movimiento (J, Z) que el MLP no puede captar al ver solo un frame estático.

### Arquitectura híbrida
- **MLP** (scikit-learn): 26 letras estáticas, clasifica frame a frame
- **LSTM** (Keras): J y Z dinámicas, clasifica secuencias de 30 frames
- **Selector por movimiento**: mide variación temporal de los landmarks (`np.std` sobre eje tiempo). Mano quieta (~0.002) → MLP; movimiento (~0.100) → LSTM. Umbral: 0.03

### Datos
- Script `grabar_secuencias.py`: graba secuencias propias desde webcam (30 frames cada una)
- Dataset externo: **SigNN Video Data** (Kaggle) — 316 vídeos J + 396 vídeos Z (.avi)
- Script `extraer_secuencias_video.py`: extrae landmarks de los vídeos, remuestrea a 30 frames con `np.linspace`
- Total: J=336, Z=412 secuencias
- `entrenar_lstm.py`: LSTM(128) → Dropout → Dense(64) → softmax. 100% accuracy en test

### Problemas encontrados y soluciones
| Problema | Causa | Solución |
|---|---|---|
| LSTM se "pegaba" en J/Z y no soltaba | Buffer se llenaba y predecía movimiento sin haberlo | Gate por movimiento temporal + umbral confianza 0.95 |
| `UnicodeEncodeError` al imprimir `→` | Consola Windows usa cp1252 | Caracteres ASCII + `PYTHONUTF8=1` |
| `hay_movimiento` siempre daba true | `np.std(seq)` medía dispersión espacial, no temporal | `np.std(seq, axis=0).mean()` mide variación en el tiempo |
| Buffer se reseteaba durante el movimiento | `hay_cambio_significativo` vaciaba el buffer justo al hacer J/Z | Eliminado el reset, ventana deslizante de 30 frames |

### Archivos nuevos
- `grabar_secuencias.py` — graba secuencias propias de J/Z
- `extraer_secuencias_video.py` — extrae secuencias del dataset de vídeo
- `entrenar_lstm.py` — entrena el LSTM
- `lstm_sequences.pkl` — secuencias de entrenamiento
- `lstm_signos.h5` + `lstm_encoder.pkl` — modelo LSTM entrenado

### Resultado
Sistema híbrido funcionando casi perfecto: detecta las 26 letras estáticas y las 2 dinámicas (J, Z) en tiempo real sobre la cámara virtual.

---

## Fase 3: UI — App Electron + React ✅
**Completado: 2026-06-20**

### Objetivo
Envolver el pipeline de Python en una app de escritorio con interfaz: encender/apagar
la cámara, preview en vivo, letra detectada y panel de ajustes.

### Arquitectura
Electron (UI en JS) + Python (pipeline) comunicados por procesos:

```
Webcam real ──► [Sidecar Python] ──► Cámara virtual "SignCam/OBS"
                 MediaPipe+MLP/LSTM        │          │
                      │ (JSON: letra,fps)  │          └──► Teams/Zoom
                      ▼                    └──► Preview React (getUserMedia)
                [Electron main] ──IPC──► [React UI]
```

- **Sidecar** (`signcam_sidecar.py`): el pipeline de la fase 2, adaptado para recibir
  config por argumentos (`--camera`, `--subtitle-scale`, `--subtitle-position`) y emitir
  eventos JSON por stdout (NDJSON). Sin ventana OpenCV. Se detiene con `stop` por stdin.
- **Electron main** (`app/electron/main.js`): crea la ventana, lanza el sidecar con
  `spawn` (cwd = raíz del proyecto, usa el venv), parsea las líneas JSON y las reenvía
  al renderer. Concede permisos de cámara (`setPermissionRequestHandler` +
  `setPermissionCheckHandler`).
- **Preload** (`app/electron/preload.js`): expone `window.signcam` (start/stop/onEvent)
  de forma segura con contextBridge.
- **React** (`app/src/`): `App.jsx` (estado + control), `Preview.jsx` (vídeo en vivo),
  `Settings.jsx` (ajustes persistidos en localStorage).

### Decisión clave: el preview lee la cámara VIRTUAL, no la real
En Windows solo un proceso abre la webcam física. Python es el dueño de la webcam real;
el preview de React lee la **cámara virtual** con `getUserMedia`. Así se ve exactamente
lo que verán en Teams, sin conflicto de acceso.

### Problemas encontrados y soluciones
| Problema | Causa | Solución |
|---|---|---|
| Preview en negro + "device in use" | El preview hacía un `getUserMedia({video:true})` que abría la webcam real (ocupada por el sidecar; el usuario usa DroidCam) | Quitar ese paso; leer directamente la cámara virtual por nombre |
| Etiquetas de cámaras vacías al enumerar | Sin permiso concedido de forma síncrona | `setPermissionCheckHandler(() => true)` en main |
| Dos subtítulos a la vez | El overlay del frontend duplicaba el subtítulo quemado, que ya aparece en el preview | Eliminado el overlay del frontend |
| "[MOVIMIENTO]" se quemaba en el vídeo | Era una ayuda de desarrollo en el texto del subtítulo | Subtítulo solo con la letra limpia; `is_movement` va solo por JSON a la app |
| npm no encuentra package.json | Se ejecutaba desde la raíz; está en `app/` | Ejecutar `npm run dev` desde `app/` |

### Limitación conocida
La selección de cámara es por **índice numérico** (0-4) porque OpenCV usa índices, que no
se corresponden con los `deviceId` del navegador. Pendiente de mejorar (sondear índices).

### Archivos nuevos
- `signcam_sidecar.py` — pipeline como sidecar (JSON por stdout, config por args)
- `app/` — proyecto Electron + React (package.json, electron/, src/)

### Resultado
App de escritorio funcionando: botón iniciar/detener, preview en vivo de la cámara
virtual, fps en pantalla y panel de ajustes (cámara, tamaño y posición del subtítulo)
persistente. El subtítulo real se compone en Python y se expone a Teams/Zoom/Meet.

---

## Fase 4a: Migración de LSTM a ONNX (quitar TensorFlow del runtime) ✅
**Completado: 2026-06-22**

### Objetivo
TensorFlow pesa ~1 GB (incluido un .dll que rompía el push a GitHub) y solo se usaba
para inferir el LSTM. Migrarlo a ONNX quita TensorFlow del runtime y prepara el
empaquetado.

### Proceso
- `convertir_lstm_onnx.py`: convierte `lstm_signos.h5` → `lstm_signos.onnx` vía
  SavedModel + tf2onnx. Verifica equivalencia Keras vs ONNX (diferencia 0.00e+00).
- Sidecar: `import onnxruntime` en vez de TensorFlow. Carga con `ort.InferenceSession`,
  inferencia con `sesion.run()`. Input `input_layer`, output `output_0`.
- Desinstalado `tensorflow` del venv. (Reinstalar solo si se reentrena el LSTM.)

### Nota
`entrenar_lstm.py` y `convertir_lstm_onnx.py` siguen necesitando TensorFlow; el runtime
(sidecar) ya no.

## Fase 4b: Saga de la cámara en Electron (resuelto) ✅
**Completado: 2026-06-25**

Tras migrar a ONNX, la app se quedaba colgada en "Cargando modelos…". Cadena de causas
y soluciones (todas en `signcam_sidecar.py` salvo donde se indique):

| Problema | Causa | Solución |
|---|---|---|
| Cuelgue al abrir cámara con `CAP_DSHOW` | DirectShow se bloquea en el proceso hijo de Electron | Volver al backend por defecto (MSMF) |
| Selector de cámara abría otra distinta | El orden de pygrabber (DShow) no coincidía con el índice de captura | Verificado con `probe_camaras.py` que MSHOW/MSMF coinciden para este equipo; se mantiene pygrabber para nombres |
| Eventos no llegaban en vivo a la UI | stdout de Python con buffering al ser proceso hijo | Lanzar Python con `-u` (sin buffer) desde Electron |
| Apertura de cámara MSMF lentísima (~30s) | Negociación de "hardware transforms" | `OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS=0` antes de importar cv2 |
| Deadlock de COM ("OleMainThreadWndName Not Responding") | El hilo entra en STA (necesita bucle de mensajes que no hay) | `CoInitializeEx` en modo MTA antes de tocar la cámara |
| Deadlock permanente al "cargar modelos" | sklearn importa su backend de hilos (OpenMP/joblib) de forma diferida y choca con la init MTA de COM | Forzar `import sklearn` ANTES de inicializar COM. **No quitar ese import** |
| Sidecars zombis acumulados reteniendo la cámara | Un proceso colgado en COM no muere con kill normal | `taskkill /T /F` al detener; matar zombis con `taskkill /F /IM python.exe` |

Lección: lanzar procesos que usan cámara/COM desde Electron es delicado; el orden de
imports y la inicialización de COM importan mucho.

---

## Fase 4c: Sidecar empaquetado con PyInstaller ✅
**Completado: 2026-06-25**

### Objetivo
Convertir el sidecar en un `.exe` autónomo para que el usuario final no necesite
Python ni el venv instalados.

### Cambios
- **Rutas portables**: `signcam_sidecar.py` ya no usa rutas absolutas `F:\App LSE\...`.
  Helper `recurso()` resuelve los modelos junto al script (dev) o en `sys._MEIPASS`
  (empaquetado). Esto además hizo el proyecto portable.
- **`signcam_sidecar.spec`**: receta de PyInstaller (modo carpeta, arranque rápido).
  `collect_all` de mediapipe, onnxruntime, pyvirtualcam, matplotlib, pygrabber, comtypes.
  Incluye los 4 modelos como datos. Excluye tensorflow/keras (no se usan en runtime).
  Genera `dist/signcam_sidecar/signcam_sidecar.exe` (~349 MB).
- **Modo `--list-cameras`**: atajo al inicio del sidecar (antes de importar cv2/mediapipe)
  que lista cámaras con pygrabber y sale. Rápido tanto en Python como en el .exe.
  Sustituye a `listar_camaras.py` (eliminado).
- **Integración Electron**: `main.js` elige el comando según entorno — `comandoSidecar()`
  devuelve Python+venv en desarrollo (`SIGNCAM_DEV=1`) y el `.exe` en producción.
  Consola oculta con `windowsHide: true`.
- **Script `npm run prod`**: compila el renderer y lanza Electron sin `SIGNCAM_DEV`
  (carga `dist/`, usa el `.exe`). Probado: funciona sin pasar por el venv.

### Problemas encontrados y soluciones
| Problema | Causa | Solución |
|---|---|---|
| `.exe` petaba: `No module named 'matplotlib'` | mediapipe importa matplotlib en `drawing_utils`; lo había excluido | Quitar matplotlib de `excludes` y añadirlo a `collect_all` |

### Resultado
`signcam_sidecar.exe` funciona en ambos modos (`--list-cameras` y normal → `ready`),
sin Python. La app en `npm run prod` lo usa correctamente. Backend de producción
completo y autocontenido.

---

## Fase 4d: Instalador (pendiente)
- Empaquetar la app Electron entera con **electron-builder** → instalador `.exe`/`.msi`
  que incluya la UI + `dist/signcam_sidecar/` (ajustar ruta del `.exe` empaquetado dentro
  del recurso de la app, p.ej. `process.resourcesPath`).
- **Driver de cámara virtual sin OBS**: que el instalador registre el driver para que el
  usuario no tenga que instalar OBS Studio.
