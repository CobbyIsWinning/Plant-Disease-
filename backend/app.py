import os
import io
import json
import threading

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "1")
os.environ.setdefault("TF_NUM_INTEROP_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
IGNORED_PREDICTION_CLASSES = {"PlantVillage"}
DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


def _get_cors_origins():
    origins = os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    return [origin.strip().rstrip("/") for origin in origins.split(",") if origin.strip()]

app = FastAPI(title="Plant Disease Prediction API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_model = None
_class_indices = None
_preprocess_mode = "mobilenetv2"
_model_path = ""
_load_error = None
_model_lock = threading.Lock()
tf = None
load_model = None


def _find_model_path() -> str:
    for name in PREFERRED_MODELS:
        p = os.path.join(MODEL_DIR, name)
        if os.path.exists(p):
            return p
    return ""


@app.on_event("startup")
def load_resources():
    global _class_indices, _model_path
    _model_path = _find_model_path()
    if not _model_path:
        abs_model_dir = os.path.abspath(MODEL_DIR)
        message = (
            f"No model found in: {abs_model_dir}. "
            "Please ensure your model file is placed there with a recognized name "
            "(e.g., 'mobilenetv2_best.keras' or 'cnn_baseline.keras')."
        )
        print(message)
    elif os.getenv("EAGER_MODEL_LOAD", "").lower() in {"1", "true", "yes"}:
        ensure_model_loaded()
    else:
        print(f"Model found and will be loaded on first prediction: {_model_path}")

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


def _import_tensorflow():
    global tf, load_model
    if tf is not None:
        return

    import tensorflow as tensorflow
    from tensorflow.keras.models import load_model as keras_load_model

    tensorflow.config.threading.set_intra_op_parallelism_threads(int(os.getenv("TF_NUM_INTRAOP_THREADS", "1")))
    tensorflow.config.threading.set_inter_op_parallelism_threads(int(os.getenv("TF_NUM_INTEROP_THREADS", "1")))
    tf = tensorflow
    load_model = keras_load_model


def ensure_model_loaded():
    global _model, _preprocess_mode, _model_path, _load_error
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model
        if not _model_path:
            _model_path = _find_model_path()
        if not _model_path:
            raise RuntimeError(f"No model found in: {os.path.abspath(MODEL_DIR)}")

        try:
            print(f"Loading model from: {_model_path}")
            _import_tensorflow()
            _model = load_model(_model_path, compile=False)
            _preprocess_mode = "baseline" if os.path.basename(_model_path).startswith("cnn_baseline") else "mobilenetv2"
            _load_error = None
            print(f"Preprocessing mode: {_preprocess_mode}")
            print("Model loaded.")
            return _model
        except Exception as exc:
            _load_error = str(exc)
            raise


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
        arr = (arr / 127.5) - 1.0
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

    heatmap_float = heatmap_resized.astype(np.float32) / 255.0
    colored_heatmap = np.stack(
        [
            np.clip(1.5 - np.abs(4.0 * heatmap_float - 3.0), 0.0, 1.0),
            np.clip(1.5 - np.abs(4.0 * heatmap_float - 2.0), 0.0, 1.0),
            np.clip(1.5 - np.abs(4.0 * heatmap_float - 1.0), 0.0, 1.0),
        ],
        axis=-1,
    )
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
    try:
        model = ensure_model_loaded()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model not loaded on server: {e}")

    if not _validate_extension(file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file extension. Use jpg/jpeg/png.")

    content = await file.read()
    try:
        inp = _preprocess_image(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unable to read image: {e}")

    # prediction
    try:
        preds = model.predict(inp, verbose=0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")
    if preds.ndim == 2:
        preds = preds[0]
    
    # Softmax probabilities
    probs = preds / (preds.sum() + 1e-12)

    # prepare label mapping
    idx_to_label = None
    if _class_indices:
        idx_to_label = {v: k for k, v in _class_indices.items()}

    # top-k, excluding dataset container labels that are not real diagnoses
    top_k = max(1, min(int(top_k), len(probs)))
    sorted_idx = probs.argsort()[::-1]
    results = []
    for idx in sorted_idx:
        label = idx_to_label.get(int(idx), str(int(idx))) if idx_to_label else str(int(idx))
        if label in IGNORED_PREDICTION_CLASSES:
            continue
        confidence = float(probs[int(idx)])
        results.append({"class": label, "confidence": confidence, "index": int(idx)})
        if len(results) >= top_k:
            break

    if not results:
        raise HTTPException(status_code=500, detail="No valid diagnosis classes found in model output.")

    display_total = sum(item["confidence"] for item in results) or 1e-12
    normalized_results = [
        {
            "class": item["class"],
            "confidence": item["confidence"] / display_total,
            "raw_confidence": item["confidence"],
            "index": item["index"],
        }
        for item in results
    ]

    top1 = normalized_results[0]

    response = {
        "predicted_class": top1["class"],
        "confidence": top1["confidence"],
        "raw_confidence": top1["raw_confidence"],
        "top_k": [
            {
                "class": item["class"],
                "confidence": item["confidence"],
                "raw_confidence": item["raw_confidence"],
            }
            for item in normalized_results
        ],
        "confidence_basis": "normalized_top_k_valid_classes",
        "class_indices_loaded": bool(_class_indices),
    }

    if grad_cam:
        try:
            # Find the last convolutional layer. For MobileNetV2, it's usually 'Conv_1' or 'out_relu'
            # Note: We use the most common layer names or dynamically search for a Conv2D layer.
            last_conv_layer_name = None
            for layer in reversed(model.layers):
                if isinstance(layer, tf.keras.layers.Conv2D):
                    last_conv_layer_name = layer.name
                    break
            
            if last_conv_layer_name:
                heatmap = make_gradcam_heatmap(inp, model, last_conv_layer_name, pred_index=top1["index"])
                response["heatmap"] = overlay_heatmap(content, heatmap)
        except Exception as e:
            print(f"Grad-CAM error: {e}")
            response["heatmap_error"] = str(e)

    return response


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_available": bool(_model_path or _find_model_path()),
        "model_loaded": _model is not None,
        "class_indices_loaded": _class_indices is not None,
        "load_error": _load_error,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
