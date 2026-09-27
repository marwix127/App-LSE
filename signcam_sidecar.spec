# venv\Scripts\pyinstaller signcam_sidecar.spec  ->  dist\signcam_sidecar\signcam_sidecar.exe

from PyInstaller.utils.hooks import collect_all

# modelos
datas = [
    ("hand_landmarker.task", "."),
    ("mlp_signos.pkl", "."),
    ("lstm_signos.onnx", "."),
    ("lstm_encoder.pkl", "."),
]
binaries = []
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
    excludes=["tensorflow", "keras"],  # matplotlib no, lo usa mediapipe
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="signcam_sidecar",
    console=True,  # stdin/stdout con Electron
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="signcam_sidecar",
)
