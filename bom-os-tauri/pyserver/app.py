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
  const [selectedRowIndex, setSelectedRowIndex] = useState<number | null>(null)

  const handleProcess = async () => {
    setStatus('Przetwarzanie...')
    try {
      const data = await postJSON('http://127.0.0.1:5005/process', {
        stany: null, bomy: null, minimum: null, sprzedaz: null
      })
      setRows(data.rows || [])
      setSelectedRowIndex(null)
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
    if (selectedRowIndex === null) {
      setStatus('Błąd: Proszę zaznaczyć wiersz w tabeli, aby wygenerować prognozę.')
      return
    }
    setStatus('Prognozowanie...')
    try {
      const selectedRow = rows[selectedRowIndex]
      if (!selectedRow) throw new Error('Brak danych w zaznaczonym wierszu')
      const indeks = selectedRow?.indeks
      const stan = selectedRow?.stan ?? 0
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
        <table cellPadding={6} style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', background: '#f6f8fa' }}>
              {rows[0] && Object.keys(rows[0]).map(key => <th key={key} style={{ padding: '8px' }}>{key}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={i}
                onClick={() => setSelectedRowIndex(i)}
                style={{
                  cursor: 'pointer',
                  backgroundColor: selectedRowIndex === i ? '#e0f7fa' : 'transparent'
                }}
              >
                {Object.keys(rows[0] || {}).map(k => <td key={k + i} style={{ padding: '8px', borderBottom: '1px solid #eee' }}>{String(r[k])}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <pre style={{ background:'#f6f8fa', padding:12, borderRadius:8, marginTop: 12 }}>
        {JSON.stringify(aiInfo, null, 2)}
      </pre>
    </div>
  )
}
