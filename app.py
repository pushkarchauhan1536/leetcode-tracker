from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import json
import io
import os
import sqlite3
from datetime import datetime
import requests
import urllib3
import numpy as np
import hashlib
import secrets
import re
from collections import Counter

# Try to import pandas, but continue without it if not available
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
    print("✅ pandas available - upload/export features enabled")
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️ pandas not available - upload/export features disabled")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# ===============================
# 📁 DATABASE SETUP
# ===============================
DB_PATH = 'leetcode_tracker.db'
EXCEL_FILE = 'students.xlsx'

# def init_db():
#     """Create database and tables if they don't exist"""
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
    
#     # Students table
#     c.execute('''CREATE TABLE IF NOT EXISTS students
#                  (roll TEXT PRIMARY KEY,
#                   name TEXT NOT NULL,
#                   leetcode_ids TEXT,
#                   created_at TIMESTAMP)''')
    
#     conn.commit()
#     conn.close()
#     print("✅ Database initialized")
    
#     # Initialize courses and sections
#     init_courses_sections()


########################################################################
def init_db():
    """Create database and tables if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Students table (existing)
    c.execute('''CREATE TABLE IF NOT EXISTS students
                 (roll TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  leetcode_ids TEXT,
                  created_at TIMESTAMP)''')
    
    # NEW: Users table for authentication
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  full_name TEXT NOT NULL,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  role TEXT DEFAULT 'teacher',
                  created_at TIMESTAMP,
                  last_login TIMESTAMP)''')
    
    # NEW: Session table for tracking logins
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  session_token TEXT UNIQUE,
                  created_at TIMESTAMP,
                  expires_at TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized with authentication tables")
    
    # Initialize courses and sections
    init_courses_sections()
###################################################################################

# ===============================
# 📚 COURSE & SECTION MANAGEMENT
# ===============================

def init_courses_sections():
    """Initialize courses and sections tables with 2 sections per course"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Courses table
    c.execute('''CREATE TABLE IF NOT EXISTS courses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  course_name TEXT NOT NULL,
                  course_code TEXT UNIQUE,
                  created_at TIMESTAMP)''')
    
    # Sections table
    c.execute('''CREATE TABLE IF NOT EXISTS sections
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  course_id INTEGER NOT NULL,
                  section_name TEXT NOT NULL,
                  section_code TEXT,
                  FOREIGN KEY (course_id) REFERENCES courses(id),
                  UNIQUE(course_id, section_name))''')
    
    # Student-course mapping
    c.execute('''CREATE TABLE IF NOT EXISTS student_course_mapping
                 (student_roll TEXT,
                  section_id INTEGER,
                  assigned_at TIMESTAMP,
                  FOREIGN KEY (student_roll) REFERENCES students(roll),
                  FOREIGN KEY (section_id) REFERENCES sections(id),
                  PRIMARY KEY (student_roll, section_id))''')
    
    # Insert sample data if empty
    c.execute("SELECT COUNT(*) FROM courses")
    if c.fetchone()[0] == 0:
        courses_data = [
            ("MCA", "MCA"),
            ("B.Tech CSE", "CSE"),
            ("B.Tech ECE", "ECE"),
            ("B.Tech Civil Engineering", "CIVIL"),
            ("B.Tech IT", "IT"),
            ("B.Tech Mechanical Engineering", "ME"),
        ]
        
        for course_name, course_code in courses_data:
            c.execute("INSERT INTO courses (course_name, course_code, created_at) VALUES (?, ?, ?)",
                      (course_name, course_code, datetime.now()))
        
        c.execute("SELECT id, course_code FROM courses")
        courses = c.fetchall()
        
        for course_id, course_code in courses:
            if course_code == "MCA":
                sections = [(course_id, "MCA Section A", "MCA-A"), (course_id, "MCA Section B", "MCA-B")]
            elif course_code == "CSE":
                sections = [(course_id, "CSE Section A", "CSE-A"), (course_id, "CSE Section B", "CSE-B")]
            elif course_code == "ECE":
                sections = [(course_id, "ECE Section A", "ECE-A"), (course_id, "ECE Section B", "ECE-B")]
            elif course_code == "CIVIL":
                sections = [(course_id, "Civil Section A", "CIVIL-A"), (course_id, "Civil Section B", "CIVIL-B")]
            elif course_code == "IT":
                sections = [(course_id, "IT Section A", "IT-A"), (course_id, "IT Section B", "IT-B")]
            elif course_code == "ME":
                sections = [(course_id, "ME Section A", "ME-A"), (course_id, "ME Section B", "ME-B")]
            else:
                sections = [(course_id, f"{course_code} Section A", f"{course_code}-A"), (course_id, f"{course_code} Section B", f"{course_code}-B")]
            
            for section in sections:
                c.execute("INSERT INTO sections (course_id, section_name, section_code) VALUES (?, ?, ?)", section)
    
    conn.commit()
    conn.close()
    print("✅ Courses & Sections tables initialized")

def load_excel_to_db():
    """Auto-load students from Excel file to database"""
    if not PANDAS_AVAILABLE:
        print("⚠️ pandas not available - cannot load Excel file")
        return 0
    
    if not os.path.exists(EXCEL_FILE):
        print(f"⚠️ Warning: {EXCEL_FILE} not found.")
        return 0
    
    try:
        df = pd.read_excel(EXCEL_FILE)
        print(f"📊 Found Excel with columns: {list(df.columns)}")
        
        roll_col, name_col, ids_col = None, None, None
        for col in df.columns:
            col_lower = col.lower()
            if 'roll' in col_lower:
                roll_col = col
            elif 'name' in col_lower:
                name_col = col
            elif 'leetcode' in col_lower or 'ids' in col_lower or 'username' in col_lower:
                ids_col = col
        
        if not roll_col or not name_col or not ids_col:
            print(f"❌ Required columns not found.")
            return 0
        
        added_count = 0
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        for idx, row in df.iterrows():
            try:
                roll = str(row[roll_col]).strip()
                name = str(row[name_col]).strip()
                leetcode_str = str(row[ids_col]).strip()
                
                if not roll or not name or not leetcode_str:
                    continue
                
                ids_list = [i.strip() for i in leetcode_str.replace(',', ' ').split() if i.strip()]
                
                if ids_list:
                    c.execute('''INSERT OR REPLACE INTO students (roll, name, leetcode_ids, created_at) VALUES (?, ?, ?, ?)''',
                              (roll, name, json.dumps(ids_list), datetime.now()))
                    added_count += 1
                    print(f"   ✅ Loaded: {roll} - {name}")
            except Exception as e:
                print(f"   ⚠️ Row {idx + 2}: Error - {e}")
                continue
        
        conn.commit()
        conn.close()
        print(f"\n📊 Loaded {added_count} students from Excel")
        return added_count
    except Exception as e:
        print(f"❌ Error loading Excel: {e}")
        return 0

def fetch_leetcode_data(username):
    """Fetch LeetCode data for a username"""
    url = "https://leetcode.com/graphql"
    
    query = {
        "query": """
        query getUserProfile($username: String!) {
            matchedUser(username: $username) {
                submitStats: submitStatsGlobal {
                    acSubmissionNum {
                        difficulty
                        count
                    }
                }
                tagProblemCounts {
                    advanced { tagName problemsSolved }
                    intermediate { tagName problemsSolved }
                    fundamental { tagName problemsSolved }
                }
            }
        }
        """,
        "variables": {"username": username}
    }
    
    try:
        response = requests.post(url, json=query, headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}, verify=False, timeout=10)
        data = response.json()
        
        if not data or "data" not in data or not data["data"]["matchedUser"]:
            return {"error": "Invalid username"}
        
        user_data = data["data"]["matchedUser"]
        
        stats = {'Easy': 0, 'Medium': 0, 'Hard': 0, 'All': 0}
        for item in user_data["submitStats"]["acSubmissionNum"]:
            difficulty = item["difficulty"]
            if difficulty == "Easy":
                stats["Easy"] = item["count"]
            elif difficulty == "Medium":
                stats["Medium"] = item["count"]
            elif difficulty == "Hard":
                stats["Hard"] = item["count"]
        stats["All"] = stats["Easy"] + stats["Medium"] + stats["Hard"]
        
        topics = []
        for level in ["fundamental", "intermediate", "advanced"]:
            for tag in user_data["tagProblemCounts"][level]:
                topics.append({"tagName": tag["tagName"], "problemsSolved": tag["problemsSolved"]})
        
        return {"difficulty": stats, "topics": topics}
    except Exception as e:
        return {"error": str(e)}

# ===============================
# 🚀 API ROUTES
# ===============================

# @app.route('/')
# def index():
#     return render_template('index.html')

#############################################################################
@app.route('/')
def index():
    """Login/Signup page"""
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Protected dashboard page"""
    return render_template('dashboard.html')
######################################################################################3

@app.route('/integrity-ai')
def integrity_ai_page():
    """Render the IntegrityAI page"""
    return render_template('integrity-ai.html')

@app.route('/api/students')
def get_all_students():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT roll, name, leetcode_ids FROM students ORDER BY roll')
        rows = c.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            leetcode_ids = json.loads(row[2]) if row[2] else []
            easy, medium, hard = 0, 0, 0
            for username in leetcode_ids[:1]:
                data = fetch_leetcode_data(username)
                if 'error' not in data:
                    stats = data.get('difficulty', {})
                    easy = stats.get('Easy', 0)
                    medium = stats.get('Medium', 0)
                    hard = stats.get('Hard', 0)
            
            results.append({'roll': row[0], 'name': row[1], 'leetcode_ids': leetcode_ids, 'stats': {'All': easy + medium + hard, 'Easy': easy, 'Medium': medium, 'Hard': hard}})
        return jsonify(results)
    except Exception as e:
        return jsonify([])

@app.route('/api/student/<roll>')
def get_student(roll):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT name, leetcode_ids FROM students WHERE roll=?', (roll,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Student not found'}), 404
        
        leetcode_ids = json.loads(row[1]) if row[1] else []
        all_stats, all_topics = [], []
        
        for username in leetcode_ids:
            data = fetch_leetcode_data(username)
            if 'error' not in data:
                all_stats.append(data.get('difficulty', {}))
                all_topics.extend(data.get('topics', []))
        
        total_stats = {'Easy': 0, 'Medium': 0, 'Hard': 0, 'All': 0}
        for stats in all_stats:
            total_stats['Easy'] += stats.get('Easy', 0)
            total_stats['Medium'] += stats.get('Medium', 0)
            total_stats['Hard'] += stats.get('Hard', 0)
        total_stats['All'] = total_stats['Easy'] + total_stats['Medium'] + total_stats['Hard']
        
        topic_map = {}
        for topic in all_topics:
            topic_map[topic['tagName']] = topic_map.get(topic['tagName'], 0) + topic['problemsSolved']
        
        topics_list = [{'tagName': k, 'problemsSolved': v} for k, v in topic_map.items()]
        topics_list.sort(key=lambda x: x['problemsSolved'], reverse=True)
        weak_topics = [t['tagName'] for t in topics_list if t['problemsSolved'] < 5]
        
        return jsonify({'roll': roll, 'name': row[0], 'leetcode_ids': leetcode_ids, 'stats': total_stats, 'topics': topics_list, 'weak_topics': weak_topics})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/student', methods=['POST'])
def add_student():
    try:
        data = request.json
        roll = str(data.get('roll', '')).strip()
        name = str(data.get('name', '')).strip()
        leetcode_ids = data.get('leetcode_ids', [])
        
        if not roll or not name or not leetcode_ids:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if isinstance(leetcode_ids, str):
            leetcode_ids = [i.strip() for i in leetcode_ids.split(',') if i.strip()]
        
        valid_ids = []
        for username in leetcode_ids[:3]:
            test = fetch_leetcode_data(username.strip())
            if 'error' not in test:
                valid_ids.append(username.strip())
        
        if not valid_ids:
            valid_ids = leetcode_ids[:3]
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT roll FROM students WHERE roll=?', (roll,))
        exists = c.fetchone()
        c.execute('''INSERT OR REPLACE INTO students (roll, name, leetcode_ids, created_at) VALUES (?, ?, ?, ?)''', (roll, name, json.dumps(valid_ids), datetime.now()))
        conn.commit()
        conn.close()
        
        return jsonify({'message': f'Student {"updated" if exists else "added"} successfully!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/leaderboard')
def leaderboard():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT roll, name, leetcode_ids FROM students')
        rows = c.fetchall()
        conn.close()
        
        leaderboard_data = []
        for row in rows:
            leetcode_ids = json.loads(row[2]) if row[2] else []
            easy, medium, hard = 0, 0, 0
            for username in leetcode_ids[:1]:
                data = fetch_leetcode_data(username)
                if 'error' not in data:
                    stats = data.get('difficulty', {})
                    easy = stats.get('Easy', 0)
                    medium = stats.get('Medium', 0)
                    hard = stats.get('Hard', 0)
            
            total_solved = easy + medium + hard
            leaderboard_data.append({'roll': row[0], 'name': row[1], 'easy': easy, 'medium': medium, 'hard': hard, 'total_solved': total_solved})
        
        leaderboard_data.sort(key=lambda x: x['total_solved'], reverse=True)
        for i, student in enumerate(leaderboard_data, 1):
            student['rank'] = i
        
        return jsonify(leaderboard_data)
    except Exception as e:
        return jsonify([])

@app.route('/api/batch-analytics')
def batch_analytics():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT roll, name, leetcode_ids FROM students')
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            return jsonify({})
        
        total_students = len(rows)
        total_easy, total_medium, total_hard = 0, 0, 0
        student_names = []
        
        for row in rows[:20]:
            leetcode_ids = json.loads(row[2]) if row[2] else []
            student_names.append(row[1])
            for username in leetcode_ids[:1]:
                data = fetch_leetcode_data(username)
                if 'error' not in data:
                    stats = data.get('difficulty', {})
                    total_easy += stats.get('Easy', 0)
                    total_medium += stats.get('Medium', 0)
                    total_hard += stats.get('Hard', 0)
        
        analytics = {'Your Batch': {'students': student_names[:5], 'count': total_students, 'total_easy': total_easy, 'total_medium': total_medium, 'total_hard': total_hard, 'total_all': total_easy + total_medium + total_hard, 'avg_total': (total_easy + total_medium + total_hard) / total_students if total_students > 0 else 0, 'top_performer': rows[0][1] if rows else 'None'}}
        return jsonify(analytics)
    except Exception as e:
        return jsonify({})

@app.route('/api/export')
def export_data():
    if not PANDAS_AVAILABLE:
        return jsonify({'error': 'Export not available'}), 400
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT roll, name, leetcode_ids FROM students", conn)
        conn.close()
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Students', index=False)
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f'students_{datetime.now().strftime("%Y%m%d")}.xlsx')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/courses')
def get_courses():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, course_name, course_code FROM courses ORDER BY course_name")
        rows = c.fetchall()
        conn.close()
        return jsonify([{'id': row[0], 'name': row[1], 'code': row[2]} for row in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/courses/<int:course_id>/sections')
def get_sections(course_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, section_name, section_code FROM sections WHERE course_id = ? ORDER BY section_name", (course_id,))
        rows = c.fetchall()
        conn.close()
        return jsonify([{'id': row[0], 'name': row[1], 'code': row[2]} for row in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/section/<int:section_id>/dashboard')
def get_section_dashboard(section_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT s.id, s.section_name, s.section_code, c.course_name, c.course_code FROM sections s JOIN courses c ON s.course_id = c.id WHERE s.id = ?''', (section_id,))
        section_row = c.fetchone()
        if not section_row:
            return jsonify({'error': 'Section not found'}), 404
        
        c.execute('''SELECT s.roll, s.name, s.leetcode_ids FROM students s JOIN student_course_mapping scm ON s.roll = scm.student_roll WHERE scm.section_id = ?''', (section_id,))
        student_rows = c.fetchall()
        conn.close()
        
        students_data = []
        total_easy, total_medium, total_hard = 0, 0, 0
        
        for row in student_rows:
            leetcode_ids = json.loads(row[2]) if row[2] else []
            stats = {'Easy': 0, 'Medium': 0, 'Hard': 0}
            for username in leetcode_ids[:1]:
                data = fetch_leetcode_data(username)
                if 'error' not in data:
                    diff = data.get('difficulty', {})
                    stats['Easy'] = diff.get('Easy', 0)
                    stats['Medium'] = diff.get('Medium', 0)
                    stats['Hard'] = diff.get('Hard', 0)
            
            total_easy += stats['Easy']
            total_medium += stats['Medium']
            total_hard += stats['Hard']
            students_data.append({'roll': row[0], 'name': row[1], 'stats': stats})
        
        students_data.sort(key=lambda x: x['stats']['Easy'] + x['stats']['Medium'] + x['stats']['Hard'], reverse=True)
        for i, student in enumerate(students_data, 1):
            student['rank'] = i
        
        total_students = len(students_data)
        total_solved = total_easy + total_medium + total_hard
        
        return jsonify({'section': {'id': section_row[0], 'name': section_row[1], 'code': section_row[2], 'course_name': section_row[3], 'course_code': section_row[4]}, 'stats': {'total_students': total_students, 'total_easy': total_easy, 'total_medium': total_medium, 'total_hard': total_hard, 'total_solved': total_solved, 'avg_per_student': round(total_solved / total_students, 1) if total_students > 0 else 0}, 'leaderboard': students_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/assign-student', methods=['POST'])
def assign_student_to_section():
    try:
        data = request.json
        student_roll = data.get('student_roll')
        section_id = data.get('section_id')
        
        if not student_roll or not section_id:
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT roll FROM students WHERE roll = ?", (student_roll,))
        if not c.fetchone():
            conn.close()
            return jsonify({'error': 'Student not found'}), 404
        
        c.execute("SELECT id FROM sections WHERE id = ?", (section_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'error': 'Section not found'}), 404
        
        c.execute('''INSERT OR REPLACE INTO student_course_mapping (student_roll, section_id, assigned_at) VALUES (?, ?, ?)''', (student_roll, section_id, datetime.now()))
        conn.commit()
        conn.close()
        
        return jsonify({'message': f'Student assigned to section successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/section-assignments')
def get_all_assignments():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT scm.student_roll, s.name, sec.section_name, sec.section_code, c.course_name, c.course_code, scm.assigned_at, sec.id as section_id FROM student_course_mapping scm JOIN students s ON scm.student_roll = s.roll JOIN sections sec ON scm.section_id = sec.id JOIN courses c ON sec.course_id = c.id ORDER BY c.course_name, sec.section_name, s.name''')
        rows = c.fetchall()
        conn.close()
        
        assignments = [{'student_roll': row[0], 'student_name': row[1], 'section_name': row[2], 'section_code': row[3], 'course_name': row[4], 'course_code': row[5], 'assigned_at': row[6], 'section_id': row[7]} for row in rows]
        return jsonify(assignments)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/unassign-student', methods=['POST'])
def unassign_student():
    try:
        data = request.json
        student_roll = data.get('student_roll')
        section_id = data.get('section_id')
        
        if not student_roll:
            return jsonify({'error': 'Student roll required'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if section_id:
            c.execute("DELETE FROM student_course_mapping WHERE student_roll = ? AND section_id = ?", (student_roll, section_id))
        else:
            c.execute("DELETE FROM student_course_mapping WHERE student_roll = ?", (student_roll,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Student unassigned successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===============================
# 🧠 INTEGRITYAI - SMART STUDENT ANALYSIS
# ===============================

QUESTION_BANK = None

def load_question_bank():
    global QUESTION_BANK
    try:
        if not os.path.exists('merged_problems.json'):
            print("❌ merged_problems.json not found")
            QUESTION_BANK = []
            return False
        
        with open('merged_problems.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                QUESTION_BANK = data
            elif isinstance(data, dict) and 'questions' in data:
                QUESTION_BANK = data['questions']
            else:
                QUESTION_BANK = []
        
        print(f"✅ Loaded {len(QUESTION_BANK)} problems for IntegrityAI")
        return True
    except Exception as e:
        print(f"⚠️ Error loading question bank: {e}")
        QUESTION_BANK = []
        return False

def get_problems_by_topic(topic_name, limit=5, difficulty=None):
    if not QUESTION_BANK:
        return []
    
    matching_problems = []
    topic_lower = topic_name.lower()
    
    for problem in QUESTION_BANK:
        problem_topics = [t.lower() for t in problem.get('topics', [])]
        if topic_lower in problem_topics or any(topic_lower in pt or pt in topic_lower for pt in problem_topics):
            prob_difficulty = problem.get('difficulty', 'Medium')
            if difficulty is None or prob_difficulty == difficulty:
                matching_problems.append({
                    'id': problem.get('frontend_id', problem.get('problem_id')),
                    'name': problem.get('title'),
                    'difficulty': prob_difficulty,
                    'url': f"https://leetcode.com/problems/{problem.get('problem_slug')}/",
                    'reason': f"Practice this to improve your {topic_name} skills."
                })
    return matching_problems[:limit]

def get_fallback_recommendations(topic):
    fallback = {
        "Array": [{"id": 1, "name": "Two Sum", "difficulty": "Easy", "url": "https://leetcode.com/problems/two-sum/"}],
        "String": [{"id": 3, "name": "Longest Substring", "difficulty": "Medium", "url": "https://leetcode.com/problems/longest-substring-without-repeating-characters/"}],
        "Dynamic Programming": [{"id": 70, "name": "Climbing Stairs", "difficulty": "Easy", "url": "https://leetcode.com/problems/climbing-stairs/"}],
        "Graph": [{"id": 200, "name": "Number of Islands", "difficulty": "Medium", "url": "https://leetcode.com/problems/number-of-islands/"}],
        "Tree": [{"id": 104, "name": "Max Depth", "difficulty": "Easy", "url": "https://leetcode.com/problems/maximum-depth-of-binary-tree/"}]
    }
    for key in fallback:
        if key.lower() in topic.lower():
            return fallback[key]
    return [{"id": 1, "name": "Two Sum", "difficulty": "Easy", "url": "https://leetcode.com/problems/two-sum/"}]

@app.route('/api/integrity-ai/<roll>', methods=['GET'])
def integrity_ai_analysis(roll):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT name, leetcode_ids FROM students WHERE roll=?', (roll,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Student not found'}), 404
        
        name = row[0]
        leetcode_ids = json.loads(row[1]) if row[1] else []
        
        student_topics = {}
        easy_count = medium_count = hard_count = 0
        weak_topics = []
        strong_topics = []
        
        for username in leetcode_ids[:1]:
            data = fetch_leetcode_data(username)
            if 'error' not in data:
                stats = data.get('difficulty', {})
                easy_count = stats.get('Easy', 0)
                medium_count = stats.get('Medium', 0)
                hard_count = stats.get('Hard', 0)
                topics = data.get('topics', [])
                
                for topic in topics:
                    topic_name = topic['tagName']
                    solved = topic['problemsSolved']
                    student_topics[topic_name] = solved
                    if solved < 3:
                        weak_topics.append(topic_name)
                    elif solved > 10:
                        strong_topics.append(topic_name)
        
        total_solved = easy_count + medium_count + hard_count
        
        if total_solved < 20:
            skill_level = "Beginner"
            level_color = "#10b981"
            level_icon = "🌱"
        elif total_solved < 50:
            skill_level = "Intermediate"
            level_color = "#f59e0b"
            level_icon = "📈"
        elif total_solved < 100:
            skill_level = "Advanced"
            level_color = "#6366f1"
            level_icon = "🚀"
        else:
            skill_level = "Expert"
            level_color = "#8b5cf6"
            level_icon = "🏆"
        
        if not weak_topics:
            weak_topics = ["Dynamic Programming", "Graph", "Tree"]
        
        recommendations = {}
        for topic in weak_topics[:5]:
            easy_probs = get_problems_by_topic(topic, limit=2, difficulty='Easy')
            medium_probs = get_problems_by_topic(topic, limit=2, difficulty='Medium')
            hard_probs = get_problems_by_topic(topic, limit=1, difficulty='Hard')
            
            if not (easy_probs or medium_probs or hard_probs):
                fallback = get_fallback_recommendations(topic)
                easy_probs = [p for p in fallback if p['difficulty'] == 'Easy'][:2]
                medium_probs = [p for p in fallback if p['difficulty'] == 'Medium'][:2]
                hard_probs = [p for p in fallback if p['difficulty'] == 'Hard'][:1]
            
            recommendations[topic] = easy_probs + medium_probs + hard_probs
        
        total_topics = len(student_topics)
        mastered_topics = len([t for t in student_topics.values() if t >= 10])
        mastery_percentage = round((mastered_topics / total_topics * 100) if total_topics > 0 else 0, 1)
        
        insights = [
            {'type': 'info', 'icon': '📊', 'title': 'Performance Overview', 'message': f'Total {total_solved} problems solved. Keep going!'},
            {'type': 'warning' if weak_topics else 'success', 'icon': '⚠️' if weak_topics else '✅', 'title': 'Areas to Focus', 'message': f'Focus on: {", ".join(weak_topics[:3])}' if weak_topics else 'Great balance across topics!'}
        ]
        
        study_plan = {
            'daily_goal': '2-3 problems daily',
            'weekly_target': '15-20 problems per week',
            'focus_area': ', '.join(weak_topics[:3]),
            'weekly_schedule': [
                {'day': 'Monday', 'task': f'Practice {weak_topics[0] if weak_topics else "Arrays"} problems', 'problems': 2},
                {'day': 'Wednesday', 'task': f'Practice {weak_topics[1] if len(weak_topics) > 1 else "Strings"} problems', 'problems': 2},
                {'day': 'Friday', 'task': 'Review and solve difficult problems', 'problems': 1}
            ]
        }
        
        return jsonify({
            'student_name': name,
            'roll': roll,
            'stats': {'easy': easy_count, 'medium': medium_count, 'hard': hard_count, 'total': total_solved, 'skill_level': skill_level, 'level_color': level_color, 'level_icon': level_icon, 'mastery_percentage': mastery_percentage},
            'topics': {'weak': weak_topics[:8], 'strong': strong_topics[:5]},
            'recommendations': recommendations,
            'study_plan': study_plan,
            'insights': insights,
            'total_recommendations': sum(len(v) for v in recommendations.values())
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

load_question_bank()

###########################################################################################
# ===============================
# 📊 ACCEPTANCE RATE API
@app.route('/api/student/acceptance/<roll>')
def get_acceptance_rate(roll):
    """Get acceptance rate matching LeetCode's official calculation"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT leetcode_ids FROM students WHERE roll=?', (roll,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Student not found'}), 404
        
        leetcode_ids = json.loads(row[0]) if row[0] else []
        
        acceptance_data = []
        
        for username in leetcode_ids[:1]:
            url = "https://leetcode.com/graphql"
            
            query = {
                "query": """
                query getUserProfile($username: String!) {
                    matchedUser(username: $username) {
                        submitStats: submitStatsGlobal {
                            acSubmissionNum {
                                difficulty
                                count
                                submissions
                            }
                            totalSubmissionNum {
                                difficulty
                                count
                                submissions
                            }
                        }
                    }
                }
                """,
                "variables": {"username": username}
            }
            
            response = requests.post(url, json=query, headers={"Content-Type": "application/json"}, timeout=10)
            data = response.json()
            
            if data and "data" in data and data["data"]["matchedUser"]:
                ac_stats = data["data"]["matchedUser"]["submitStats"]["acSubmissionNum"]
                total_stats = data["data"]["matchedUser"]["submitStats"]["totalSubmissionNum"]
                
                # Create a map for total submissions by difficulty
                total_map = {}
                for item in total_stats:
                    total_map[item["difficulty"]] = item.get("submissions", 0)
                
                for item in ac_stats:
                    difficulty = item["difficulty"]
                    if difficulty == "All":
                        continue  # Skip "All" category
                    
                    accepted = item.get("submissions", 0)      # Total accepted submissions
                    solved_unique = item["count"]               # Unique problems solved
                    total = total_map.get(difficulty, 0)        # Total submissions
                    
                    acceptance_rate = round((accepted / total * 100), 1) if total > 0 else 0
                    
                    acceptance_data.append({
                        'difficulty': difficulty,
                        'solved': solved_unique,
                        'accepted_submissions': accepted,
                        'total_submissions': total,
                        'acceptance_rate': acceptance_rate
                    })
        
        if acceptance_data:
            total_accepted = sum(d['accepted_submissions'] for d in acceptance_data)
            total_submissions_all = sum(d['total_submissions'] for d in acceptance_data)
            overall_rate = round((total_accepted / total_submissions_all * 100), 1) if total_submissions_all > 0 else 0
        else:
            overall_rate = 0
        
        return jsonify({
            'roll': roll,
            'acceptance_data': acceptance_data,
            'overall_rate': overall_rate
        })
        
    except Exception as e:
        print(f"Acceptance API Error: {e}")
        return jsonify({'error': str(e), 'acceptance_data': []}), 500
# ===============================



#############################################################
# ===============================
# 🔐 AUTHENTICATION ROUTES
# ===============================



def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

def generate_session_token():
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """Register a new user"""
    try:
        data = request.json
        full_name = data.get('full_name', '').strip()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        role = data.get('role', 'teacher')
        
        if not all([full_name, username, email, password]):
            return jsonify({'error': 'All fields are required'}), 400
        
        if password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        is_valid, msg = validate_password(password)
        if not is_valid:
            return jsonify({'error': msg}), 400
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if c.fetchone():
            conn.close()
            return jsonify({'error': 'Username or email already exists'}), 400
        
        hashed_pw = hash_password(password)
        c.execute('''INSERT INTO users (full_name, username, email, password, role, created_at)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (full_name, username, email, hashed_pw, role, datetime.now()))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Account created successfully! Please login.', 'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user and create session"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, full_name, username, email, role, password FROM users WHERE username = ? OR email = ?", 
                  (username, username))
        user = c.fetchone()
        
        if not user or user[5] != hash_password(password):
            conn.close()
            return jsonify({'error': 'Invalid username or password'}), 401
        
        c.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.now(), user[0]))
        
        session_token = generate_session_token()
        expires_at = datetime.now().timestamp() + (7 * 24 * 60 * 60)
        
        c.execute('''INSERT INTO sessions (user_id, session_token, created_at, expires_at)
                     VALUES (?, ?, ?, ?)''',
                  (user[0], session_token, datetime.now(), datetime.fromtimestamp(expires_at)))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user[0],
                'full_name': user[1],
                'username': user[2],
                'email': user[3],
                'role': user[4]
            },
            'session_token': session_token
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user - invalidate session"""
    try:
        data = request.json
        session_token = data.get('session_token')
        
        if session_token:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))
            conn.commit()
            conn.close()
        
        return jsonify({'success': True, 'message': 'Logged out successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/verify', methods=['POST'])
def verify_session():
    """Verify if session token is valid"""
    try:
        data = request.json
        session_token = data.get('session_token')
        
        if not session_token:
            return jsonify({'valid': False}), 401
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT u.id, u.full_name, u.username, u.email, u.role 
                     FROM sessions s 
                     JOIN users u ON s.user_id = u.id 
                     WHERE s.session_token = ? AND s.expires_at > datetime('now')''', 
                  (session_token,))
        user = c.fetchone()
        conn.close()
        
        if user:
            return jsonify({
                'valid': True,
                'user': {
                    'id': user[0],
                    'full_name': user[1],
                    'username': user[2],
                    'email': user[3],
                    'role': user[4]
                }
            })
        else:
            return jsonify({'valid': False}), 401
            
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 401

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 LeetCode Tracker Starting...")
    print("="*50)
    init_db()
    if os.path.exists(EXCEL_FILE) and PANDAS_AVAILABLE:
        load_excel_to_db()
    print("\n" + "="*50)
    print("🌐 Server: http://127.0.0.1:5000")
    print("="*50 + "\n")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)