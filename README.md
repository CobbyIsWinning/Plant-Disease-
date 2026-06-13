# Plant Disease Detection

Plant Disease Detection is a full-stack machine learning project for classifying crop leaf images and showing diagnosis support to the user. The app combines a trained Keras image classifier, a FastAPI prediction service, and a React landing page where users can upload a leaf image, view the prediction, inspect a Grad-CAM heatmap, and read practical diagnosis notes.

## Project Goals

- Detect plant leaf disease from an uploaded image.
- Return the most likely class, confidence score, and top alternative predictions.
- Show a Grad-CAM heatmap so users can see which parts of the image influenced the model.
- Provide educational diagnosis details such as symptoms, common causes, and suggested next steps.
- Present the model through a polished landing-page frontend suitable for a demo or portfolio.

## Tech Stack

- **Frontend:** React, Vite, CSS
- **Backend:** FastAPI, TensorFlow/Keras, Pillow, NumPy
- **Model:** Saved Keras CNN model in `backend/saved_models/cnn_baseline.keras`
- **Explainability:** Grad-CAM heatmap generation in the backend
- **Data:** Plant leaf image folders under `backend/dataset/raw`

## Repository Structure

```text
.
├── backend/
│   ├── app.py                    # FastAPI app, prediction route, Grad-CAM logic
│   ├── dataset/                  # Local training/evaluation dataset folders
│   ├── notebooks/                # Dataset exploration and model training notebook
│   ├── requirements.txt          # Backend Python dependencies
│   ├── results/                  # Training/evaluation reports and figures
│   └── saved_models/             # Saved Keras model artifacts
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # Landing page, upload UI, diagnosis rendering
│   │   ├── App.css               # Frontend styling
│   │   ├── diagnosisInfo.js      # Diagnosis notes and display helpers
│   │   └── landingvideo.mp4      # Hero background video
│   ├── package.json              # Frontend scripts and dependencies
│   └── vite.config.js
├── docker-compose.yml
└── README.md
```

## How It Works

1. The user opens the React landing page.
2. The user uploads a JPG or PNG leaf image.
3. The frontend sends the image to `POST /predict?grad_cam=true`.
4. The backend loads the saved Keras model and preprocesses the image.
5. The model predicts the class probabilities.
6. The backend returns:
   - predicted class
   - displayed confidence rating normalized across the returned valid top predictions
   - top predictions with both normalized display confidence and raw model confidence
   - optional Grad-CAM heatmap as base64 JPEG
7. The backend filters out the temporary `PlantVillage` dataset-folder label and returns the best real crop/disease prediction.
8. The frontend maps the predicted class to diagnosis notes stored locally in `frontend/src/diagnosisInfo.js`.

## Local Setup

Run the backend first:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

Run the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually:

```text
http://localhost:5173
```

The frontend uses `VITE_API_URL` in production and falls back locally to:

```text
http://localhost:8000/predict
```

On Vercel, set:

```text
VITE_API_URL=https://your-render-backend.onrender.com
```

On Render, set:

```text
CORS_ORIGINS=https://your-vercel-app.vercel.app
PYTHONUNBUFFERED=1
```

## API Summary

### `GET /health`

Returns whether the backend is running and whether model/class-index resources are loaded.

### `POST /predict`

Accepts a multipart image upload.

Query parameters:

- `top_k`: number of displayed predictions to return, default `3`
- `grad_cam`: whether to include a heatmap, default `false`

Example:

```bash
curl -F "file=@/path/to/leaf.jpg" "http://127.0.0.1:8000/predict?top_k=5&grad_cam=true"
```

Example response shape:

```json
{
  "predicted_class": "Tomato_Early_blight",
  "confidence": 0.91,
  "raw_confidence": 0.82,
  "top_k": [
    { "class": "Tomato_Early_blight", "confidence": 0.91, "raw_confidence": 0.82 },
    { "class": "Tomato_Late_blight", "confidence": 0.09, "raw_confidence": 0.08 }
  ],
  "confidence_basis": "normalized_top_k_valid_classes",
  "class_indices_loaded": true,
  "heatmap": "base64-jpeg-data"
}
```

## Model Notes

The backend looks for model files in `backend/saved_models/`. It prefers MobileNetV2 filenames if they exist, then falls back to the included baseline CNN:

- `mobilenetv2_best.keras`
- `mobilenetv2_final.keras`
- `mobilenetv2_best.h5`
- `mobilenetv2_final.h5`
- `cnn_baseline.keras`
- `cnn_baseline.h5`

The current checked-in model is:

```text
backend/saved_models/cnn_baseline.keras
```

For this baseline model, images are resized to `224x224` and normalized with `arr / 255.0`.

## Diagnosis Notes

The model itself only predicts labels and probabilities. The detailed diagnosis text is provided by the frontend using a class-to-content map in `frontend/src/diagnosisInfo.js`.

Each diagnosis entry can include:

- disease or healthy-class summary
- visible symptoms to check
- common causes
- suggested next steps
- educational-use disclaimer

This keeps the explanation predictable and avoids generating unsupported advice.

## Known Limitations

- `PlantVillage` currently exists as a folder inside `backend/dataset/raw`, so the model may score it as a class. The backend filters it out of API responses, but the dataset should be cleaned so `PlantVillage` is not a class label.
- The baseline model evaluation in `backend/results/classification_report.txt` shows low overall accuracy. Treat predictions as a demo result, not a production diagnosis.
- The app uses image-only classification. It does not consider weather, location, plant age, crop management, or field spread.
- The Grad-CAM heatmap explains model attention, not guaranteed biological evidence.
- The landing video is large and should be compressed before deployment.

## Recommended Improvements

- Clean the dataset folder structure and remove `PlantVillage` as a class.
- Retrain or fine-tune a stronger model after fixing the dataset labels.
- Save a stable `class_indices_*.json` file alongside each trained model.
- Add backend tests for `/predict`, preprocessing, and Grad-CAM.
- Move diagnosis content into a separate JSON file or backend endpoint.
- Compress `frontend/src/landingvideo.mp4` before hosting.

## More Documentation

- Backend details: `backend/README.md`
- Frontend details: `frontend/README.md`
- Dataset details: `backend/dataset/README.md`
- Notebook/training details: `backend/notebooks/README.md`
- Model artifact details: `backend/saved_models/README.md`
- Results details: `backend/results/README.md`
