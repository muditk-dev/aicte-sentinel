import json
import logging
from typing import Dict, Any, Tuple
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, mean_absolute_error

logger = logging.getLogger("sentinel.model_trainer")

FEATURE_COLUMNS = [
    "days_in_current_status",
    "days_since_submission",
    "total_documents",
    "deficient_documents_count",
    "deficiency_notices_count",
    "unresolved_deficiencies_count",
    "has_evc_inspection",
    "regional_backlog_density",
]


def generate_synthetic_workflow_dataset(n_samples: int = 500, random_state: int = 42) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generates synthetic historical workflow records for SIH 2026 demonstration.
    Explicit Notice: This is synthetic baseline data for workflow risk modeling,
    not calibrated on multi-year live production databases.
    
    Features:
    0: days_in_current_status (0 - 45 days)
    1: days_since_submission (0 - 90 days)
    2: total_documents (2 - 15 docs)
    3: deficient_documents_count (0 - 5 docs)
    4: deficiency_notices_count (0 - 3 notices)
    5: unresolved_deficiencies_count (0 - 4 items)
    6: has_evc_inspection (0 or 1)
    7: regional_backlog_density (1 - 50 applications)
    
    Target:
    y_delayed: 1 if application experienced > 14 days delay, else 0
    delay_days: continuous delay days
    """
    rng = np.random.RandomState(random_state)
    
    days_in_status = rng.exponential(scale=8.0, size=n_samples).clip(0, 45)
    days_sub = days_in_status + rng.exponential(scale=15.0, size=n_samples).clip(0, 75)
    total_docs = rng.randint(3, 16, size=n_samples)
    deficient_docs = np.minimum(total_docs, rng.poisson(lam=0.8, size=n_samples))
    notices = np.minimum(deficient_docs, rng.poisson(lam=0.6, size=n_samples))
    unresolved = np.minimum(notices * 2, rng.poisson(lam=0.7, size=n_samples))
    has_evc = rng.binomial(1, 0.45, size=n_samples)
    reg_backlog = rng.randint(5, 45, size=n_samples)

    X = np.column_stack([
        days_in_status,
        days_sub,
        total_docs,
        deficient_docs,
        notices,
        unresolved,
        has_evc,
        reg_backlog,
    ])

    # True latent delay risk function
    logits = (
        -2.2
        + 0.18 * days_in_status
        + 1.10 * unresolved
        + 0.45 * deficient_docs
        + 0.04 * reg_backlog
        - 0.50 * has_evc
    )
    prob_delayed = 1.0 / (1.0 + np.exp(-logits))
    y_delayed = rng.binomial(1, prob_delayed)
    
    # Continuous delay days (approx 3 to 28 days for delayed, 0 to 4 for on-track)
    delay_days = np.where(
        y_delayed == 1,
        7.0 + 3.2 * unresolved + 0.4 * days_in_status + rng.normal(0, 1.5, size=n_samples),
        rng.exponential(scale=1.5, size=n_samples)
    ).clip(0, 45)

    return X, y_delayed, delay_days


def train_and_evaluate_model(random_state: int = 42) -> Dict[str, Any]:
    """
    Reproducibly trains and evaluates the delay risk model on held-out test split.
    Returns measured metrics and comparison against simple majority-class baseline.
    """
    X, y_delayed, delay_days = generate_synthetic_workflow_dataset(n_samples=600, random_state=random_state)
    
    X_train, X_test, y_train, y_test, d_train, d_test = train_test_split(
        X, y_delayed, delay_days, test_size=0.25, random_state=random_state, stratify=y_delayed
    )

    # 1. Baseline Model (Majority Class Classifier)
    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(X_train, y_train)
    baseline_acc = float(baseline.score(X_test, y_test))

    # 2. Supervised Gradient Boosting Model
    clf = GradientBoostingClassifier(
        n_estimators=60,
        max_depth=3,
        learning_rate=0.08,
        random_state=random_state
    )
    clf.fit(X_train, y_train)

    y_probs = clf.predict_proba(X_test)[:, 1]
    y_pred = (y_probs >= 0.50).astype(int)

    # Compute actual measured evaluation metrics
    auc_val = float(roc_auc_score(y_test, y_probs))
    prec_val = float(precision_score(y_test, y_pred, zero_division=0))
    rec_val = float(recall_score(y_test, y_pred, zero_division=0))
    f1_val = float(f1_score(y_test, y_pred, zero_division=0))
    acc_val = float(np.mean(y_pred == y_test))

    # Projected delay MAE
    pred_delay_days = y_probs * 22.0
    mae_val = float(mean_absolute_error(d_test, pred_delay_days))

    measured_metrics = {
        "roc_auc": round(auc_val, 3),
        "precision": round(prec_val, 3),
        "recall": round(rec_val, 3),
        "f1_score": round(f1_val, 3),
        "accuracy": round(acc_val, 3),
        "baseline_accuracy": round(baseline_acc, 3),
        "mae_delay_days": round(mae_val, 1),
        "evaluation_sample_size": len(y_test),
        "train_sample_size": len(y_train),
        "is_synthetic_demonstration": True,
    }

    feature_importances = {
        "days_in_current_status": round(float(clf.feature_importances_[0]), 3),
        "days_since_submission": round(float(clf.feature_importances_[1]), 3),
        "total_documents": round(float(clf.feature_importances_[2]), 3),
        "deficient_documents_count": round(float(clf.feature_importances_[3]), 3),
        "deficiency_notices_count": round(float(clf.feature_importances_[4]), 3),
        "unresolved_deficiencies_count": round(float(clf.feature_importances_[5]), 3),
        "has_evc_inspection": round(float(clf.feature_importances_[6]), 3),
        "regional_backlog_density": round(float(clf.feature_importances_[7]), 3),
    }

    return {
        "metrics": measured_metrics,
        "feature_importances": feature_importances,
        "model_class": "GradientBoostingClassifier",
    }
