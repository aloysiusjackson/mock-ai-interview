# Mock AI Interview Prep Platform

An interactive, high-fidelity web application built for students and job seekers to practice job interviews. Features a dark-themed glassmorphism interface, responsive dashboard visualization charts, real-time speech-to-text transcribing, and AI-driven feedback grading.

## 🚀 Key Features

* **Responsive Dashboard:** Shows overall average scoring progress, total interviews completed, and crutch filler words tracking. Uses **Chart.js** to show progression line charts and subscore radar graphs.
* **Simulated Interview Room:** Complete with simulated camera overlays, active question teleprompter widgets, real-time timer readouts, and active visual voice wave pulses.
* **Built-in Speech-to-Text:** Uses the browser's native **Web Speech API** (`SpeechRecognition`) to transcribe answers in real-time, completely free of charge. Includes a manual text editor fallback.
* **Text-to-Speech Question Readout:** Reads the active interview questions out loud using the browser's synthesis engines.
* **AI Feedback Evaluator:** Grades each question response out of 100 on **Clarity**, **Grammar**, and **Relevance**. Generates bulleted lists of specific Strengths, Improvement Areas, and Actionable Tips.
* **Modular Grading Engine:** Runs immediately out of the box using a local rule-based NLP simulator. Can easily be updated to run full LLM evaluations using a Gemini API Key!
* **SQLite Persistence:** Keeps record history logs of all past mock interview sessions, questions, and detail results.

---

## 🛠️ Technology Stack

* **Frontend:** HTML5, Vanilla CSS3 (Custom Glassmorphism design system & cubic-bezier page transitions), JavaScript (Vanilla ES6).
* **Backend:** Python, Flask, Flask-CORS, SQLite.
* **Libraries:** Chart.js (Data rendering), python-dotenv, google-generativeai (Optional).

---

## 💻 Setup & Installation Instructions

Follow these steps to run the application on your computer:

### 1. Prerequisite Checklist
Make sure you have Python 3.8+ installed on your system.

### 2. Install Backend Python Dependencies
Navigate to the root directory and install dependencies:
```bash
pip install -r backend/requirements.txt
```

### 3. Initialize and Seed the Database
Initialize SQLite and pre-seed mock questions and historical stats:
```bash
python backend/database.py
```
This creates the SQLite file `backend/interview.db` and populates baseline interview data, so your dashboard charts display visual details instantly on startup.

### 4. Run the Flask Backend Server
Launch the local API server:
```bash
python backend/app.py
```
The server starts running locally on `http://127.0.0.1:5000`.

### 5. Launch the Frontend
You can open `frontend/index.html` directly in any web browser (Chrome, Edge, or Safari recommended for Speech-to-Text features).

Alternatively, you can serve the frontend files using a local HTTP server:
```bash
# Using python built-in server inside the frontend folder
cd frontend
python -m http.server 8000
```
Then navigate to `http://localhost:8000` in your browser.

---

## 🔑 Optional: Configure Gemini Live AI Grading

By default, the application runs on a local NLP grading engine that scans transcripts for keyword relevance, filler words count, and answer lengths. 

To enable advanced Gemini AI model evaluations:
1. Copy `.env.example` and rename it to `.env`:
   ```bash
   copy .env.example .env
   ```
2. Open `.env` and fill in your Gemini API key:
   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```
3. Restart your Flask application (`python backend/app.py`). The grading engine will automatically detect the key and switch to Gemini's LLM evaluation model.
