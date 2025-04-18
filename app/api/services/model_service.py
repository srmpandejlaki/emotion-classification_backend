import os
import joblib
import pandas as pd
from typing import Tuple
from sqlalchemy.orm import Session
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, precision_score, recall_score
from app.models import PreprocessedData
from app.database.settings import settings

MODEL_PATH = settings.model_path
TEST_DATA_PATH = settings.test_data_path
METRICS_PATH = settings.metrics_path

def train_model(ratio_str: str, db: Session) -> Tuple[dict, str]:
    data = db.query(PreprocessedData).all()
    if not data:
        return None, "Tidak ada data yang tersedia untuk pelatihan."

    texts = [item.cleaned_text for item in data]
    labels = [item.label for item in data]

    try:
        train_ratio = int(ratio_str.split(":")[0]) / 100
    except:
        return None, "Format rasio tidak valid. Gunakan format seperti 80:20"

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=1 - train_ratio, stratify=labels, random_state=42
    )

    vectorizer = CountVectorizer()
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    model = MultinomialNB()
    model.fit(X_train_vec, y_train)

    # Simpan model dan vectorizer
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump((model, vectorizer), MODEL_PATH)

    y_pred = model.predict(X_test_vec)
    metrics = {
        "accuracy": round(accuracy_score(y_test, y_pred) * 100, 2),
        "precision": round(precision_score(y_test, y_pred, average="macro") * 100, 2),
        "recall": round(recall_score(y_test, y_pred, average="macro") * 100, 2),
    }

    # Simpan metrik ke file
    pd.Series(metrics).to_json(METRICS_PATH)

    # Simpan data uji
    df_test = pd.DataFrame({
        "text": X_test,
        "label": y_test,
        "predicted": y_pred
    })

    save_test_data_to_csv(df_test)

    return {
        "metrics": metrics,
        "test_data": df_test
    }, None

def save_test_data_to_csv(df_test: pd.DataFrame) -> str:
    os.makedirs(os.path.dirname(TEST_DATA_PATH), exist_ok=True)
    df_test.to_csv(TEST_DATA_PATH, index=False)
    return TEST_DATA_PATH

def is_model_available() -> bool:
    return os.path.exists(MODEL_PATH)

def load_latest_metrics() -> dict:
    if not os.path.exists(METRICS_PATH):
        return {}
    return pd.read_json(METRICS_PATH, typ='series').to_dict()