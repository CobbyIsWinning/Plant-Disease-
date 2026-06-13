import os
import io
import json
import tempfile
from typing import List

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))

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
    "cnn_baseline.keras",
    "cnn_baseline.h5",
]
CLASS_INDICES_PATH = os.path.join(MODEL_DIR, "class_indices_mobilenetv2.json")
DATASET_DIR = os.path.join(os.path.dirname(__file__), "dataset", "raw")

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
_preprocess_mode = "mobilenetv2"


def _find_model_path() -> str:
    for name in PREFERRED_MODELS:
        p = os.path.join(MODEL_DIR, name)
        if os.path.exists(p):
            return p
    return ""


@app.on_event("startup")
def load_resources():
    global _model, _class_indices, _preprocess_mode
    model_path = _find_model_path()
    if not model_path:
        abs_model_dir = os.path.abspath(MODEL_DIR)
        message = (
            f"No model found in: {abs_model_dir}. "
            "Please ensure your model file is placed there with a recognized name "
            "(e.g., 'mobilenetv2_best.keras' or 'cnn_baseline.keras')."
        )
        print(message)
        # keep server running but will return errors on predict
        _model = None
    else:
        print(f"Loading model from: {model_path}")
        # load without compiling to keep startup faster
        _model = load_model(model_path, compile=False)
        _preprocess_mode = "baseline" if os.path.basename(model_path).startswith("cnn_baseline") else "mobilenetv2"
        print(f"Preprocessing mode: {_preprocess_mode}")
        print("Model loaded.")

    if os.path.exists(CLASS_INDICES_PATH):
        with open(CLASS_INDICES_PATH, "r") as f:
            _class_indices = json.load(f)
        print("Class indices loaded.")
    elif os.path.isdir(DATASET_DIR):
        labels = sorted(
            entry
            for entry in os.listdir(DATASET_DIR)
            if os.path.isdir(os.path.join(DATASET_DIR, entry)) and not entry.startswith(".")
        )
        _class_indices = {label: idx for idx, label in enumerate(labels)}
        print(f"Class indices inferred from dataset folders: {len(_class_indices)} classes.")
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
    if _preprocess_mode == "baseline":
        arr = arr / 255.0
    else:
        arr = preprocess_input(arr)
    arr = np.expand_dims(arr, axis=0)
    return arr


def make_gradcam_heatmap(img_array, model, last_conv_layer_name, pred_index=None):
    """Generates a Grad-CAM heatmap."""
    img_tensor = tf.convert_to_tensor(img_array)

    if isinstance(model, tf.keras.Sequential):
        with tf.GradientTape() as tape:
            x = img_tensor
            last_conv_layer_output = None
            for layer in model.layers:
                try:
                    x = layer(x, training=False)
                except TypeError:
                    x = layer(x)
                if layer.name == last_conv_layer_name:
                    last_conv_layer_output = x

            if last_conv_layer_output is None:
                raise ValueError(f"Layer not found: {last_conv_layer_name}")

            preds = x
            if pred_index is None:
                pred_index = int(tf.argmax(preds[0]))
            class_channel = preds[:, pred_index]
    else:
        # Create a model that maps the input image to the activations
        # of the last conv layer as well as the output predictions.
        grad_model = Model(
            inputs=model.inputs,
            outputs=[model.get_layer(last_conv_layer_name).output, model.outputs[0]]
        )

        # Then, compute the gradient of the top predicted class for our input image
        # with respect to the activations of the last conv layer.
        with tf.GradientTape() as tape:
            last_conv_layer_output, preds = grad_model(img_tensor)
            if pred_index is None:
                pred_index = int(tf.argmax(preds[0]))
            class_channel = preds[:, pred_index]

    # This is the gradient of the output neuron (top predicted or chosen)
    # with regard to the output feature map of the last conv layer
    grads = tape.gradient(class_channel, last_conv_layer_output)
    if grads is None:
        raise ValueError(f"Could not compute gradients for layer: {last_conv_layer_name}")

    # This is a vector where each entry is the mean intensity of the gradient
    # over a specific feature map channel
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    # We multiply each channel in the feature map array
    # by "how important this channel is" with regard to the top predicted class
    # then sum all the channels to obtain the heatmap class activation
    last_conv_layer_output = last_conv_layer_output[0]
    heatmap = last_conv_layer_output @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)

    # For visualization purpose, we will also normalize the heatmap between 0 & 1
    heatmap = tf.maximum(heatmap, 0) / (tf.math.reduce_max(heatmap) + 1e-10)
    return heatmap.numpy()


def overlay_heatmap(img_data, heatmap, alpha=0.4, colormap_name="jet"):
    """Overlays the heatmap on the original image and returns as base64."""
    original_img = Image.open(io.BytesIO(img_data)).convert("RGB")
    img = original_img.resize((IMG_SIZE, IMG_SIZE))
    img_array = np.array(img)

    # Rescale heatmap to 0-255
    heatmap_img = Image.fromarray(np.uint8(255 * heatmap))
    heatmap_img = heatmap_img.resize((IMG_SIZE, IMG_SIZE), Image.Resampling.BILINEAR)
    heatmap_resized = np.array(heatmap_img)

    # Use a colormap to colorize the heatmap
    colormap = cm.get_cmap(colormap_name)
    
    # Use the colormap to get RGB values
    colored_heatmap = colormap(heatmap_resized)[:, :, :3]
    
    # Convert to uint8
    colored_heatmap = np.uint8(255 * colored_heatmap)

    # Superimpose the heatmap on original image
    superimposed_img = colored_heatmap * alpha + img_array
    superimposed_img = np.clip(superimposed_img, 0, 255)
    superimposed_img = Image.fromarray(np.uint8(superimposed_img))
    superimposed_img = superimposed_img.resize(original_img.size)

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
    try:
        preds = _model.predict(inp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")
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
            last_conv_layer_name = None
            for layer in reversed(_model.layers):
                if isinstance(layer, tf.keras.layers.Conv2D):
                    last_conv_layer_name = layer.name
                    break
            
            if last_conv_layer_name:
                heatmap = make_gradcam_heatmap(inp, _model, last_conv_layer_name)
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
