import os
import json
import re
from dotenv import load_dotenv

# Load env variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
    except ImportError:
        print("Warning: google-generativeai package not found. Falling back to local NLP analysis.")
        GEMINI_API_KEY = None

def analyze_answer(question_text, category, optimal_keywords, expected_concepts, transcript):
    """
    Main entrypoint for grading answers. Checks if Gemini is available, otherwise falls back to local NLP engine.
    """
    if not transcript or len(transcript.strip()) == 0:
        return {
            "score": 0,
            "clarity": 0,
            "grammar": 0,
            "relevance": 0,
            "filler_count": 0,
            "strengths": ["None (No response provided)"],
            "weaknesses": ["You did not provide a transcript response."],
            "tips": ["Make sure to speak clearly into your microphone to record your response."]
        }

    if GEMINI_API_KEY:
        try:
            return analyze_with_gemini(question_text, category, optimal_keywords, expected_concepts, transcript)
        except Exception as e:
            print(f"Gemini API analysis failed: {e}. Falling back to local NLP engine.")
            return analyze_locally(question_text, category, optimal_keywords, expected_concepts, transcript)
    else:
        return analyze_locally(question_text, category, optimal_keywords, expected_concepts, transcript)

def analyze_with_gemini(question_text, category, optimal_keywords, expected_concepts, transcript):
    import google.generativeai as genai
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert AI Job Interviewer. Analyze the following candidate's answer to the given question.
    
    Question: {question_text}
    Category: {category}
    Expected Keywords/Concepts: {optimal_keywords} | {expected_concepts}
    Candidate's Transcript: "{transcript}"
    
    Evaluate the response and output a JSON object EXACTLY in the following format. Ensure all values are filled. Do not include any markdown wrappers or backticks in the response. Output raw JSON only.
    
    Format:
    {{
        "score": <overall score integer between 0 and 100>,
        "clarity": <clarity/structure score integer between 0 and 100>,
        "grammar": <grammar/vocabulary score integer between 0 and 100>,
        "relevance": <relevance/technical accuracy score integer between 0 and 100>,
        "filler_count": <integer representing count of filler words like 'uh', 'um', 'like', 'actually', 'so' used unnecessary as crutches>,
        "strengths": [<list of 2-3 specific strengths of this response>],
        "weaknesses": [<list of 1-2 constructive weaknesses or missed points>],
        "tips": [<list of 2-3 actionable tips for improvement (e.g. using the STAR method for behavioral, or describing trade-offs for technical)>]
    }}
    """
    
    response = model.generate_content(prompt)
    response_text = response.text.strip()
    
    # Strip markdown code blocks if the model wrapped it in ```json ... ```
    if response_text.startswith("```"):
        # Match anything inside backticks
        match = re.search(r"```(?:json)?(.*?)```", response_text, re.DOTALL)
        if match:
            response_text = match.group(1).strip()
            
    # Try parsing
    try:
        data = json.loads(response_text)
        # Validate keys
        required_keys = ["score", "clarity", "grammar", "relevance", "filler_count", "strengths", "weaknesses", "tips"]
        if all(k in data for k in required_keys):
            return data
    except Exception as parse_error:
        print(f"Error parsing Gemini response JSON: {parse_error}. Response content: {response_text}")
        
    # Fallback if parsing failed
    return analyze_locally(question_text, category, optimal_keywords, expected_concepts, transcript)

def generate_questions(role, count=3):
    """
    Generates interview questions for a given role using Gemini AI.
    Falls back to template-based questions if AI is unavailable.
    """
    if GEMINI_API_KEY:
        try:
            return generate_questions_with_gemini(role, count)
        except Exception as e:
            print(f"Gemini question generation failed: {e}. Using template fallback.")
            return generate_questions_locally(role, count)
    else:
        return generate_questions_locally(role, count)

def generate_questions_with_gemini(role, count=3):
    import google.generativeai as genai
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert interview question generator. Generate {count} interview questions for a candidate applying for a "{role}" position.
    
    For each question, provide:
    1. The question text
    2. The category (one of: Behavioral, Technical, Situational)
    3. Optimal keywords that should appear in a good answer (comma-separated)
    4. Expected concepts that should be covered (comma-separated)
    5. Difficulty level (one of: Easy, Medium, Hard)
    
    Output a JSON array EXACTLY in the following format. Do not include any markdown wrappers or backticks. Output raw JSON only.
    
    Format:
    [
        {{
            "question_text": "The interview question text here",
            "category": "Behavioral",
            "optimal_keywords": "keyword1, keyword2, keyword3",
            "expected_concepts": "concept1, concept2, concept3",
            "difficulty": "Medium"
        }},
        ...
    ]
    """
    
    response = model.generate_content(prompt)
    response_text = response.text.strip()
    
    # Strip markdown code blocks if the model wrapped it
    if response_text.startswith("```"):
        match = re.search(r"```(?:json)?(.*?)```", response_text, re.DOTALL)
        if match:
            response_text = match.group(1).strip()
    
    try:
        data = json.loads(response_text)
        if isinstance(data, list):
            # Add id and role fields
            for i, q in enumerate(data):
                q["id"] = -(i + 1)  # Use negative IDs for AI-generated questions
                q["role"] = role
                if "category" not in q:
                    q["category"] = "Behavioral"
                if "difficulty" not in q:
                    q["difficulty"] = "Medium"
                if "optimal_keywords" not in q:
                    q["optimal_keywords"] = ""
                if "expected_concepts" not in q:
                    q["expected_concepts"] = ""
            return data[:count]
    except Exception as e:
        print(f"Error parsing Gemini generated questions JSON: {e}")
    
    return generate_questions_locally(role, count)

def generate_questions_locally(role, count=3):
    """
    Template-based question generation for roles not in the database.
    Creates relevant questions based on the role name.
    """
    templates = [
        {
            "category": "Behavioral",
            "question": f"Tell me about a time you demonstrated leadership skills in a {role} context. What was the outcome?",
            "keywords": "leadership, team, outcome, initiative, responsibility",
            "concepts": "Leadership experience, team collaboration, measurable results, initiative"
        },
        {
            "category": "Behavioral",
            "question": f"Describe a challenging situation you faced as a {role} and how you overcame it.",
            "keywords": "challenge, problem-solving, solution, adaptation, result",
            "concepts": "Problem-solving, resilience, critical thinking, adaptability"
        },
        {
            "category": "Technical",
            "question": f"What are the most important skills and tools for a {role} to master, and why?",
            "keywords": "skills, tools, proficiency, expertise, best practices",
            "concepts": "Domain knowledge, tool proficiency, industry best practices, continuous learning"
        },
        {
            "category": "Situational",
            "question": f"You are working as a {role} and your team misses a critical deadline. How do you handle the situation?",
            "keywords": "deadline, accountability, communication, recovery, plan",
            "concepts": "Crisis management, accountability, team communication, process improvement"
        },
        {
            "category": "Behavioral",
            "question": f"Describe a time you had to learn a new skill or tool quickly to succeed in a {role} position.",
            "keywords": "learning, adaptation, skill development, initiative, growth",
            "concepts": "Learning agility, self-development, initiative, adaptability"
        },
        {
            "category": "Technical",
            "question": f"What metrics or KPIs do you consider most important when evaluating success in a {role} position?",
            "keywords": "metrics, KPI, evaluation, success, measurement, performance",
            "concepts": "Performance measurement, analytical thinking, results orientation, domain metrics"
        },
        {
            "category": "Situational",
            "question": f"As a {role}, you are given a project with limited resources and a tight deadline. How do you prioritize?",
            "keywords": "prioritization, resource management, deadline, efficiency, trade-offs",
            "concepts": "Resource allocation, priority setting, time management, strategic thinking"
        },
        {
            "category": "Behavioral",
            "question": f"Tell me about a time you received constructive criticism in a {role} role. How did you respond and grow from it?",
            "keywords": "feedback, improvement, growth, reflection, adaptation",
            "concepts": "Receptiveness to feedback, continuous improvement, self-awareness, professional growth"
        },
    ]
    
    # Shuffle and pick requested count
    import random
    random.shuffle(templates)
    selected = templates[:count]
    
    questions = []
    for i, t in enumerate(selected):
        questions.append({
            "id": -(i + 1),
            "role": role,
            "question_text": t["question"],
            "category": t["category"],
            "optimal_keywords": t["keywords"],
            "expected_concepts": t["concepts"],
            "difficulty": "Medium"
        })
    
    return questions

def analyze_locally(question_text, category, optimal_keywords, expected_concepts, transcript):
    """
    Rule-based local NLP grading logic. Evaluates filler words, length, keyword matching, and readability.
    """
    words = transcript.lower().split()
    word_count = len(words)
    
    # 1. Count filler words
    filler_words = ["um", "uh", "like", "actually", "basically", "so", "you know", "sort of", "stuff"]
    filler_count = 0
    # Simple check for phrases and standalone words
    transcript_lower = transcript.lower()
    for filler in filler_words:
        # Match word boundaries
        matches = re.findall(rf"\b{re.escape(filler)}\b", transcript_lower)
        filler_count += len(matches)

    # 2. Check keywords match
    keyword_list = [k.strip().lower() for k in optimal_keywords.split(",")] if optimal_keywords else []
    matches_found = []
    for kw in keyword_list:
        if re.search(rf"\b{re.escape(kw)}\b", transcript_lower):
            matches_found.append(kw)
            
    keyword_match_ratio = len(matches_found) / len(keyword_list) if keyword_list else 1.0

    # 3. Calculate scores
    # Relevance Score: based on keyword matching
    relevance = int(40 + (keyword_match_ratio * 60))
    if word_count < 15:
        relevance = max(10, relevance - 30)

    # Clarity Score: based on length stability and filler word frequency relative to total words
    filler_ratio = filler_count / max(1, word_count)
    filler_penalty = min(40, int(filler_ratio * 150))
    
    if word_count < 25:
        clarity = 50 - filler_penalty
    elif word_count > 250:
        clarity = 85 - filler_penalty  # Slight penalty for rambling
    else:
        clarity = 95 - filler_penalty
    clarity = max(20, min(100, clarity))

    # Grammar & Vocabulary Score: base check for sentences, length, filler words
    grammar = max(30, min(100, 95 - filler_penalty - (5 if word_count < 15 else 0)))

    # Overall Score: weighted average
    if category == "Technical":
        score = int((relevance * 0.5) + (clarity * 0.3) + (grammar * 0.2))
    else:
        score = int((relevance * 0.3) + (clarity * 0.4) + (grammar * 0.3))

    # Cap scores
    score = max(0, min(100, score))
    relevance = max(0, min(100, relevance))
    clarity = max(0, min(100, clarity))
    grammar = max(0, min(100, grammar))

    # 4. Generate Strengths, Weaknesses, Tips dynamically
    strengths = []
    weaknesses = []
    tips = []

    # Strengths
    if word_count >= 40:
        strengths.append("Provided a detailed explanation with good response length.")
    else:
        strengths.append("Answer was concise and direct.")
        
    if len(matches_found) >= 2:
        strengths.append(f"Successfully integrated key terminology: {', '.join(matches_found[:3])}.")
    else:
        strengths.append("Presented structured layout flow.")

    if filler_count <= 2:
        strengths.append("Spoke fluently with minimal crutch words.")

    # Weaknesses
    if word_count < 30:
        weaknesses.append("Response was too brief, missing opportunities to elaborate on details.")
    elif word_count > 250:
        weaknesses.append("Rambled slightly, which reduced the impact and conciseness of the main point.")

    if len(matches_found) < len(keyword_list) / 2:
        missed = [k for k in keyword_list if k not in matches_found]
        if missed:
            weaknesses.append(f"Missed addressing core concepts like: {', '.join(missed[:2])}.")

    if filler_count > 5:
        weaknesses.append(f"Used a high volume of crutch words ({filler_count} detected), making the delivery sound hesitant.")

    # Ensure we always have at least one weakness/strength
    if not weaknesses:
        weaknesses.append("Minor lack of specific metrics or quantitative details in the response.")
        
    # Tips
    if category == "Behavioral":
        tips.append("Use the STAR method: describe the Situation, Task, Action you took, and final quantitative Result.")
        tips.append("Focus more on your individual contributions using 'I' statements rather than general 'we' statements.")
    else:
        tips.append("Whenever describing technical terms, explicitly state the engineering tradeoffs (pros/cons) of your approach.")
        tips.append("Use a real-world project example to illustrate this concept in action.")

    if filler_count > 3:
        tips.append("Practice pausing silently instead of using verbal filler words when organizing your next sentence.")

    return {
        "score": score,
        "clarity": clarity,
        "grammar": grammar,
        "relevance": relevance,
        "filler_count": filler_count,
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:2],
        "tips": tips[:3]
    }
