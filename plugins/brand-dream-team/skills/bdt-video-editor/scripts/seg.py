"""Person cutout for camera effects (graphics behind the creator). Small model shipped in data/u2netp.onnx."""
import os, subprocess, sys
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "..", "data", "u2netp.onnx")
_S = None

def _session():
    global _S
    if _S is None:
        try:
            import onnxruntime as ort
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "onnxruntime", "--break-system-packages"], capture_output=True)
            try: import onnxruntime as ort
            except ImportError: _S = False; print("note: onnxruntime unavailable, camera effects draw without the cutout"); return _S
        _S = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
    return _S

def person_mask(rgb):
    """float32 HxW, 1 = person. Zeros if the model can't run."""
    h, w = rgb.shape[:2]; s = _session()
    if not s: return np.zeros((h, w), np.float32)
    x = cv2.resize(np.asarray(rgb, np.uint8), (320, 320), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    x = ((x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]).transpose(2, 0, 1)[None].astype(np.float32)
    o = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
    o = (o - o.min()) / (o.max() - o.min() + 1e-6)
    m = cv2.resize(o, (w, h), interpolation=cv2.INTER_LINEAR)
    m = np.clip((m - 0.35) / 0.4, 0, 1)
    return cv2.GaussianBlur(m, (5, 5), 0).astype(np.float32)
