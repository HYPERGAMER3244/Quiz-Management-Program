from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
import mysql.connector
from mysql.connector import Error
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-12345'

# MySQL Database Configuration
def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='quiz_app',
            user='root',
            password='qqcc@$qqcc'
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Initialize database tables
def init_db():
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()            
            # Create users table (simplified without full_name and email)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(100) NOT NULL,
                    role ENUM('student', 'teacher') NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create quizzes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quizzes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    quiz_id VARCHAR(50) UNIQUE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    questions JSON NOT NULL,
                    created_by VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(username)
                )
            """)
            
            # Create results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL,
                    quiz_id VARCHAR(50) NOT NULL,
                    score INT NOT NULL,
                    total INT NOT NULL,
                    detailed_results JSON,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (username) REFERENCES users(username),
                    FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id)
                )
            """)
            
            # Insert default users if they don't exist
            cursor.execute("SELECT COUNT(*) FROM users WHERE username IN ('admin', 'student')")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", 
                              ('admin', 'admin123', 'teacher'))
                cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", 
                              ('student', 'student123', 'student'))
            
            connection.commit()
            print("Database initialized successfully")
            
        except Error as e:
            print(f"Error initializing database: {e}")
        finally:
            cursor.close()
            connection.close()

# Load users from database
def load_users():
    users = {}
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT username, password, role FROM users")
            for row in cursor.fetchall():
                users[row['username']] = {
                    'password': row['password'],
                    'role': row['role']
                }
        except Error as e:
            print(f"Error loading users: {e}")
        finally:
            cursor.close()
            connection.close()
    return users

# Load quizzes from database
def load_quizzes():
    quizzes = {}
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT quiz_id, title, description, questions FROM quizzes")
            for row in cursor.fetchall():
                quizzes[row['quiz_id']] = {
                    'title': row['title'],
                    'description': row['description'],
                    'questions': json.loads(row['questions'])
                }
        except Error as e:
            print(f"Error loading quizzes: {e}")
        finally:
            cursor.close()
            connection.close()
    
    return quizzes

def save_quiz(quiz_id, title, description, questions, created_by):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            # Check if quiz exists
            cursor.execute("SELECT id FROM quizzes WHERE quiz_id = %s", (quiz_id,))
            if cursor.fetchone():
                # Update existing quiz
                cursor.execute("""
                    UPDATE quizzes 
                    SET title = %s, description = %s, questions = %s 
                    WHERE quiz_id = %s
                """, (title, description, json.dumps(questions), quiz_id))
            else:
                # Insert new quiz
                cursor.execute("""
                    INSERT INTO quizzes (quiz_id, title, description, questions, created_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (quiz_id, title, description, json.dumps(questions), created_by))
            connection.commit()
            return True
        except Error as e:
            print(f"Error saving quiz: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()
    return False

def delete_quiz_db(quiz_id):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM quizzes WHERE quiz_id = %s", (quiz_id,))
            connection.commit()
            return cursor.rowcount > 0
        except Error as e:
            print(f"Error deleting quiz: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()
    return False

def save_result(username, quiz_id, score, total, detailed_results):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO results (username, quiz_id, score, total, detailed_results)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, quiz_id, score, total, json.dumps(detailed_results)))
            connection.commit()
            return True
        except Error as e:
            print(f"Error saving result: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()
    return False

def has_attempted_quiz(username, quiz_id):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM results 
                WHERE username = %s AND quiz_id = %s
            """, (username, quiz_id))
            count = cursor.fetchone()[0]
            return count > 0
        except Error as e:
            print(f"Error checking quiz attempt: {e}")
            return False
        finally:
            cursor.close()
            connection.close()
    return False

def get_quiz_result(username, quiz_id):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT score, total, timestamp, detailed_results 
                FROM results 
                WHERE username = %s AND quiz_id = %s
            """, (username, quiz_id))
            return cursor.fetchone()
        except Error as e:
            print(f"Error getting quiz result: {e}")
            return None
        finally:
            cursor.close()
            connection.close()
    return None

def get_reports():
    reports = {}
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Get quiz attempts and average scores
            cursor.execute("""
                SELECT quiz_id, COUNT(*) as attempts, AVG(score) as avg_score
                FROM results 
                GROUP BY quiz_id
            """)
            for row in cursor.fetchall():
                reports[row['quiz_id']] = {
                    "attempts": row['attempts'],
                    "average_score": round(float(row['avg_score']), 2) if row['avg_score'] else 0
                }
            
            # Get top scorers for each quiz
            for quiz_id in reports:
                cursor.execute("""
                    SELECT username, MAX(score) as max_score 
                    FROM results 
                    WHERE quiz_id = %s 
                    GROUP BY username 
                    ORDER BY max_score DESC 
                    LIMIT 1
                """, (quiz_id,))
                top_scorer = cursor.fetchone()
                if top_scorer:
                    reports[quiz_id]["top_scorer"] = f"{top_scorer['username']} ({top_scorer['max_score']})"
                else:
                    reports[quiz_id]["top_scorer"] = "No attempts yet"
                    
        except Error as e:
            print(f"Error loading reports: {e}")
        finally:
            cursor.close()
            connection.close()
    
    return reports

def get_student_results():
    students = {}
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Get all students and their results
            cursor.execute("""
                SELECT u.username, r.quiz_id, r.score, r.total, r.timestamp, r.detailed_results
                FROM users u
                LEFT JOIN results r ON u.username = r.username
                WHERE u.role = 'student'
                ORDER BY u.username, r.timestamp DESC
            """)
            
            for row in cursor.fetchall():
                username = row['username']
                if username not in students:
                    students[username] = {
                        'quiz_attempts': {},
                        'total_score': 0,
                        'total_questions': 0
                    }
                
                if row['quiz_id']:
                    if row['quiz_id'] not in students[username]['quiz_attempts']:
                        students[username]['quiz_attempts'][row['quiz_id']] = []
                    
                    students[username]['quiz_attempts'][row['quiz_id']].append({
                        'score': row['score'],
                        'total': row['total'],
                        'timestamp': row['timestamp'],
                        'detailed_results': json.loads(row['detailed_results']) if row['detailed_results'] else []
                    })
                    
                    students[username]['total_score'] += row['score']
                    students[username]['total_questions'] += row['total']
                    
        except Error as e:
            print(f"Error loading student results: {e}")
        finally:
            cursor.close()
            connection.close()
    
    return students

# User management functions (simplified without full_name and email)
def add_user(username, password, role):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO users (username, password, role)
                VALUES (%s, %s, %s)
            """, (username, password, role))
            connection.commit()
            return True
        except Error as e:
            print(f"Error adding user: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()
    return False

def update_user(username, password, role):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            if password:
                cursor.execute("""
                    UPDATE users 
                    SET password = %s, role = %s
                    WHERE username = %s
                """, (password, role, username))
            else:
                cursor.execute("""
                    UPDATE users 
                    SET role = %s
                    WHERE username = %s
                """, (role, username))
            connection.commit()
            return True
        except Error as e:
            print(f"Error updating user: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()
    return False

def delete_user(username):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM users WHERE username = %s", (username,))
            connection.commit()
            return cursor.rowcount > 0
        except Error as e:
            print(f"Error deleting user: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()
    return False

# Initialize database when app starts
init_db()

@app.route('/')
def home():
    session.clear()
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_users()
        user = users.get(username)
        
        if user and user['password'] == password:
            session['username'] = username
            session['role'] = user['role']
            flash("Login successful", "success")
            
            # Redirect based on role
            if user['role'] == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('lobby'))
        
        flash("Invalid username or password", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/lobby')
def lobby():
    if 'username' not in session:
        return redirect(url_for('home'))
    
    quizzes = load_quizzes()
    
    # Check which quizzes the student has already attempted
    attempted_quizzes = {}
    if session.get('role') == 'student':
        for quiz_id in quizzes:
            attempted_quizzes[quiz_id] = has_attempted_quiz(session['username'], quiz_id)
    
    return render_template('lobby.html', quizzes=quizzes, attempted_quizzes=attempted_quizzes)

@app.route('/quiz/<quiz_id>')
def take_quiz(quiz_id):
    if 'username' not in session or session.get('role') != 'student':
        return redirect(url_for('home'))
    
    # Check if student has already attempted this quiz
    if has_attempted_quiz(session['username'], quiz_id):
        flash("You have already attempted this quiz. You cannot take it again.", "error")
        return redirect(url_for('lobby'))
    
    quizzes = load_quizzes()
    if quiz_id not in quizzes:
        flash("Quiz not found", "error")
        return redirect(url_for('lobby'))
    
    return render_template('quiz.html', quiz=quizzes[quiz_id], quiz_id=quiz_id)

@app.route('/quiz_result/<quiz_id>')
def quiz_result(quiz_id):
    if 'username' not in session or session.get('role') != 'student':
        return redirect(url_for('home'))
    
    # Get the quiz result
    result = get_quiz_result(session['username'], quiz_id)
    quizzes = load_quizzes()
    
    if not result or quiz_id not in quizzes:
        flash("Quiz result not found", "error")
        return redirect(url_for('lobby'))
    
    return render_template('quiz_result.html',
                         score=result['score'],
                         total=result['total'],
                         results=json.loads(result['detailed_results']) if result['detailed_results'] else [],
                         quiz_title=quizzes[quiz_id]['title'],
                         timestamp=result['timestamp'])

@app.route('/submit-quiz/<quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    # Check if student has already attempted this quiz
    if has_attempted_quiz(session['username'], quiz_id):
        flash("You have already attempted this quiz. You cannot submit it again.", "error")
        return redirect(url_for('lobby'))
    
    quizzes = load_quizzes()
    if quiz_id not in quizzes:
        return redirect(url_for('lobby'))
    
    quiz = quizzes[quiz_id]
    score = 0
    results = []
    
    for i, question in enumerate(quiz['questions']):
        # Use the correct naming convention that matches quiz.html
        user_answer = request.form.get(f'question_{i}')
        correct = question["correct"]
        is_correct = user_answer == correct
        
        results.append({
            "question": question["question"],
            "user_answer": user_answer,
            "correct_answer": correct,
            "is_correct": is_correct
        })
        
        if is_correct:
            score += 1
    
    # Save result to database with detailed results
    save_result(session['username'], quiz_id, score, len(quiz['questions']), results)
    
    return redirect(url_for('quiz_result', quiz_id=quiz_id))

# ================= TEACHER MODULE =================
@app.route('/teacher/dashboard')
def teacher_dashboard():
    if 'username' not in session or session.get('role') != 'teacher':
        return redirect(url_for('home'))
    
    quizzes = load_quizzes()
    return render_template('teacher/dashboard.html', quizzes=quizzes)

@app.route('/teacher/add-quiz', methods=['GET', 'POST'])
def add_quiz():
    if 'username' not in session or session.get('role') != 'teacher':
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        quiz_id = request.form.get('quiz_id', '').strip().lower()
        
        # Validate quiz ID
        if not quiz_id:
            flash("Quiz ID cannot be empty", "error")
            return redirect(url_for('add_quiz'))
        
        quizzes = load_quizzes()
        if quiz_id in quizzes:
            flash("Quiz ID already exists", "error")
            return redirect(url_for('add_quiz'))
        
        # Create new quiz
        success = save_quiz(
            quiz_id,
            request.form.get('title'),
            request.form.get('description'),
            [],
            session['username']
        )
        
        if success:
            flash("Quiz created successfully", "success")
            return redirect(url_for('edit_quiz', quiz_id=quiz_id))
        else:
            flash("Error creating quiz", "error")
    
    return render_template('teacher/add_quiz.html')

@app.route('/teacher/edit-quiz/<quiz_id>', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    if 'username' not in session or session.get('role') != 'teacher':
        return redirect(url_for('home'))
    
    quizzes = load_quizzes()
    
    if quiz_id not in quizzes:
        flash("Quiz not found", "error")
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        # Handle quiz metadata update
        if 'update_quiz' in request.form:
            success = save_quiz(
                quiz_id,
                request.form.get('title'),
                request.form.get('description'),
                quizzes[quiz_id]['questions'],
                session['username']
            )
            if success:
                flash("Quiz updated successfully", "success")
            else:
                flash("Error updating quiz", "error")
        
        # Handle question addition
        elif 'add_question' in request.form:
            # Get the option values directly
            option1 = request.form.get('option1')
            option2 = request.form.get('option2')
            option3 = request.form.get('option3')
            option4 = request.form.get('option4')
            
            # Get the correct option value, not just the key
            correct_option_key = request.form.get('correct_option')
            if correct_option_key == 'option1':
                correct_answer = option1
            elif correct_option_key == 'option2':
                correct_answer = option2
            elif correct_option_key == 'option3':
                correct_answer = option3
            elif correct_option_key == 'option4':
                correct_answer = option4
            else:
                correct_answer = option1  # Default to first option
            
            new_question = {
                "question": request.form.get('question'),
                "options": [option1, option2, option3, option4],
                "correct": correct_answer
            }
            
            quizzes[quiz_id]['questions'].append(new_question)
            success = save_quiz(
                quiz_id,
                quizzes[quiz_id]['title'],
                quizzes[quiz_id]['description'],
                quizzes[quiz_id]['questions'],
                session['username']
            )
            
            if success:
                flash("Question added successfully", "success")
            else:
                flash("Error adding question", "error")
        
        # Handle question deletion
        elif 'delete_question' in request.form:
            question_index = int(request.form.get('question_index', -1))
            if 0 <= question_index < len(quizzes[quiz_id]['questions']):
                quizzes[quiz_id]['questions'].pop(question_index)
                success = save_quiz(
                    quiz_id,
                    quizzes[quiz_id]['title'],
                    quizzes[quiz_id]['description'],
                    quizzes[quiz_id]['questions'],
                    session['username']
                )
                
                if success:
                    flash("Question deleted successfully", "success")
                else:
                    flash("Error deleting question", "error")
        
        return redirect(url_for('edit_quiz', quiz_id=quiz_id))
    
    return render_template('teacher/edit_quiz.html', quiz=quizzes[quiz_id], quiz_id=quiz_id)

@app.route('/teacher/delete-quiz/<quiz_id>')
def delete_quiz(quiz_id):
    if 'username' not in session or session.get('role') != 'teacher':
        return redirect(url_for('home'))
    
    success = delete_quiz_db(quiz_id)
    if success:
        flash("Quiz deleted successfully", "success")
    else:
        flash("Quiz not found or error deleting", "error")
    
    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher/reports')
def view_reports():
    if 'username' not in session or session.get('role') != 'teacher':
        return redirect(url_for('home'))
    
    reports = get_reports()
    student_results = get_student_results()
    
    return render_template('teacher/reports.html', reports=reports, student_results=student_results)

@app.route('/teacher/student-report/<username>')
def student_report(username):
    if 'username' not in session or session.get('role') != 'teacher':
        return redirect(url_for('home'))
    
    student_results = get_student_results()
    
    if username not in student_results:
        flash("Student not found or no results available", "error")
        return redirect(url_for('view_reports'))
    
    # Generate pie chart
    total_correct = student_results[username]['total_score']
    total_questions = student_results[username]['total_questions']
    total_incorrect = total_questions - total_correct
    
    if total_questions > 0:
        # Create pie chart
        labels = ['Correct Answers', 'Incorrect Answers']
        sizes = [total_correct, total_incorrect]
        colors = ['#4CAF50', '#F44336']
        explode = (0.1, 0)  # explode the 1st slice
        
        plt.figure(figsize=(8, 6))
        plt.pie(sizes, explode=explode, labels=labels, colors=colors, 
                autopct='%1.1f%%', shadow=True, startangle=90)
        plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        plt.title(f'Performance Overview for {username}')
        
        # Save plot to a bytes buffer
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png')
        img_buffer.seek(0)
        
        # Encode the image to base64
        img_data = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        plt.close()
    else:
        img_data = None
    
    return render_template('teacher/student_report.html', 
                         username=username, 
                         student_data=student_results[username],
                         chart_data=img_data)

# ================= USER MANAGEMENT MODULE =================
@app.route('/teacher/users')
def manage_users():
    if 'username' not in session or session.get('role') != 'teacher':
        return redirect(url_for('home'))
    
    users = load_users()
    return render_template('teacher/users.html', users=users)

@app.route('/teacher/add-user', methods=['GET', 'POST'])
def add_user_route():
    if 'username' not in session or session.get('role') != 'teacher':
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        # Validate input
        if not username or not password or not role:
            flash("Username, password, and role are required", "error")
            return redirect(url_for('add_user_route'))
        
        users = load_users()
        if username in users:
            flash("Username already exists", "error")
            return redirect(url_for('add_user_route'))
        
        # Add user
        success = add_user(username, password, role)
        if success:
            flash("User added successfully", "success")
            return redirect(url_for('manage_users'))
        else:
            flash("Error adding user", "error")
    
    # FIXED: Return the correct template for adding users
    return render_template('teacher/add_user.html')

@app.route('/teacher/edit-user/<username>', methods=['GET', 'POST'])
def edit_user(username):
    if 'username' not in session or session.get('role') != 'teacher':
        return redirect(url_for('home'))
    
    users = load_users()
    user = users.get(username)
    
    if not user:
        flash("User not found", "error")
        return redirect(url_for('manage_users'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        role = request.form.get('role')
        
        # Update user
        success = update_user(username, password, role)
        if success:
            flash("User updated successfully", "success")
            return redirect(url_for('manage_users'))
        else:
            flash("Error updating user", "error")
    
    return render_template('teacher/edit_user.html', user=user, username=username)

@app.route('/teacher/delete-user/<username>')
def delete_user_route(username):
    if 'username' not in session or session.get('role') != 'teacher':
        return redirect(url_for('home'))
    
    if username == session['username']:
        flash("You cannot delete your own account", "error")
        return redirect(url_for('manage_users'))
    
    success = delete_user(username)
    if success:
        flash("User deleted successfully", "success")
    else:
        flash("Error deleting user", "error")
    
    return redirect(url_for('manage_users'))

if __name__ == '__main__':
    app.run(debug=True)
