"""Small helpers for releasing inference-call input ownership.

Ultralytics keeps the most recent dataset, batch and result list on its
long-lived predictor. That is useful for interactive prediction, but in this
service it pins the last batch of very large camera images between coils.
"""

import gc


def release_predictor_input_references(model) -> None:
    """Drop completed-call references without unloading model weights."""
    predictor = getattr(model, "predictor", None)
    if predictor is None:
        return
    for attribute in ("dataset", "batch", "results", "plotted_img"):
        if hasattr(predictor, attribute):
            setattr(predictor, attribute, None)


def release_inference_caches() -> None:
    """Return completed surface inference buffers to their allocators.

    A production surface can temporarily own several gigabytes of decoded
    images.  NumPy/Pillow objects do not necessarily advance Python's normal
    GC thresholds, and CUDA deliberately keeps freed blocks cached.  Running
    this at the surface boundary prevents a low-frequency service from
    retaining the first coil's transient working set until many later coils.
    Model weights remain loaded.
    """
    gc.collect()
    try:
        import torch
    except ImportError:
        return

    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        # Cache release is best effort.  A missing/reset CUDA context must not
        # turn an otherwise completed coil into a failed one.
        return
