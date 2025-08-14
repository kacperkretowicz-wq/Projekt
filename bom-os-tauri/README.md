
# BOM OS – Tauri + React + Flask (Sidecar)

Ten projekt uruchamia frontend w Tauri/React i backend w Python/Flask jako sidecar.
Backend stara się korzystać z Twoich istniejących modułów (`ai_logic`, `forecasting_logic`,
`common.data_processing`, `pandas_model`, itd.). Dzięki temu możesz szybko zbudować `.exe`.

## Szybki start (dev)
1. **Wymagania**: Node 18+, Rust + Tauri CLI, Python 3.10–3.12.
2. Zainstaluj zależności frontendu:
   ```bash
   npm install
   ```
3. Zainstaluj zależności backendu:
   ```bash
   cd pyserver
   python -m venv .venv
   .venv/Scripts/activate  # Windows
   pip install -r requirements.txt
   cd ..
   ```
4. Dev (uruchamia React + Flask sidecar + Tauri):
   ```bash
   npm run tauri:dev
   ```

## Build `.exe`
### Opcja A (rekomendowana): spakuj Flask jako binarkę sidecar
1. W aktywnym venv:
   ```bash
   cd pyserver
   pyinstaller --onefile --name flask_sidecar --add-data ".;." app.py
   cd ..
   ```
   Binarka będzie w `pyserver/dist/flask_sidecar(.exe)`.

2. Zbuduj Tauri (dołączy sidecar automatycznie):
   ```bash
   npm run tauri:build
   ```

### Opcja B: używaj systemowego Pythona (dev/test)
W `tauri.conf.json` tryb dev odpala `python pyserver/app.py`. Dla produkcji **zalecane** jest
użycie opcji A (PyInstaller), aby nie wymagać zewnętrznego Pythona.

## Struktura
```
.
├─ src/                # React (Vite)
├─ src-tauri/          # Tauri (Rust)
├─ pyserver/           # Flask + integracja z Twoim kodem Pythona
└─ README.md
```

## Integracja z Twoim kodem
- Umieść swoje pliki/modele w `pyserver/` lub zainstaluj je jako pakiet w venv.
- Flask próbuje importować: `ai_logic`, `forecasting_logic`, `common.data_processing`.
  Jeżeli nie znajdzie – użyje łagodnych stubów, aby UI działał.

## Punkty API
- `POST /process` – łączy pliki wejściowe (stany/bomy/minimum/sprzedaz) i zwraca tabelę
- `POST /train` – trenuje i zapisuje model
- `POST /predict` – zwraca predykcje i/lub ważności cech
- `POST /forecast` – prognoza dla wskazanego indeksu
- `POST /export` – eksport danych do CSV (po stronie serwera)
- `GET /health` – status

Frontend używa fetch do tych endpointów.

Powodzenia! :)
