import os
import io
import json
from typing import List

import numpy as np
from PIL import Image
import tensorflow as tf
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from tensorflow.keras.models import load_model, Model
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
import matplotlib.cm as cm
import base64

# Configuration
IMG_SIZE = 224
ALLOWED_EXT = {".jpg", ".jpeg", ".png"}
MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
# preferred model filenames (the notebook saves these names)
PREFERRED_MODELS = [
    "mobilenetv2_best.keras",
    "mobilenetv2_final.keras",
    "mobilenetv2_best.h5",
    "mobilenetv2_final.h5",
]
CLASS_INDICES_PATH = os.path.join(MODEL_DIR, "class_indices_mobilenetv2.json")

app = FastAPI(title="Plant Disease Prediction API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_model = None
_class_indices = None


def _find_model_path() -> str:
    for name in PREFERRED_MODELS:
        p = os.path.join(MODEL_DIR, name)
        if os.path.exists(p):
            return p
    return ""


@app.on_event("startup")
def load_resources():
    global _model, _class_indices
    model_path = _find_model_path()
    if not model_path:
        message = (
            "No model found in backend/saved_models/. "
            "Place your saved MobileNetV2 model as 'mobilenetv2_best.keras' or 'mobilenetv2_final.keras'."
        )
        print(message)
        # keep server running but will return errors on predict
        _model = None
    else:
        print(f"Loading model from: {model_path}")
        # load without compiling to keep startup faster
        _model = load_model(model_path, compile=False)
        print("Model loaded.")

    if os.path.exists(CLASS_INDICES_PATH):
        with open(CLASS_INDICES_PATH, "r") as f:
            _class_indices = json.load(f)
        print("Class indices loaded.")
    else:
        print(f"Class indices file not found at {CLASS_INDICES_PATH}")
        _class_indices = None


def _validate_extension(filename: str) -> bool:
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXT


def _preprocess_image(data: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img = img.resize((IMG_SIZE, IMG_SIZE))
    arr = np.array(img).astype(np.float32)
    arr = preprocess_input(arr)
    arr = np.expand_dims(arr, axis=0)
    return arr


def make_gradcam_heatmap(img_array, model, last_conv_layer_name, pred_index=None):
    """Generates a Grad-CAM heatmap."""
    grad_model = Model(
        model.inputs, [model.get_layer(last_conv_layer_name).output, model.output]
    )

    with tf.GradientTape() as tape:
        last_conv_layer_output, preds = grad_model(img_array)
        if pred_index is None:
            pred_index = tf.argmax(preds[0])
        class_channel = preds[:, pred_index]

    grads = tape.gradient(class_channel, last_conv_layer_output)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    last_conv_layer_output = last_conv_layer_output[0]
    heatmap = last_conv_layer_output @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)

    heatmap = tf.maximum(heatmap, 0) / (tf.math.reduce_max(heatmap) + 1e-10)
    return heatmap.numpy()


def overlay_heatmap(img_data, heatmap, alpha=0.4):
    """Overlays the heatmap on the original image and returns as base64."""
    img = Image.open(io.BytesIO(img_data)).convert("RGB")
    original_size = img.size
    img_array = np.array(img)

    # Rescale heatmap to 0-255
    heatmap_img = np.uint8(255 * heatmap)
    jet = cm.get_cmap("jet")
    jet_colors = jet(np.arange(256))[:, :3]
    jet_heatmap = jet_colors[heatmap_img]

    # Resize heatmap to match image size
    jet_heatmap = Image.fromarray(np.uint8(jet_heatmap * 255))
    jet_heatmap = jet_heatmap.resize(original_size)
    jet_heatmap = np.array(jet_heatmap)

    # Superimpose
    superimposed_img = jet_heatmap * alpha + img_array
    superimposed_img = Image.fromarray(np.uint8(superimposed_img))

    buffered = io.BytesIO()
    superimposed_img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()


@app.post("/predict")
async def predict(file: UploadFile = File(...), top_k: int = 3, grad_cam: bool = False):
    """Predict the plant disease from an uploaded image.
    If grad_cam is True, returns a base64 encoded heatmap overlay.
    """
    if _model is None:
        raise HTTPException(status_code=500, detail="Model not loaded on server. Check backend/saved_models/.")

    if not _validate_extension(file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file extension. Use jpg/jpeg/png.")

    content = await file.read()
    try:
        inp = _preprocess_image(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unable to read image: {e}")

    # prediction
    preds = _model.predict(inp)
    if preds.ndim == 2:
        preds = preds[0]
    
    # Softmax probabilities
    probs = preds / (preds.sum() + 1e-12)

    # top-k
    top_k = min(int(top_k), len(probs))
    top_idx = probs.argsort()[-top_k:][::-1]

    # prepare label mapping
    idx_to_label = None
    if _class_indices:
        idx_to_label = {v: k for k, v in _class_indices.items()}

    results = []
    for idx in top_idx:
        label = idx_to_label.get(int(idx), str(int(idx))) if idx_to_label else str(int(idx))
        confidence = float(probs[int(idx)])
        results.append({"class": label, "confidence": confidence})

    top1 = results[0]

    response = {
        "predicted_class": top1["class"],
        "confidence": top1["confidence"],
        "top_k": results,
        "class_indices_loaded": bool(_class_indices),
    }

    if grad_cam:
        try:
            # Find the last convolutional layer. For MobileNetV2, it's usually 'Conv_1' or 'out_relu'
            # Note: We use the most common layer names or dynamically search for a Conv2D layer.
            last_conv_layer = None
            for layer in reversed(_model.layers):
                if isinstance(layer, tf.keras.layers.Conv2D):
                    last_conv_layer = layer.name
                    break
            
            if last_conv_layer:
                heatmap = make_gradcam_heatmap(inp, _model, last_conv_layer)
                response["heatmap"] = overlay_heatmap(content, heatmap)
        except Exception as e:
            print(f"Grad-CAM error: {e}")
            response["heatmap_error"] = str(e)

    return response


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None, "class_indices_loaded": _class_indices is not None}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
