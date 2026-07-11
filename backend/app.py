import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from database import get_db_connection, init_db
from ai_engine import analyze_answer, generate_questions

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend'))
# Enable CORS for all routes (important for static frontend setups)
CORS(app)

# Ensure the database exists and has schema/seeds before starting
db_file = os.path.join(os.path.dirname(__file__), 'interview.db')
if not os.path.exists(db_file):
    print("Database not found. Initializing database...")
    init_db()

# Serve the frontend static files
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/api/roles', methods=['GET'])
def get_roles():
    """Returns the list of job categories available in the question bank."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT role FROM questions")
        roles = [row['role'] for row in cursor.fetchall()]
        conn.close()
        return jsonify({"roles": roles})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/questions', methods=['GET'])
def get_questions():
    """Fetches a set of random questions (typically 3) for the selected role.
    If no questions exist for the role in the database, generates them using AI."""
    role = request.args.get('role', 'Software Engineer')
    limit = request.args.get('limit', 3, type=int)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, role, category, question_text, optimal_keywords, expected_concepts, difficulty "
            "FROM questions WHERE role = ? ORDER BY RANDOM() LIMIT ?", 
            (role, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        
        # If we have enough questions, return them
        if len(rows) >= limit:
            questions = []
            for r in rows:
                questions.append({
                    "id": r["id"],
                    "role": r["role"],
                    "category": r["category"],
                    "question_text": r["question_text"],
                    "difficulty": r["difficulty"]
                })
            return jsonify({"questions": questions})
        
        # If not enough questions in DB, generate via AI
        print(f"Not enough questions for '{role}' in DB. Generating via AI...")
        try:
            ai_questions = generate_questions(role, limit)
            return jsonify({"questions": ai_questions, "ai_generated": True})
        except Exception as ai_error:
            print(f"AI generation failed: {ai_error}. Using available DB questions.")
            questions = []
            for r in rows:
                questions.append({
                    "id": r["id"],
                    "role": r["role"],
                    "category": r["category"],
                    "question_text": r["question_text"],
                    "difficulty": r["difficulty"]
                })
            return jsonify({"questions": questions})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/submit-interview', methods=['POST'])
def submit_interview():
    """
    Submits a completed interview session. Grades each answer transcript,
    calculates summary metrics, and saves the session to SQLite.
    """
    data = request.json
    if not data:
        return jsonify({"error": "Missing payload"}), 400
        
    role = data.get('role')
    user_answers = data.get('answers')  # List of {question_id: int, transcript: string, question_text: string, category: string}
    user_id = data.get('user_id', 1)  # Default demo user

    if not role or not user_answers:
        return jsonify({"error": "Missing role or answers"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        graded_answers = []
        total_score = 0.0

        for answer in user_answers:
            question_id = answer.get('question_id')
            transcript = answer.get('transcript', '')
            question_text = answer.get('question_text', '')
            category = answer.get('category', 'Behavioral')
            optimal_keywords = answer.get('optimal_keywords', '')
            expected_concepts = answer.get('expected_concepts', '')

            # Try to get question details from DB if available
            if question_id:
                cursor.execute(
                    "SELECT question_text, category, optimal_keywords, expected_concepts "
                    "FROM questions WHERE id = ?", (question_id,)
                )
                q = cursor.fetchone()
                if q:
                    question_text = q["question_text"]
                    category = q["category"]
                    optimal_keywords = q["optimal_keywords"]
                    expected_concepts = q["expected_concepts"]

            # Run AI analysis
            feedback = analyze_answer(
                question_text=question_text,
                category=category,
                optimal_keywords=optimal_keywords,
                expected_concepts=expected_concepts,
                transcript=transcript
            )

            score = float(feedback["score"])
            total_score += score

            graded_answers.append({
                "question_id": question_id,
                "question_text": question_text,
                "category": category,
                "transcript": transcript,
                "score": score,
                "feedback": feedback
            })

        # Calculate average score
        overall_score = round(total_score / len(graded_answers), 1) if graded_answers else 0.0

        # Generate overall summary paragraph dynamically based on score
        if overall_score >= 85:
            summary = f"Excellent performance! You exhibited deep clarity and domain mastery in the {role} role. Your response delivery was highly fluent with negligible hesitation."
        elif overall_score >= 70:
            summary = f"Strong performance for {role}. Your core concepts are solid. However, you could improve by eliminating structural filler words and grounding your answers with specific trade-offs or quantitative results."
        else:
            summary = f"Decent starting point, but significant improvement is needed for {role} interviews. Focus on expanding response length, structuring your thoughts clearly (using the STAR method), and revising key domain terminology."

        # Save to interviews table
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO interviews (user_id, role, date, overall_score, summary) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, role, date_str, overall_score, summary)
        )
        interview_id = cursor.lastrowid

        # Save all answers
        for ga in graded_answers:
            cursor.execute(
                "INSERT INTO answers (interview_id, question_id, transcript, feedback_json, score) "
                "VALUES (?, ?, ?, ?, ?)",
                (interview_id, ga["question_id"], ga["transcript"], json.dumps(ga["feedback"]), ga["score"])
            )

        conn.commit()
        conn.close()

        return jsonify({
            "interview_id": interview_id,
            "overall_score": overall_score,
            "summary": summary,
            "date": date_str,
            "answers": graded_answers
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auto-grade', methods=['POST'])
def auto_grade():
    """
    Real-time auto-grading endpoint. Grades a single answer transcript immediately
    without requiring full interview submission. Used for live feedback during practice.
    """
    data = request.json
    if not data:
        return jsonify({"error": "Missing payload"}), 400

    transcript = data.get('transcript', '')
    question_text = data.get('question_text', '')
    category = data.get('category', 'Behavioral')
    optimal_keywords = data.get('optimal_keywords', '')
    expected_concepts = data.get('expected_concepts', '')

    if not transcript or not question_text:
        return jsonify({"error": "Missing transcript or question_text"}), 400

    try:
        feedback = analyze_answer(
            question_text=question_text,
            category=category,
            optimal_keywords=optimal_keywords,
            expected_concepts=expected_concepts,
            transcript=transcript
        )

        return jsonify({
            "score": feedback["score"],
            "clarity": feedback["clarity"],
            "grammar": feedback["grammar"],
            "relevance": feedback["relevance"],
            "filler_count": feedback["filler_count"],
            "strengths": feedback["strengths"],
            "weaknesses": feedback["weaknesses"],
            "tips": feedback["tips"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """
    Assembles metrics for the dashboard home screen:
    - User stats
    - Historical score progress
    - Category scoring averages (Behavioral vs Technical)
    - Average crutch word frequency
    - Past interviews list
    """
    user_id = request.args.get('user_id', 1, type=int)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get User details
        cursor.execute("SELECT name, target_role FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            return jsonify({"error": "User not found"}), 404
        
        user_info = {
            "name": user_row["name"],
            "target_role": user_row["target_role"]
        }

        # Get total interviews and average score
        cursor.execute("SELECT COUNT(*), AVG(overall_score) FROM interviews WHERE user_id = ?", (user_id,))
        stats = cursor.fetchone()
        total_interviews = stats[0] or 0
        avg_score = round(stats[1], 1) if stats[1] else 0.0

        # Get score progression over time
        cursor.execute(
            "SELECT id, role, date, overall_score FROM interviews "
            "WHERE user_id = ? ORDER BY date ASC", (user_id,)
        )
        history_rows = cursor.fetchall()
        
        progression = []
        history_list = []
        for r in history_rows:
            # Format date for cleaner display in charts
            raw_date = datetime.strptime(r["date"], '%Y-%m-%d %H:%M:%S')
            formatted_date = raw_date.strftime('%b %d, %Y')
            
            progression.append({
                "interview_id": r["id"],
                "date": formatted_date,
                "score": r["overall_score"]
            })
            
            history_list.append({
                "id": r["id"],
                "role": r["role"],
                "date": formatted_date,
                "overall_score": r["overall_score"]
            })

        # Reverse history list so latest shows first in recent logs
        history_list.reverse()

        # Get category analytics (Behavioral vs Technical vs Situational averages)
        cursor.execute(
            "SELECT q.category, AVG(a.score) as avg_score "
            "FROM answers a "
            "JOIN questions q ON a.question_id = q.id "
            "JOIN interviews i ON a.interview_id = i.id "
            "WHERE i.user_id = ? "
            "GROUP BY q.category", (user_id,)
        )
        cat_rows = cursor.fetchall()
        categories = {row["category"]: round(row["avg_score"], 1) for row in cat_rows}

        # Ensure both keys exist in category metrics
        if "Behavioral" not in categories:
            categories["Behavioral"] = 0.0
        if "Technical" not in categories:
            categories["Technical"] = 0.0
        if "Situational" not in categories:
            categories["Situational"] = 0.0

        # Aggregate average filler words and subscore breakdowns (Clarity, Grammar, Relevance)
        cursor.execute(
            "SELECT a.feedback_json FROM answers a "
            "JOIN interviews i ON a.interview_id = i.id "
            "WHERE i.user_id = ?", (user_id,)
        )
        ans_rows = cursor.fetchall()
        
        total_fillers = 0
        total_clarity = 0.0
        total_grammar = 0.0
        total_relevance = 0.0
        feedback_count = len(ans_rows)

        for row in ans_rows:
            fb = json.loads(row["feedback_json"])
            total_fillers += fb.get("filler_count", 0)
            total_clarity += fb.get("clarity", 0)
            total_grammar += fb.get("grammar", 0)
            total_relevance += fb.get("relevance", 0)

        subscores = {
            "clarity": round(total_clarity / feedback_count, 1) if feedback_count else 0.0,
            "grammar": round(total_grammar / feedback_count, 1) if feedback_count else 0.0,
            "relevance": round(total_relevance / feedback_count, 1) if feedback_count else 0.0,
            "avg_fillers_per_answer": round(total_fillers / feedback_count, 1) if feedback_count else 0.0
        }

        conn.close()

        return jsonify({
            "user": user_info,
            "metrics": {
                "total_interviews": total_interviews,
                "average_score": avg_score,
                "subscores": subscores,
                "categories": categories
            },
            "progression": progression,
            "history": history_list[:5] # returns last 5
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/interview/<int:interview_id>', methods=['GET'])
def get_interview_detail(interview_id):
    """Fetches details and graded questions/answers for a specific interview."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch basic interview info
        cursor.execute(
            "SELECT id, role, date, overall_score, summary FROM interviews WHERE id = ?",
            (interview_id,)
        )
        i_row = cursor.fetchone()
        if not i_row:
            conn.close()
            return jsonify({"error": "Interview not found"}), 404

        raw_date = datetime.strptime(i_row["date"], '%Y-%m-%d %H:%M:%S')
        formatted_date = raw_date.strftime('%B %d, %Y at %I:%M %p')

        interview_data = {
            "id": i_row["id"],
            "role": i_row["role"],
            "date": formatted_date,
            "overall_score": i_row["overall_score"],
            "summary": i_row["summary"],
            "answers": []
        }

        # Fetch answers for this interview
        cursor.execute(
            "SELECT a.id, a.transcript, a.score, a.feedback_json, q.question_text, q.category "
            "FROM answers a "
            "JOIN questions q ON a.question_id = q.id "
            "WHERE a.interview_id = ?",
            (interview_id,)
        )
        answer_rows = cursor.fetchall()
        for r in answer_rows:
            interview_data["answers"].append({
                "id": r["id"],
                "question_text": r["question_text"],
                "category": r["category"],
                "transcript": r["transcript"],
                "score": r["score"],
                "feedback": json.loads(r["feedback_json"])
            })

        conn.close()
        return jsonify(interview_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the local development server on port 5000, accessible from network
    app.run(host='0.0.0.0', port=5000, debug=True)