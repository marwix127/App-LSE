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

## Fase 3: UI — App Electron + React (pendiente)
Panel de configuración, selección de lengua de signos, etc.

## Fase 4: Empaquetado (pendiente)
Instalador que incluye el driver de cámara virtual sin necesidad de instalar OBS.
