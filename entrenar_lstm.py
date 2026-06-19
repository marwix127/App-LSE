import pickle
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dropout, Dense
from tensorflow.keras.callbacks import EarlyStopping

SEQUENCES_PKL = r"F:\App LSE\lstm_sequences.pkl"
MODEL_PATH = r"F:\App LSE\lstm_signos.h5"
ENCODER_PATH = r"F:\App LSE\lstm_encoder.pkl"


def main():
    print("Cargando secuencias...")
    with open(SEQUENCES_PKL, "rb") as f:
        secuencias = pickle.load(f)

    X, y = [], []
    for letra in ["J", "Z"]:
        for seq in secuencias[letra]:
            X.append(seq)
            y.append(letra)

    X = np.array(X)
    y = np.array(y)
    print(f"{len(X)} secuencias, {len(set(y))} clases: {sorted(set(y))}")
    print(f"Shape de cada secuencia: {X[0].shape}")

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42
    )

    print("Construyendo LSTM...")
    model = Sequential([
        LSTM(128, input_shape=(X.shape[1], X.shape[2]), activation="relu"),
        Dropout(0.2),
        Dense(64, activation="relu"),
        Dropout(0.2),
        Dense(len(le.classes_), activation="softmax")
    ])

    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    print(model.summary())

    print("Entrenando...")
    early_stop = EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)
    model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=50,
        batch_size=4,
        callbacks=[early_stop],
        verbose=1
    )

    y_pred = np.argmax(model.predict(X_test), axis=1)
    accuracy = np.mean(y_pred == y_test)
    print(f"\nAccuracy: {accuracy:.2%}")

    model.save(MODEL_PATH)
    with open(ENCODER_PATH, "wb") as f:
        pickle.dump(le, f)
    print(f"Modelo guardado en {MODEL_PATH}")


if __name__ == "__main__":
    main()
