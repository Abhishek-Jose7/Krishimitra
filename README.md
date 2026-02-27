# KrishiMitra AI 🌾

AI-powered decision support system for Indian farmers.

## Features
- **Yield Prediction**: Estimate crop output based on soil & weather.
- **Price Forecasting**: 90-day price trend analysis.
- **Smart Selling**: Recommendation on when to sell for max profit.
- **Mandi Prices**: Compare nearby market rates.
- **Farmer Profile**: Personalized data management.

## Setup Instructions

### Option 1: Docker (Recommended)
If you have Docker installed:
```bash
docker compose up --build
```
(Note: Use `docker compose` instead of `docker-compose` on newer versions).

### Option 2: Local Python Setup (Fallback)
If Docker is not installed, run the backend manually:

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
5. **Run Backend**:
   ```bash
   # Generate models first
   python models/generate_dummy_models.py
   # Run app
   python app.py
   ```

### 3. Mobile App (Flutter)
Can run on Android Emulator or Windows Desktop.

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
- `backend/`: Flask API, Models, Services.
- `mobile_app/`: Flutter source code.
