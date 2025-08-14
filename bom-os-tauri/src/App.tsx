
import React, { useState } from 'react'

type TableRow = Record<string, any>

async function postJSON(url: string, payload: any) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export default function App() {
  const [rows, setRows] = useState<TableRow[]>([])
  const [status, setStatus] = useState<string>('Gotowy')
  const [aiInfo, setAiInfo] = useState<any>(null)

  const handleProcess = async () => {
    setStatus('Przetwarzanie...')
    try {
      // w dev – podpinamy się do localhost:5005
      const data = await postJSON('http://127.0.0.1:5005/process', {
        stany: null, bomy: null, minimum: null, sprzedaz: null
      })
      setRows(data.rows || [])
      setStatus('OK')
    } catch (e:any) {
      setStatus(e.message)
    }
  }

  const handleTrain = async () => {
    setStatus('Trenowanie...')
    try {
      const data = await postJSON('http://127.0.0.1:5005/train', {})
      setAiInfo(data)
      setStatus('Model zaktualizowany')
    } catch (e:any) {
      setStatus(e.message)
    }
  }

  const handlePredict = async () => {
    setStatus('Predykcja...')
    try {
      const data = await postJSON('http://127.0.0.1:5005/predict', { rows })
      setRows(data.rows || rows)
      setAiInfo({ importances: data.importances || null })
      setStatus('Gotowe')
    } catch (e:any) {
      setStatus(e.message)
    }
  }

  const handleForecast = async () => {
    setStatus('Prognozowanie...')
    try {
      if (!rows.length) throw new Error('Brak danych')
      const indeks = rows[0]?.indeks
      const stan = rows[0]?.stan ?? 0
      const data = await postJSON('http://127.0.0.1:5005/forecast', { indeks, stan })
      setAiInfo({ forecast: data })
      setStatus('Gotowe')
    } catch (e:any) {
      setStatus(e.message)
    }
  }

  return (
    <div style={{ padding: 16, fontFamily: 'Inter, system-ui, sans-serif' }}>
      <h1>BOM OS – Dashboard (Tauri + React + Flask)</h1>
      <div style={{ display:'flex', gap:8, marginBottom:12 }}>
        <button onClick={handleProcess}>1. Przetwórz</button>
        <button onClick={handleTrain}>2. Trenuj AI</button>
        <button onClick={handlePredict}>3. Predykcja</button>
        <button onClick={handleForecast}>4. Prognoza</button>
      </div>
      <div style={{ marginBottom:12 }}>
        <strong>Status:</strong> {status}
      </div>

      <div style={{ maxHeight: 300, overflow: 'auto', border: '1px solid #ddd' }}>
        <table cellPadding={6}>
          <thead>
            <tr>{rows[0] && Object.keys(rows[0]).map(key => <th key={key}>{key}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {Object.keys(rows[0] || {}).map(k => <td key={k + i}>{String(r[k])}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <pre style={{ background:'#f6f8fa', padding:12, borderRadius:8 }}>
        {JSON.stringify(aiInfo, null, 2)}
      </pre>
    </div>
  )
}
