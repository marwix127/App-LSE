import csv
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
import pickle

CSV_PATHS = [
    r"F:\App LSE\landmarks_dataset.csv",
    r"F:\App LSE\muestras_propias.csv",
]
MODEL_PATH = r"F:\App LSE\mlp_signos.pkl"

def cargar_datos():
    X, y = [], []
    for csv_path in CSV_PATHS:
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for fila in reader:
                letra = fila["letra"]
                landmarks = [float(fila[col]) for col in list(fila.keys())[1:]]
                X.append(landmarks)
                y.append(letra)
    return np.array(X), np.array(y)

def main():
    print("Cargando datos...")
    X, y = cargar_datos()
    print(f"{len(X)} ejemplos, {len(set(y))} clases: {sorted(set(y))}")

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

    print("Entrenando MLP...")
    clf = MLPClassifier(
        hidden_layer_sizes=(128, 64),
        activation="relu",
        max_iter=50,
        verbose=True,
        random_state=42,
    )
    clf.fit(X_train, y_train)

    print("\nEvaluación:")
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"model": clf, "encoder": le}, f)
    print(f"Modelo guardado en {MODEL_PATH}")

if __name__ == "__main__":
    main()
