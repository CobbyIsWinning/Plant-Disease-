# Notebooks

This folder contains the exploratory and training notebook for the plant disease detection model.

## Main Notebook

```text
dataset_exploration.ipynb
```

The notebook covers:

- dataset inspection
- class distribution analysis
- image loading with Keras data generators
- baseline CNN training
- evaluation with classification reports and confusion matrix
- transfer-learning experiments with MobileNetV2
- saving trained model files
- saving class-index mappings

## Training Paths

The notebook references dataset and output paths relative to the notebook/backend folder structure. Check paths before rerunning cells, especially when saving models.

Important output locations:

```text
backend/saved_models/
backend/results/
```

## Baseline CNN

The currently available model file is:

```text
backend/saved_models/cnn_baseline.keras
```

This model was trained with image values scaled by:

```python
rescale=1./255
```

The backend therefore uses `arr / 255.0` preprocessing for this model.

## MobileNetV2 Transfer Learning

The notebook also includes MobileNetV2 transfer-learning code. MobileNetV2 expects:

```python
tensorflow.keras.applications.mobilenet_v2.preprocess_input
```

If a MobileNetV2 model is saved as `mobilenetv2_best.keras` or `mobilenetv2_final.keras`, the backend will use the MobileNetV2 preprocessing path automatically.

## Class Indices

The preferred way to preserve labels is to save class indices during training:

```text
backend/saved_models/class_indices_mobilenetv2.json
```

If this file is missing, the backend infers labels from `backend/dataset/raw`. That fallback can include unwanted folders such as `PlantVillage`, so saving a clean class-index JSON is recommended.

## Recommended Rerun Order

1. Clean the dataset folder structure.
2. Verify class distribution.
3. Create training and validation generators.
4. Train or fine-tune the model.
5. Evaluate with confusion matrix and classification report.
6. Save the model to `backend/saved_models/`.
7. Save the matching class-index JSON.
8. Test the model through the FastAPI `/predict` route.

## Notebook Caution

Notebook cells may depend on previous state. Restart the kernel and run from top to bottom before trusting saved outputs.
