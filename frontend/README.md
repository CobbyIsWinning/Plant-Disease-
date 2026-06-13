# Frontend

The frontend is a React/Vite landing page for the plant disease detection model. It presents the project, explains the model, lets users upload a leaf image, displays prediction results, shows a Grad-CAM heatmap, and renders diagnosis notes for the predicted class.

## Main Files

```text
frontend/
├── src/
│   ├── App.jsx             # Main React app and diagnosis content map
│   ├── App.css             # Landing page and predictor styling
│   ├── main.jsx            # React entry point
│   └── landingvideo.mp4    # Hero background video
├── package.json            # Scripts and dependencies
├── vite.config.js          # Vite configuration
└── index.html              # App HTML shell
```

## Page Structure

The UI is organized as:

1. **Hero section** with autoplay background video.
2. **Model overview section** explaining the classifier and heatmap.
3. **Prediction section** with file upload, image preview, heatmap, and model output.
4. **Diagnosis notes panel** with symptoms, causes, and suggested next steps.
5. **Footer** with project links and backend endpoint information.

## Backend Connection

The frontend posts images to the backend endpoint defined in `src/App.jsx`:

```js
const BACKEND_DEFAULT = 'http://localhost:8000'
```

Prediction requests are sent to:

```text
POST http://localhost:8000/predict?grad_cam=true
```

The request body is `FormData` containing:

- `file`: selected image
- `top_k`: currently set to `5`

## Diagnosis Notes

The detailed diagnosis text is stored in `DIAGNOSIS_INFO` inside `src/App.jsx`.

Each class can define:

- `title`
- `summary`
- `symptoms`
- `causes`
- `nextSteps`

The model returns only labels and confidence scores. The frontend maps those labels to readable educational guidance.

## Ignored Prediction Classes

The frontend currently ignores:

```text
PlantVillage
```

This is a temporary UI fix because `PlantVillage` appears as a folder in the dataset and can be returned as a model class. The preferred long-term fix is to clean the dataset and retrain with only real crop/disease labels.

## Running Locally

Install dependencies:

```bash
cd frontend
npm install
```

Start the development server:

```bash
npm run dev
```

Open the Vite URL, usually:

```text
http://localhost:5173
```

Make sure the backend is also running at:

```text
http://localhost:8000
```

## Building for Production

```bash
npm run build
```

The production files are generated in:

```text
frontend/dist/
```

## Video Asset Note

`src/landingvideo.mp4` is used as the hero background. It is currently large, so compress it before deploying to improve load time and hosting cost.

## Customization

Common edits:

- Change hero copy in `App.jsx`
- Change colors and layout in `App.css`
- Update backend URL with `BACKEND_DEFAULT`
- Add or improve diagnosis content in `DIAGNOSIS_INFO`
- Add more ignored non-disease labels to `IGNORED_PREDICTION_CLASSES`
