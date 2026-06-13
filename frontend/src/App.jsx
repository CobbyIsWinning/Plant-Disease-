import React, { useState } from 'react'
import landingVideo from './landingvideo.mp4'

const BACKEND_DEFAULT = 'http://localhost:8000'

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

  return (
    <main className="site-shell">
      <section className="hero" id="top">
        <video className="hero-video" src={landingVideo} autoPlay muted loop playsInline />
        <div className="hero-overlay" />
        <nav className="topbar" aria-label="Primary">
          <a className="brand" href="#top">LeafGuard</a>
          <a className="nav-link" href="#model">Model</a>
          <a className="nav-link" href="#predictor">Try it</a>
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
              <div className="result">
                <div>
                  <span className="result-label">Predicted class</span>
                  <div className="predicted">
                    {result.predicted_class} <span>{(result.confidence * 100).toFixed(1)}%</span>
                  </div>
                </div>
                <div className="top-results">
                  <h3>Top {result.top_k.length}</h3>
                  <ul>
                    {result.top_k.map((t, i) => (
                      <li key={i}>
                        <span>{t.class}</span>
                        <strong>{(t.confidence * 100).toFixed(1)}%</strong>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
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
            <span>Backend: {BACKEND_DEFAULT}/predict</span>
          </div>
        </div>
      </footer>
    </main>
  )
}
