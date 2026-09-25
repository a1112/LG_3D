"""Helpers for releasing completed inference-call input ownership."""


def release_predictor_input_references(model) -> None:
    """Drop large last-batch references without unloading model weights."""
    predictor = getattr(model, "predictor", None)
    if predictor is None:
        return
    for attribute in ("dataset", "batch", "results", "plotted_img"):
        if hasattr(predictor, attribute):
            setattr(predictor, attribute, None)
