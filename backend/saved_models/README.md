# Saved Models

This folder stores trained model artifacts used by the FastAPI backend.

## Current Model

The current project includes:

```text
cnn_baseline.keras
```

This is the baseline Keras CNN model used by the backend when no MobileNetV2 model is available.

## Recognized Model Filenames

The backend searches for models in this order:

```text
mobilenetv2_best.keras
mobilenetv2_final.keras
mobilenetv2_best.h5
mobilenetv2_final.h5
cnn_baseline.keras
cnn_baseline.h5
```

The first file found is loaded.

## Matching Preprocessing

Preprocessing is selected by filename:

- `mobilenetv2_*`: uses MobileNetV2 `preprocess_input`
- `cnn_baseline*`: uses `arr / 255.0`

Always deploy the model with the preprocessing logic it was trained with.

## Class Index File

Preferred class mapping file:

```text
class_indices_mobilenetv2.json
```

This should contain a mapping from class name to numeric index, for example:

```json
{
  "Tomato_healthy": 0,
  "Tomato_Early_blight": 1
}
```

If the JSON is missing, the backend infers labels from `backend/dataset/raw`, but this can include unwanted folders. Saving a clean mapping is safer.

## Deployment Notes

For hosting, include this folder with the backend container or mount it as read-only storage.

The dataset is not required for prediction if a model and clean class-index JSON are provided.

## Model Replacement Checklist

When adding a new model:

1. Place the model in this folder with a recognized filename.
2. Save the matching class-index JSON.
3. Confirm the backend chooses the correct preprocessing mode.
4. Start the backend and call `/health`.
5. Test `/predict` with a known sample image.
6. Verify top predictions and Grad-CAM output.
