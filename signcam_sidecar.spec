# PyInstaller spec para el sidecar de SignCam.
# Construir con:  venv\Scripts\pyinstaller signcam_sidecar.spec
#
# Genera dist\signcam_sidecar\signcam_sidecar.exe (modo carpeta: arranque rápido).
# MediaPipe, onnxruntime y pyvirtualcam necesitan que se recojan sus datos y
# binarios nativos, por eso usamos collect_all.

from PyInstaller.utils.hooks import collect_all

# Modelos que el sidecar carga en tiempo de ejecución (van junto al .exe, raíz ".").
datas = [
    ("hand_landmarker.task", "."),
    ("mlp_signos.pkl", "."),
    ("lstm_signos.onnx", "."),
    ("lstm_encoder.pkl", "."),
]
binaries = []
# El MLP es un MLPClassifier; aseguramos que la clase esté disponible al deserializar.
hiddenimports = ["sklearn.neural_network", "sklearn.utils._typedefs"]

for paquete in ("mediapipe", "onnxruntime", "pyvirtualcam", "matplotlib", "pygrabber", "comtypes"):
    d, b, h = collect_all(paquete)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["signcam_sidecar.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tensorflow", "keras"],  # no se usan; matplotlib SÍ lo necesita mediapipe
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="signcam_sidecar",
    console=True,  # consola: stdout/stdin para hablar con Electron
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="signcam_sidecar",
)
