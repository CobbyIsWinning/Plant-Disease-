const backendDefault = (window.backendUrl && window.backendUrl !== '') ? window.backendUrl : 'http://localhost:8000';
const backendUrl = backendDefault;
document.getElementById('backendUrl').textContent = backendUrl + '/predict';

const fileInput = document.getElementById('fileInput');
const predictBtn = document.getElementById('predictBtn');
const preview = document.getElementById('preview');
const result = document.getElementById('result');
const prediction = document.getElementById('prediction');
const topk = document.getElementById('topk');
const errorBox = document.getElementById('error');

let selectedFile = null;
fileInput.addEventListener('change', (e) => {
  const f = e.target.files[0];
  if (!f) return;
  selectedFile = f;
  const url = URL.createObjectURL(f);
  preview.innerHTML = `<img src="${url}" alt="preview">`;
  result.classList.add('hidden');
  errorBox.classList.add('hidden');
});

predictBtn.addEventListener('click', async () => {
  if (!selectedFile) {
    errorBox.textContent = 'Please select an image first.';
    errorBox.classList.remove('hidden');
    return;
  }
  errorBox.classList.add('hidden');
  prediction.textContent = 'Thinking...';
  topk.innerHTML = '';
  result.classList.remove('hidden');

  const form = new FormData();
  form.append('file', selectedFile);
  form.append('top_k', '5');

  try {
    const res = await fetch(backendUrl + '/predict', { method: 'POST', body: form });
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(txt || `HTTP ${res.status}`);
    }
    const data = await res.json();
    prediction.textContent = `${data.predicted_class} — ${(data.confidence*100).toFixed(1)}%`;
    topk.innerHTML = data.top_k.map(t => `<li>${t.class}: ${(t.confidence*100).toFixed(1)}%</li>`).join('');
  } catch (err) {
    errorBox.textContent = err.message || String(err);
    errorBox.classList.remove('hidden');
    result.classList.add('hidden');
  }
});