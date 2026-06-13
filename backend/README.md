# Backend

The backend is a FastAPI service that loads a saved Keras model and exposes prediction endpoints for the React frontend. It handles image validation, preprocessing, model inference, top-k formatting, and optional Grad-CAM heatmap generation.

## Main Files

```text
backend/
├── app.py              # FastAPI app and model inference code
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container definition for backend deployment
├── dataset/            # Local dataset used for training/evaluation
├── notebooks/          # Training and exploration notebook
├── results/            # Reports and generated figures
└── saved_models/       # Saved Keras model files
```

## Runtime Behavior

On startup, `app.py`:

1. Searches `backend/saved_models/` for a known model filename.
2. Loads the model with `compile=False`.
3. Chooses preprocessing based on the model type.
4. Loads `class_indices_mobilenetv2.json` if present.
5. If the class-index JSON is missing, infers labels from `backend/dataset/raw`.

Recognized model filenames:

```text
mobilenetv2_best.keras
mobilenetv2_final.keras
mobilenetv2_best.h5
mobilenetv2_final.h5
cnn_baseline.keras
cnn_baseline.h5
```

The current project includes:

```text
backend/saved_models/cnn_baseline.keras
```

## Preprocessing

The backend supports two preprocessing modes:

- **MobileNetV2 models:** `tensorflow.keras.applications.mobilenet_v2.preprocess_input`
- **Baseline CNN model:** resize to `224x224`, convert to float, divide by `255.0`

This matters because a model must receive images in the same format used during training.

## API Endpoints

### `GET /health`

Returns backend status:

```json
{
  "status": "ok",
  "model_loaded": true,
  "class_indices_loaded": true
}
```

### `POST /predict`

Accepts a multipart uploaded image.

Query parameters:

- `top_k`: number of prediction classes to return, default `3`
- `grad_cam`: include a Grad-CAM heatmap when `true`, default `false`

Example:

```bash
curl -F "file=@/path/to/leaf.jpg" "http://127.0.0.1:8000/predict?top_k=5&grad_cam=true"
```

Response fields:

- `predicted_class`: top model class
- `confidence`: probability-like confidence value
- `top_k`: ranked class list
- `class_indices_loaded`: whether label mapping was available
- `heatmap`: optional base64 JPEG heatmap overlay
- `heatmap_error`: returned only when Grad-CAM fails but prediction succeeds

## Running Locally

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

Then test:

```bash
curl "http://127.0.0.1:8000/health"
```

## Grad-CAM

Grad-CAM is generated when `grad_cam=true`.

The backend:

1. Finds the last `Conv2D` layer.
2. Computes class gradients with `tf.GradientTape`.
3. Creates a heatmap from weighted convolution activations.
4. Resizes the heatmap to match the model input image.
5. Overlays it on the original image and returns a base64 JPEG.

The implementation includes a separate path for loaded `Sequential` models because Keras graph access can differ between model types.

## Troubleshooting

### Model not loaded

Check that a recognized model file exists in:

```text
backend/saved_models/
```

### Wrong or strange class labels

If `class_indices_mobilenetv2.json` is missing, labels are inferred from dataset folders. This currently includes `PlantVillage` if that folder exists in `backend/dataset/raw`, which is why the frontend filters it out temporarily.

Best fix: clean the dataset folder structure and save an explicit class-index JSON file during training.

### 500 on prediction

Common causes:

- model file missing
- incompatible preprocessing
- unsupported image file
- broken class mapping
- TensorFlow load/runtime issue

Check the backend terminal logs for the exact exception.

## Deployment Notes

For hosting, deploy the backend as a Docker container with the saved model included or mounted. The prediction service needs enough memory for TensorFlow and the model file.

If deploying the current `Dockerfile`, verify the import path and app command for the target platform. Local development currently runs from the repository root with:

```bash
uvicorn backend.app:app
```
