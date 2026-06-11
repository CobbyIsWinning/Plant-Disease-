import React, { useState } from 'react'

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
    <div className="container">
      <h1>Plant Disease Prediction</h1>
      <p>Upload a leaf image (jpg/png) and get a prediction from the backend.</p>

      <div className="controls">
        <input type="file" accept="image/*" onChange={onFileChange} />
        <button onClick={onPredict} disabled={loading}>Predict</button>
      </div>

      <div className="images-container">
        {preview && (
          <div className="preview">
            <h3>Original Image</h3>
            <img src={preview} alt="preview" />
          </div>
        )}

        {result && result.heatmap && (
          <div className="heatmap">
            <h3>Explainability (Heatmap)</h3>
            <img src={`data:image/jpeg;base64,${result.heatmap}`} alt="heatmap" />
          </div>
        )}
      </div>

      {loading && <p className="status">Processing request...</p>}

      {result && (
        <div className="result">
          <h2>Prediction</h2>
          <div className="predicted">{result.predicted_class} — {(result.confidence*100).toFixed(1)}%</div>
          <h3>Top {result.top_k.length}</h3>
          <ul>
            {result.top_k.map((t, i) => (
              <li key={i}>{t.class}: {(t.confidence*100).toFixed(1)}%</li>
            ))}
          </ul>
        </div>
      )}

      {error && (
        <div className="error">{error}</div>
      )}

      <footer>
        <small>Backend: {BACKEND_DEFAULT}/predict</small>
      </footer>
    </div>
  )
}
