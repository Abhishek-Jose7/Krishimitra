## KrishiMitra AI

AI-powered decision support system for Indian farmers.

## Features
- **Yield Prediction**: Estimate crop output based on soil & weather.
- **Price Forecasting**: 90-day price trend analysis.
- **Smart Selling**: Recommendation on when to sell for max profit.
- **Mandi Prices**: Compare nearby market rates.
- **Farmer Profile**: Personalized data management.

## Setup Instructions

### Option 1: Docker (Recommended — backend + DB)
If you have Docker installed and only need the backend + database:
```bash
docker compose up --build
```
(Note: Use `docker compose` instead of `docker-compose` on newer versions).

The Flask API will be available at `http://localhost:5000`.

### Option 2: Local Python Setup (Flask backend)
Run the Flask backend manually (used by the Flutter app).

1. **Install PostgreSQL**: Ensure PostgreSQL is running locally.
2. **Setup DB**: Create a database named `krishimitra`.
3. **Configure**: Update `backend/config.py` or exporting `DATABASE_URL`.
   ```bash
   # Windows PowerShell
   $env:DATABASE_URL="postgresql://postgres:password@localhost:5432/krishimitra"
   ```
4. **Install Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
   - Note: `backend/requirements.txt` is compatible with **Python 3.13** (uses binary wheels for scikit-learn on Windows).
5. **Run Backend**:
   ```bash
   # Generate models first
   python models/generate_dummy_models.py
   # Run app
   python app.py
   ```

### Option 3: Yield Prediction + Simulation API (FastAPI)
The yield prediction model lives in `backend/mysuru_agri_ai/` and exposes a FastAPI service.

From the `backend/` folder:

```bash
pip install -r mysuru_agri_ai/requirements.txt
uvicorn mysuru_agri_ai.app.main:app --reload --port 8000
```

Key endpoints:
- `GET /options`: valid dropdown options derived from CSV data
- `POST /predict-yield`: predict yield for a single scenario (JSON in/out)
- `POST /simulate`: simulate many scenarios and return a plain-text advisory report
- `GET /model-info`: model metadata (version, feature spec)

### Frontend + Backend (Flutter + Flask)
Run backend and Flutter app together.

1. **Start backend (Flask)** in one terminal:
   ```bash
   cd backend
   pip install -r requirements.txt
   # optional but recommended: train/load ML models & dependencies
   pip install -r mysuru_agri_ai/requirements.txt
   python models/generate_dummy_models.py
   python app.py
   ```

2. **Start mobile app (Flutter)** in another terminal:

   ```bash
   cd mobile_app
   flutter pub get
   # Run on Windows desktop
   flutter run -d windows
   # OR run on Android (if emulator is open)
   flutter run
   ```

   - **Android Emulator**: app connects to `10.0.2.2:5000`
   - **Windows Desktop**: app connects to `localhost:5000` (ensure backend is running)

3. **Yield advisory endpoint used by Flutter**:

   - Method: `POST /yield/simulate`
   - Example request body:
     ```json
     {
       "district": "Mysuru",
       "crop": "Rice",
       "season": "Kharif",
       "soil_type": "Black",
       "irrigation": "Canal",
       "area": 2.5
     }
     ```
   - Example success response:
     ```json
     {
       "status": "success",
       "advisory": "After analysing ... (human-readable text)"
     }
     ```

### 3. Mobile App (Flutter only)
Can run on Android Emulator or Windows Desktop if backend is already running.

```bash
cd mobile_app
flutter pub get
# Run on Windows
flutter run -d windows
# OR Run on Android (if emulator is open)
flutter run
```
**Note for Android Emulator**: The app connects to `10.0.2.2:5000`.
**Note for Windows**: The app connects to `localhost:5000` (Ensure backend is running).

## Project Structure
- `backend/`: Flask API + services + ML assets.
- `mobile_app/`: Flutter source code.
- `csv/`: datasets / exported CSVs.

### File structure (high-level)

```text
Krishimitra/
  backend/
    app.py
    config.py
    requirements.txt
    routes/
    services/
    models/
    database/
    mysuru_agri_ai/
      app/
        main.py
      pipeline/
        train.py
        predict.py
        preprocess.py
      models/
      data/
      requirements.txt
  mobile_app/
  csv/
  docker-compose.yml
  README.md
  CODEBASE_DOCUMENTATION.md
```
