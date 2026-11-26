def predict_risk() -> dict:
    return {
        "status": "not_available",
        "reason": "No valid labelled training dataset or trained model is configured.",
        "prediction": None,
    }
