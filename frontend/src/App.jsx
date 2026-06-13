import React, { useState } from 'react'
import landingVideo from './landingvideo.mp4'

const BACKEND_DEFAULT = 'http://localhost:8000'
const IGNORED_PREDICTION_CLASSES = new Set(['PlantVillage'])

const DIAGNOSIS_INFO = {
  Pepper__bell___Bacterial_spot: {
    title: 'Bell Pepper Bacterial Spot',
    summary: 'A bacterial disease that causes water-soaked spots on pepper leaves and can spread quickly in warm, wet conditions.',
    symptoms: ['Small dark leaf spots with yellow halos', 'Spots that merge into larger dead patches', 'Scab-like spots on fruit'],
    causes: ['Splashing rain or overhead watering', 'Infected seed or plant debris', 'Warm, humid weather'],
    nextSteps: ['Remove badly infected leaves', 'Avoid watering over the foliage', 'Improve spacing and airflow', 'Use clean seed and rotate crops']
  },
  Pepper__bell___healthy: {
    title: 'Healthy Bell Pepper',
    summary: 'The model did not detect a visible disease pattern in the uploaded pepper leaf.',
    symptoms: ['Even green leaf color', 'No major spotting or lesions', 'Normal leaf shape'],
    causes: ['Healthy plant tissue', 'Low visible disease pressure'],
    nextSteps: ['Keep monitoring new growth', 'Water at the soil level', 'Maintain good airflow around plants']
  },
  Potato___Early_blight: {
    title: 'Potato Early Blight',
    summary: 'A fungal disease that often starts on older potato leaves and forms brown target-like spots.',
    symptoms: ['Brown circular spots with ring patterns', 'Yellowing around lesions', 'Older lower leaves affected first'],
    causes: ['Fungal spores in soil or debris', 'Leaf wetness and humidity', 'Plant stress'],
    nextSteps: ['Remove infected leaves', 'Avoid overhead irrigation', 'Mulch to reduce soil splash', 'Rotate potatoes and related crops']
  },
  Potato___Late_blight: {
    title: 'Potato Late Blight',
    summary: 'A serious water mold disease that can spread rapidly and damage leaves, stems, and tubers.',
    symptoms: ['Large dark water-soaked patches', 'White fuzzy growth under leaves in humid weather', 'Rapid leaf collapse'],
    causes: ['Cool, wet conditions', 'Wind-blown spores', 'Infected volunteer plants or tubers'],
    nextSteps: ['Isolate and remove affected foliage', 'Keep leaves dry where possible', 'Check nearby plants often', 'Seek local extension guidance if spreading']
  },
  Potato___healthy: {
    title: 'Healthy Potato',
    summary: 'The model did not detect a visible disease pattern in the uploaded potato leaf.',
    symptoms: ['Consistent green color', 'No major necrotic spots', 'Normal leaf texture'],
    causes: ['Healthy plant tissue', 'No obvious visual disease signs'],
    nextSteps: ['Continue routine monitoring', 'Avoid wet foliage overnight', 'Rotate planting areas each season']
  },
  Tomato_Bacterial_spot: {
    title: 'Tomato Bacterial Spot',
    summary: 'A bacterial disease that produces dark specks or spots and is favored by wet, warm weather.',
    symptoms: ['Small dark spots on leaves', 'Yellowing around spots', 'Rough dark spots on fruit'],
    causes: ['Splashing water', 'Contaminated tools or transplants', 'Warm, humid conditions'],
    nextSteps: ['Remove infected leaves', 'Avoid touching wet plants', 'Water at the base', 'Disinfect tools after pruning']
  },
  Tomato_Early_blight: {
    title: 'Tomato Early Blight',
    summary: 'A common fungal disease that usually begins on lower tomato leaves with brown target-like lesions.',
    symptoms: ['Brown spots with concentric rings', 'Yellowing lower leaves', 'Leaves drying and dropping early'],
    causes: ['Fungal spores in plant debris', 'Soil splash', 'High humidity and stressed plants'],
    nextSteps: ['Remove lower infected leaves', 'Mulch soil surface', 'Improve airflow with pruning', 'Rotate away from tomatoes and potatoes']
  },
  Tomato_Late_blight: {
    title: 'Tomato Late Blight',
    summary: 'A fast-moving disease that can cause large dark lesions and rapid plant decline in wet weather.',
    symptoms: ['Large greasy-looking leaf patches', 'Dark stem lesions', 'White growth on leaf undersides in humidity'],
    causes: ['Cool, wet weather', 'Airborne spores', 'Nearby infected tomato or potato plants'],
    nextSteps: ['Remove affected plants if infection is severe', 'Do not compost infected tissue', 'Keep foliage dry', 'Check local disease alerts']
  },
  Tomato_Leaf_Mold: {
    title: 'Tomato Leaf Mold',
    summary: 'A fungal disease common in humid, poorly ventilated growing areas such as greenhouses.',
    symptoms: ['Yellow patches on upper leaf surfaces', 'Olive-gray mold under leaves', 'Leaves curling and drying'],
    causes: ['High humidity', 'Poor airflow', 'Crowded plants'],
    nextSteps: ['Increase ventilation', 'Prune crowded foliage', 'Avoid wetting leaves', 'Remove heavily affected leaves']
  },
  Tomato_Septoria_leaf_spot: {
    title: 'Tomato Septoria Leaf Spot',
    summary: 'A fungal leaf spot disease that creates many small circular spots and often starts low on the plant.',
    symptoms: ['Many small round spots', 'Gray or tan centers with dark edges', 'Yellowing and leaf drop'],
    causes: ['Fungal spores on debris', 'Rain splash', 'Wet foliage'],
    nextSteps: ['Remove infected lower leaves', 'Mulch below plants', 'Water the soil directly', 'Clean plant debris after harvest']
  },
  Tomato_Spider_mites_Two_spotted_spider_mite: {
    title: 'Tomato Two-Spotted Spider Mite',
    summary: 'A mite pest problem that causes stippling, bronzing, and weakening of tomato leaves.',
    symptoms: ['Tiny pale speckles on leaves', 'Fine webbing under leaves', 'Bronzed or dry leaf surfaces'],
    causes: ['Hot, dry conditions', 'Mite buildup on leaf undersides', 'Stressed plants'],
    nextSteps: ['Rinse leaf undersides with water', 'Remove badly damaged leaves', 'Reduce plant stress', 'Consider insecticidal soap if needed']
  },
  Tomato__Target_Spot: {
    title: 'Tomato Target Spot',
    summary: 'A fungal disease that forms circular lesions and can affect leaves, stems, and fruit.',
    symptoms: ['Brown circular leaf spots', 'Target-like rings in larger lesions', 'Yellowing and premature leaf drop'],
    causes: ['Warm, humid weather', 'Dense foliage', 'Spores surviving on debris'],
    nextSteps: ['Prune for airflow', 'Remove infected debris', 'Avoid overhead watering', 'Rotate crops when replanting']
  },
  Tomato__Tomato_YellowLeaf__Curl_Virus: {
    title: 'Tomato Yellow Leaf Curl Virus',
    summary: 'A viral disease commonly spread by whiteflies that causes curling, yellowing, and stunted tomato growth.',
    symptoms: ['Upward curled leaves', 'Yellow leaf edges', 'Stunted growth and reduced fruit set'],
    causes: ['Whitefly transmission', 'Infected transplants', 'Nearby infected host plants'],
    nextSteps: ['Control whiteflies early', 'Remove severely infected plants', 'Use insect netting where practical', 'Choose resistant varieties in future plantings']
  },
  Tomato__Tomato_mosaic_virus: {
    title: 'Tomato Mosaic Virus',
    summary: 'A viral disease that can create mottled leaf color, distortion, and reduced plant vigor.',
    symptoms: ['Mosaic light and dark green pattern', 'Leaf curling or distortion', 'Stunted growth'],
    causes: ['Contaminated hands or tools', 'Infected seed or plant material', 'Mechanical spread between plants'],
    nextSteps: ['Remove severely affected plants', 'Wash hands before handling plants', 'Disinfect tools', 'Avoid tobacco contact around tomatoes']
  },
  Tomato_healthy: {
    title: 'Healthy Tomato',
    summary: 'The model did not detect a visible disease pattern in the uploaded tomato leaf.',
    symptoms: ['Uniform green color', 'No strong spotting pattern', 'Normal leaf structure'],
    causes: ['Healthy plant tissue', 'No obvious visual disease signs'],
    nextSteps: ['Keep checking lower leaves', 'Water at soil level', 'Prune lightly for airflow', 'Watch for new spots after wet weather']
  }
}

const getDiagnosisInfo = (className) => (
  DIAGNOSIS_INFO[className] || {
    title: className.replaceAll('_', ' '),
    summary: 'No detailed diagnosis notes are available for this class yet.',
    symptoms: ['Review the uploaded image for visible spotting, curling, discoloration, or pest damage'],
    causes: ['The predicted class may need a custom diagnosis entry'],
    nextSteps: ['Compare with field symptoms', 'Retake the photo in clear light if uncertain', 'Ask a local plant specialist for confirmation']
  }
)

const getDisplayPrediction = (result) => {
  if (!result) return null

  const topK = (result.top_k || []).filter((item) => !IGNORED_PREDICTION_CLASSES.has(item.class))
  const primary = IGNORED_PREDICTION_CLASSES.has(result.predicted_class)
    ? topK[0]
    : { class: result.predicted_class, confidence: result.confidence }

  return {
    primary,
    topK
  }
}

export default function App() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const onFileChange = (e) => {
    const f = e.target.files[0]
    if (!f) return
    setFile(f)
    setPreview(URL.createObjectURL(f))
    setResult(null)
    setError(null)
  }

  const onPredict = async () => {
    if (!file) return setError('Choose an image first')
    setLoading(true)
    setError(null)
    setResult(null)

    const form = new FormData()
    form.append('file', file)
    form.append('top_k', '5')

    try {
      const res = await fetch(BACKEND_DEFAULT + '/predict?grad_cam=true', { method: 'POST', body: form })
      if (!res.ok) {
        const txt = await res.text()
        throw new Error(txt || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setResult(data)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  const displayPrediction = getDisplayPrediction(result)
  const diagnosis = displayPrediction?.primary ? getDiagnosisInfo(displayPrediction.primary.class) : null

  return (
    <main className="site-shell">
      <section className="hero" id="top">
        <video className="hero-video" src={landingVideo} autoPlay muted loop playsInline />
        <div className="hero-overlay" />
        <nav className="topbar" aria-label="Primary">
          <a className="brand" href="#top">LeafGuard</a>
          {/* <a className="nav-link" href="#model">Model</a>
          <a className="nav-link" href="#predictor">Try it</a> */}
        </nav>
        <div className="hero-content">
          <p className="eyebrow">Plant disease detection</p>
          <h1>Identify leaf disease from a single image.</h1>
          <p className="hero-copy">
            Upload a crop leaf photo and the model returns the most likely disease class,
            confidence score, top alternatives, and a Grad-CAM heatmap for visual context.
          </p>
          <a className="hero-action" href="#predictor">Start diagnosis</a>
        </div>
      </section>

      <section className="model-section" id="model">
        <div className="section-inner model-grid">
          <div>
            <p className="section-kicker">About the model</p>
            <h2>A trained CNN for plant leaf classification.</h2>
          </div>
          <div className="model-copy">
            <p>
              This application uses a saved Keras model trained on labeled plant leaf images.
              It resizes uploaded leaves to the model input size, normalizes the image, and
              predicts across the available disease and healthy crop classes.
            </p>
            <p>
              Results include the top matching classes and a heatmap that highlights image
              regions contributing to the prediction. Use the output as decision support,
              not as a replacement for expert field diagnosis.
            </p>
          </div>
        </div>
      </section>

      <section className="predictor-section" id="predictor">
        <div className="section-inner">
          <div className="predictor-heading">
            <p className="section-kicker">Run a prediction</p>
            <h2>Upload a clear leaf image.</h2>
          </div>

          <div className="predictor-card">
            <div className="upload-panel">
              <label className="file-drop">
                <input type="file" accept="image/*" onChange={onFileChange} />
                <span className="file-title">{file ? file.name : 'Choose leaf image'}</span>
                <span className="file-subtitle">JPG or PNG, photographed in good light</span>
              </label>
              <button className="predict-button" onClick={onPredict} disabled={loading}>
                {loading ? 'Analyzing...' : 'Predict disease'}
              </button>
              {error && <div className="error">{error}</div>}
            </div>

            <div className="images-container">
              <div className="image-slot">
                <h3>Original Image</h3>
                {preview ? (
                  <img src={preview} alt="Uploaded leaf preview" />
                ) : (
                  <div className="empty-state">Image preview appears here</div>
                )}
              </div>

              <div className="image-slot">
                <h3>Explainability Heatmap</h3>
                {result && result.heatmap ? (
                  <img src={`data:image/jpeg;base64,${result.heatmap}`} alt="Grad-CAM heatmap" />
                ) : (
                  <div className="empty-state">Heatmap appears after prediction</div>
                )}
              </div>
            </div>

            {loading && <p className="status">Processing request...</p>}

            {result && (
              <>
                <div className="result">
                  <div>
                    <span className="result-label">Predicted class</span>
                    {displayPrediction?.primary ? (
                      <div className="predicted">
                        {displayPrediction.primary.class} <span>{(displayPrediction.primary.confidence * 100).toFixed(1)}%</span>
                      </div>
                    ) : (
                      <div className="predicted">No valid class found</div>
                    )}
                  </div>
                  <div className="top-results">
                    <h3>Top {displayPrediction.topK.length}</h3>
                    <ul>
                      {displayPrediction.topK.map((t, i) => (
                        <li key={i}>
                          <span>{t.class}</span>
                          <strong>{(t.confidence * 100).toFixed(1)}%</strong>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {diagnosis && (
                <div className="diagnosis-panel">
                  <div className="diagnosis-summary">
                    <span className="result-label">Diagnosis notes</span>
                    <h3>{diagnosis.title}</h3>
                    <p>{diagnosis.summary}</p>
                  </div>
                  <div className="diagnosis-grid">
                    <div>
                      <h4>What to check</h4>
                      <ul>
                        {diagnosis.symptoms.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    </div>
                    <div>
                      <h4>Common causes</h4>
                      <ul>
                        {diagnosis.causes.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    </div>
                    <div>
                      <h4>Suggested next steps</h4>
                      <ul>
                        {diagnosis.nextSteps.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    </div>
                  </div>
                  <p className="diagnosis-note">
                    This guidance is educational and should be confirmed with field symptoms or a local agricultural expert.
                  </p>
                </div>
                )}
              </>
            )}
          </div>
        </div>
      </section>

      <footer className="site-footer">
        <div className="section-inner footer-grid">
          <div>
            <a className="footer-brand" href="#top">LeafGuard AI</a>
            <p>
              A plant disease detection interface powered by a saved Keras model and
              Grad-CAM visual explanations.
            </p>
          </div>
          <div className="footer-links">
            <a href="#model">Model overview</a>
            <a href="#predictor">Upload image</a>
            
          </div>
        </div>
      </footer>
    </main>
  )
}
