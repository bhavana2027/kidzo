from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import sqlite3
import json
import os
from datetime import datetime, date
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import io
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Database initialization
def init_db():
    conn = sqlite3.connect('kids_learning_app.db')
    cursor = conn.cursor()
    
    # Kids table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            avatar TEXT NOT NULL,
            language_preference TEXT DEFAULT 'english',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Progress table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kid_id INTEGER,
            module_name TEXT NOT NULL,
            lesson_id TEXT NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kid_id) REFERENCES kids (id)
        )
    ''')
    
    # Quiz results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kid_id INTEGER,
            module_name TEXT NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            attempt_number INTEGER DEFAULT 1,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kid_id) REFERENCES kids (id)
        )
    ''')
    
    # Badges table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kid_id INTEGER,
            badge_name TEXT NOT NULL,
            badge_icon TEXT NOT NULL,
            module_name TEXT NOT NULL,
            earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kid_id) REFERENCES kids (id)
        )
    ''')
    
    # Stories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kid_id INTEGER,
            title TEXT NOT NULL,
            character TEXT NOT NULL,
            place TEXT NOT NULL,
            magic_item TEXT NOT NULL,
            story_english TEXT NOT NULL,
            story_native TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kid_id) REFERENCES kids (id)
        )
    ''')
    
    # Parents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Parent-kid links table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parent_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            kid_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES parents (id),
            FOREIGN KEY (kid_id) REFERENCES kids (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Jinja2 filters
@app.template_filter('avatar_emoji')
def avatar_emoji_filter(avatar_name):
    avatar_emojis = {
        'cat': '🐱',
        'dog': '🐶', 
        'rabbit': '🐰',
        'bear': '🐻',
        'fox': '🦊',
        'panda': '🐼'
    }
    return avatar_emojis.get(avatar_name, '🐱')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check-session')
def check_session():
    has_session = 'kid_id' in session
    return jsonify({
        'has_session': has_session,
        'kid_id': session.get('kid_id'),
        'nickname': session.get('nickname')
    })

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        data = request.json or {}
        nickname = data.get('nickname')
        avatar = data.get('avatar')
        language = data.get('language', 'english')
        
        # Save kid to database
        conn = sqlite3.connect('kids_learning_app.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO kids (nickname, avatar, language_preference) VALUES (?, ?, ?)',
            (nickname, avatar, language)
        )
        kid_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Store kid_id in session
        session['kid_id'] = kid_id
        session['nickname'] = nickname
        session['avatar'] = avatar
        
        return jsonify({'success': True, 'kid_id': kid_id})
    
    return render_template('setup.html')

@app.route('/dashboard')
def dashboard():
    if 'kid_id' not in session:
        return redirect(url_for('setup'))
    
    kid_id = session['kid_id']
    nickname = session['nickname']
    avatar = session['avatar']
    
    # Get progress and badges
    conn = sqlite3.connect('kids_learning_app.db')
    cursor = conn.cursor()
    
    # Get completed modules
    cursor.execute('''
        SELECT DISTINCT module_name FROM progress WHERE kid_id = ?
    ''', (kid_id,))
    completed_modules = [row[0] for row in cursor.fetchall()]
    
    # Get badges
    cursor.execute('''
        SELECT badge_name, badge_icon, module_name, earned_at FROM badges 
        WHERE kid_id = ? ORDER BY earned_at DESC
    ''', (kid_id,))
    badges = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                         nickname=nickname, 
                         avatar=avatar,
                         completed_modules=completed_modules,
                         badges=badges)

# Allowed modules - security whitelist
ALLOWED_MODULES = ['colors', 'shapes', 'stories', 'rhymes']

@app.route('/module/<module_name>')
def module_view(module_name):
    if 'kid_id' not in session:
        return redirect(url_for('setup'))
    
    # Security: Validate module name against whitelist
    if module_name not in ALLOWED_MODULES:
        return "Module not found", 404
    
    # Load module content from JSON
    try:
        with open(os.path.join('data/modules', f'{module_name}.json'), 'r', encoding='utf-8') as f:
            module_data = json.load(f)
    except FileNotFoundError:
        return "Module not found", 404
    
    # Get kid's language preference
    conn = sqlite3.connect('kids_learning_app.db')
    cursor = conn.cursor()
    cursor.execute('SELECT language_preference FROM kids WHERE id = ?', (session['kid_id'],))
    language_result = cursor.fetchone()
    language_preference = language_result[0] if language_result else 'english'
    conn.close()
    
    return render_template('module.html', 
                         module_data=module_data,
                         nickname=session['nickname'],
                         avatar=session['avatar'],
                         language_preference=language_preference)

@app.route('/complete-lesson', methods=['POST'])
def complete_lesson():
    if 'kid_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json or {}
    module_name = data.get('module_name')
    lesson_id = data.get('lesson_id')
    
    if not module_name or not lesson_id:
        return jsonify({'error': 'Missing data'}), 400
    
    # Save progress to database
    conn = sqlite3.connect('kids_learning_app.db')
    cursor = conn.cursor()
    
    # Check if already completed
    cursor.execute(
        'SELECT id FROM progress WHERE kid_id = ? AND module_name = ? AND lesson_id = ?',
        (session['kid_id'], module_name, lesson_id)
    )
    
    if not cursor.fetchone():
        cursor.execute(
            'INSERT INTO progress (kid_id, module_name, lesson_id) VALUES (?, ?, ?)',
            (session['kid_id'], module_name, lesson_id)
        )
        conn.commit()
    
    conn.close()
    
    # Emit to parents in co-learning mode
    try:
        socketio.emit('kid_activity', {
            'kid_id': session['kid_id'],
            'nickname': session['nickname'],
            'activity': f'Completed lesson: {lesson_id} in {module_name}',
            'timestamp': datetime.now().isoformat()
        }, to=f"parent_{session['kid_id']}")
    except:
        pass
    
    return jsonify({'success': True})

@app.route('/lesson-progress/<module_name>')
def get_lesson_progress(module_name):
    if 'kid_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = sqlite3.connect('kids_learning_app.db')
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT lesson_id FROM progress WHERE kid_id = ? AND module_name = ?',
        (session['kid_id'], module_name)
    )
    
    completed_lessons = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'completed_lessons': completed_lessons})

@app.route('/submit-quiz', methods=['POST'])
def submit_quiz():
    if 'kid_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json or {}
    module_name = data.get('module_name')
    score = data.get('score')
    total_questions = data.get('total_questions')
    percentage = data.get('percentage')
    passed = data.get('passed')
    
    conn = sqlite3.connect('kids_learning_app.db')
    cursor = conn.cursor()
    
    # Get attempt number
    cursor.execute(
        'SELECT COUNT(*) FROM quiz_results WHERE kid_id = ? AND module_name = ?',
        (session['kid_id'], module_name)
    )
    attempt_number = cursor.fetchone()[0] + 1
    
    # Save quiz result
    cursor.execute(
        'INSERT INTO quiz_results (kid_id, module_name, score, total_questions, attempt_number) VALUES (?, ?, ?, ?, ?)',
        (session['kid_id'], module_name, score, total_questions, attempt_number)
    )
    
    badge_earned = False
    badge_name = None
    badge_icon = None
    
    # Award badge if passed and first time
    if passed and attempt_number == 1:
        # Security: Validate module name against whitelist
        if module_name in ALLOWED_MODULES:
            # Load module data to get badge info
            try:
                with open(os.path.join('data/modules', f'{module_name}.json'), 'r') as f:
                    module_data = json.load(f)
                    badge_info = module_data.get('badge', {})
                
                # Check if badge already exists
                cursor.execute(
                    'SELECT id FROM badges WHERE kid_id = ? AND module_name = ?',
                    (session['kid_id'], module_name)
                )
                
                if not cursor.fetchone():
                    badge_name = badge_info.get('name', f'{(module_name or "module").title()} Champion')
                    badge_icon = badge_info.get('icon', '🏆')
                    
                    cursor.execute(
                        'INSERT INTO badges (kid_id, badge_name, badge_icon, module_name) VALUES (?, ?, ?, ?)',
                        (session['kid_id'], badge_name, badge_icon, module_name)
                    )
                    badge_earned = True
            except FileNotFoundError:
                pass
    
    conn.commit()
    conn.close()
    
    # Emit to parents
    try:
        socketio.emit('kid_activity', {
            'kid_id': session['kid_id'],
            'nickname': session['nickname'],
            'activity': f'Quiz completed: {score}/{total_questions} ({percentage}%) in {module_name}',
            'badge_earned': badge_earned,
            'timestamp': datetime.now().isoformat()
        }, to=f"parent_{session['kid_id']}")
    except:
        pass
    
    return jsonify({
        'success': True,
        'badge_earned': badge_earned,
        'badge_name': badge_name,
        'badge_icon': badge_icon
    })

# Parent Authentication Routes
@app.route('/parent-login', methods=['GET', 'POST'])
def parent_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('parent_login.html', error='Please fill in all fields')
        
        conn = sqlite3.connect('kids_learning_app.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, password_hash FROM parents WHERE username = ?', (username,))
        parent = cursor.fetchone()
        conn.close()
        
        if parent and check_password_hash(parent[1], password):
            session['parent_id'] = parent[0]
            session['parent_username'] = username
            session['is_parent'] = True
            return redirect('/parent-dashboard')
        else:
            return render_template('parent_login.html', error='Invalid username or password')
    
    return render_template('parent_login.html')

@app.route('/parent-register', methods=['GET', 'POST'])
def parent_register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not all([username, email, password, confirm_password]):
            return render_template('parent_register.html', error='Please fill in all fields')
        
        if password != confirm_password:
            return render_template('parent_register.html', error='Passwords do not match')
        
        if password and len(password) < 6:
            return render_template('parent_register.html', error='Password must be at least 6 characters')
        
        conn = sqlite3.connect('kids_learning_app.db')
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute('SELECT id FROM parents WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            return render_template('parent_register.html', error='Username already exists')
        
        # Create parent account
        if not password:
            return render_template('parent_register.html', error='Password is required')
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO parents (username, password_hash, email)
            VALUES (?, ?, ?)
        ''', (username, password_hash, email))
        
        parent_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        session['parent_id'] = parent_id
        session['parent_username'] = username
        session['is_parent'] = True
        
        return redirect('/parent-dashboard')
    
    return render_template('parent_register.html')

@app.route('/parent-dashboard')
def parent_dashboard():
    if 'parent_id' not in session:
        return redirect('/parent-login')
    
    parent_id = session['parent_id']
    
    conn = sqlite3.connect('kids_learning_app.db')
    cursor = conn.cursor()
    
    # Get linked children
    cursor.execute('''
        SELECT k.id, k.nickname, k.avatar, k.language_preference, k.created_at
        FROM kids k
        JOIN parent_links pl ON k.id = pl.kid_id
        WHERE pl.parent_id = ?
        ORDER BY k.nickname
    ''', (parent_id,))
    
    children = []
    for child in cursor.fetchall():
        child_data = {
            'id': child[0],
            'nickname': child[1],
            'avatar': child[2],
            'language_preference': child[3],
            'created_at': child[4],
            'progress': get_child_progress(cursor, child[0]),
            'badges': get_child_badges(cursor, child[0]),
            'recent_activity': get_child_recent_activity(cursor, child[0])
        }
        children.append(child_data)
    
    conn.close()
    
    return render_template('parent_dashboard.html', 
                         parent_username=session['parent_username'],
                         children=children)

def get_child_progress(cursor, kid_id):
    """Get comprehensive progress data for a child"""
    progress = {}
    
    # Get lesson progress by module
    cursor.execute('''
        SELECT module_name, COUNT(DISTINCT lesson_id) as completed_lessons
        FROM progress
        WHERE kid_id = ?
        GROUP BY module_name
    ''', (kid_id,))
    
    for row in cursor.fetchall():
        progress[row[0]] = {
            'completed_lessons': row[1],
            'total_lessons': get_total_lessons_for_module(row[0])
        }
    
    # Get quiz results
    cursor.execute('''
        SELECT module_name, MAX(score) as best_score, total_questions, 
               COUNT(*) as attempts, MAX(completed_at) as last_attempt
        FROM quiz_results
        WHERE kid_id = ?
        GROUP BY module_name
    ''', (kid_id,))
    
    quiz_results = {}
    for row in cursor.fetchall():
        quiz_results[row[0]] = {
            'best_score': row[1],
            'total_questions': row[2],
            'percentage': round((row[1] / row[2]) * 100) if row[2] > 0 else 0,
            'attempts': row[3],
            'last_attempt': row[4]
        }
    
    return {'lessons': progress, 'quizzes': quiz_results}

def get_child_badges(cursor, kid_id):
    """Get all badges earned by a child"""
    cursor.execute('''
        SELECT badge_name, badge_icon, module_name, earned_at
        FROM badges
        WHERE kid_id = ?
        ORDER BY earned_at DESC
    ''', (kid_id,))
    
    return [{'name': row[0], 'icon': row[1], 'module': row[2], 'earned_at': row[3]} 
            for row in cursor.fetchall()]

def get_child_recent_activity(cursor, kid_id):
    """Get recent activity for a child"""
    activities = []
    
    # Recent lesson completions
    cursor.execute('''
        SELECT 'lesson' as type, module_name, lesson_id, completed_at
        FROM progress
        WHERE kid_id = ?
        ORDER BY completed_at DESC
        LIMIT 5
    ''', (kid_id,))
    
    for row in cursor.fetchall():
        activities.append({
            'type': 'lesson',
            'description': f'Completed lesson in {row[1].title()}',
            'timestamp': row[3]
        })
    
    # Recent quiz attempts
    cursor.execute('''
        SELECT 'quiz' as type, module_name, score, total_questions, completed_at
        FROM quiz_results
        WHERE kid_id = ?
        ORDER BY completed_at DESC
        LIMIT 3
    ''', (kid_id,))
    
    for row in cursor.fetchall():
        percentage = round((row[2] / row[3]) * 100)
        activities.append({
            'type': 'quiz',
            'description': f'Quiz in {row[1].title()}: {row[2]}/{row[3]} ({percentage}%)',
            'timestamp': row[4]
        })
    
    return sorted(activities, key=lambda x: x['timestamp'], reverse=True)[:10]

def get_total_lessons_for_module(module_name):
    """Get total number of lessons in a module"""
    module_lessons = {
        'colors': 3,
        'shapes': 3, 
        'stories': 3,
        'rhymes': 3
    }
    return module_lessons.get(module_name, 0)

@app.route('/link-child', methods=['POST'])
def link_child():
    if 'parent_id' not in session:
        return jsonify({'error': 'Not logged in as parent'}), 401
    
    data = request.json or {}
    nickname = data.get('nickname')
    
    if not nickname:
        return jsonify({'error': 'Child nickname required'}), 400
    
    conn = sqlite3.connect('kids_learning_app.db')
    cursor = conn.cursor()
    
    # Find child by nickname
    cursor.execute('SELECT id FROM kids WHERE nickname = ?', (nickname,))
    child = cursor.fetchone()
    
    if not child:
        conn.close()
        return jsonify({'error': 'Child not found'}), 404
    
    child_id = child[0]
    parent_id = session['parent_id']
    
    # Check if link already exists
    cursor.execute('SELECT id FROM parent_links WHERE parent_id = ? AND kid_id = ?', 
                  (parent_id, child_id))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Child already linked'}), 400
    
    # Create link
    cursor.execute('''
        INSERT INTO parent_links (parent_id, kid_id)
        VALUES (?, ?)
    ''', (parent_id, child_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Child linked successfully'})

@app.route('/parent-logout')
def parent_logout():
    session.pop('parent_id', None)
    session.pop('parent_username', None)
    session.pop('is_parent', None)
    return redirect('/parent-login')

# Story Builder Routes
@app.route('/story-builder')
def story_builder():
    if 'kid_id' not in session:
        return redirect('/')
    
    # Load story elements data
    try:
        with open('data/story_elements.json', 'r', encoding='utf-8') as f:
            story_elements = json.load(f)
    except FileNotFoundError:
        story_elements = {"characters": [], "settings": [], "plot_starters": []}
    
    # Get kid's language preference
    conn = sqlite3.connect('kids_learning_app.db')
    cursor = conn.cursor()
    cursor.execute('SELECT language_preference FROM kids WHERE id = ?', (session['kid_id'],))
    result = cursor.fetchone()
    language_preference = result[0] if result else 'english'
    
    # Get kid's saved stories
    cursor.execute('SELECT id, title, story_english, created_at FROM stories WHERE kid_id = ? ORDER BY created_at DESC LIMIT 10', (session['kid_id'],))
    saved_stories = cursor.fetchall()
    conn.close()
    
    return render_template('story_builder.html',
                         nickname=session.get('nickname'),
                         language_preference=language_preference,
                         story_elements=story_elements,
                         saved_stories=saved_stories)

@app.route('/create-story', methods=['POST'])
def create_story():
    if 'kid_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    
    if not all(key in data for key in ['character', 'setting', 'plot_starter', 'title']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Generate story using template
    try:
        with open('data/story_elements.json', 'r', encoding='utf-8') as f:
            story_elements = json.load(f)
        
        # Find selected elements
        character = next((c for c in story_elements['characters'] if c['id'] == data['character']), None)
        setting = next((s for s in story_elements['settings'] if s['id'] == data['setting']), None) 
        plot_starter = next((p for p in story_elements['plot_starters'] if p['id'] == data['plot_starter']), None)
        
        if not all([character, setting, plot_starter]):
            return jsonify({'error': 'Invalid story elements'}), 400
        
        # Select template based on plot themes
        template_id = 'simple_adventure'  # Default
        if plot_starter and 'friendship' in plot_starter['themes']:
            template_id = 'friendship_story'
        elif plot_starter and ('learning' in plot_starter['themes'] or 'discovery' in plot_starter['themes']):
            template_id = 'learning_journey'
            
        template = next((t for t in story_elements['story_templates'] if t['id'] == template_id), 
                       story_elements['story_templates'][0])
        
        # Generate story content
        story_content = generate_story_from_template(template, character, setting, plot_starter, story_elements)
        
        # Save story to database
        conn = sqlite3.connect('kids_learning_app.db')
        cursor = conn.cursor()
        
        # Map to existing schema
        character_name = character['name']['english'] if character else 'Unknown Character'
        place_name = setting['name']['english'] if setting else 'Unknown Place'
        magic_item = "magical crystal"  # Default magic item
        
        cursor.execute('''
            INSERT INTO stories (kid_id, title, character, place, magic_item, story_english)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['kid_id'], data['title'], character_name, place_name, magic_item, story_content))
        
        story_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'story_id': story_id,
            'story_content': story_content,
            'character': character,
            'setting': setting,
            'plot_starter': plot_starter
        })
        
    except Exception as e:
        print(f"Error creating story: {e}")
        return jsonify({'error': 'Failed to create story'}), 500

@app.route('/export-story/<int:story_id>')
def export_story_pdf(story_id):
    if 'kid_id' not in session:
        return redirect('/')
    
    # Get story from database
    conn = sqlite3.connect('kids_learning_app.db')
    cursor = conn.cursor()
    cursor.execute('SELECT title, story_english FROM stories WHERE id = ? AND kid_id = ?', 
                   (story_id, session['kid_id']))
    story = cursor.fetchone()
    conn.close()
    
    if not story:
        return "Story not found", 404
    
    # Generate PDF
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.utils import ImageReader
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        import io
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story_content = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor='#2E8B57'
        )
        
        story_style = ParagraphStyle(
            'StoryStyle',  
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=15,
            alignment=TA_LEFT,
            leftIndent=20,
            rightIndent=20
        )
        
        # Add title
        story_content.append(Paragraph(f"📚 {story[0]}", title_style))
        story_content.append(Spacer(1, 20))
        
        # Add story content 
        story_text = story[1].replace('\n', '<br/>')
        story_content.append(Paragraph(story_text, story_style))
        story_content.append(Spacer(1, 30))
        
        # Add footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            textColor='#666666'
        )
        story_content.append(Paragraph(f"✨ Created by {session.get('nickname', 'Young Author')} ✨", footer_style))
        
        doc.build(story_content)
        buffer.seek(0)
        
        # Return PDF as download
        return send_file(
            io.BytesIO(buffer.read()),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"{story[0].replace(' ', '_')}.pdf"
        )
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return "Error generating PDF", 500

def generate_story_from_template(template, character, setting, plot_starter, story_elements):
    """Generate a story using the template and selected elements"""
    import random
    
    # Get random elements for variety
    emotions = random.choice(story_elements['story_elements']['emotions'])
    actions = random.choice(story_elements['story_elements']['actions'])
    magical_item = random.choice(story_elements['story_elements']['magical_items'])
    lesson = random.choice(story_elements['story_elements']['lessons'])
    
    # Get a helper character (different from main character)
    helper = random.choice([c for c in story_elements['characters'] if c['id'] != character['id']])
    
    # Template replacements
    replacements = {
        '[CHARACTER]': character['name']['english'],
        '[SETTING]': setting['name']['english'].lower(),
        '[PLOT_STARTER]': plot_starter['description']['english'],
        '[EMOTION]': emotions,
        '[ACTION]': actions,
        '[MAGICAL_ITEM]': magical_item,
        '[LESSON]': lesson,
        '[HELPER]': helper['name']['english'],
        '[FRIEND_CHARACTER]': helper['name']['english'],
        '[HELPFUL_ACTION]': f"offered to help with their {random.choice(['wisdom', 'strength', 'kindness'])}",
        '[SHARED_ACTION]': f"decided to {random.choice(['work together', 'share their dreams', 'help each other'])}",
        '[SOLVE_PROBLEM]': f"{random.choice(['save the day', 'help everyone', 'make things better'])}",
        '[MYSTERY]': random.choice(['the stars above', 'hidden paths', 'ancient secrets']),
        '[NEW_SKILL]': random.choice(['be brave', 'trust friends', 'use their heart'])
    }
    
    # Generate story from template
    story_parts = []
    for sentence in template['structure']:
        story_sentence = sentence
        for placeholder, replacement in replacements.items():
            story_sentence = story_sentence.replace(placeholder, replacement)
        story_parts.append(story_sentence)
    
    return ' '.join(story_parts)

# Socket.IO event handlers for real-time parent updates
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('parent_join')
def handle_parent_join(data):
    """Handle parent joining room to receive child activity updates"""
    if 'parent_id' not in session:
        return
    
    kid_ids = data.get('kid_ids', [])
    parent_id = session['parent_id']
    
    # Verify parent owns these children
    conn = sqlite3.connect('kids_learning_app.db')
    cursor = conn.cursor()
    
    for kid_id in kid_ids:
        cursor.execute('''
            SELECT id FROM parent_links 
            WHERE parent_id = ? AND kid_id = ?
        ''', (parent_id, kid_id))
        
        if cursor.fetchone():
            room_name = f"parent_{kid_id}"
            join_room(room_name)
            emit('joined_room', {'room': room_name, 'kid_id': kid_id})
    
    conn.close()

@socketio.on('parent_leave')
def handle_parent_leave(data):
    """Handle parent leaving child activity rooms"""
    kid_ids = data.get('kid_ids', [])
    
    for kid_id in kid_ids:
        room_name = f"parent_{kid_id}"
        leave_room(room_name)
        emit('left_room', {'room': room_name, 'kid_id': kid_id})

# Festival Corner Routes
@app.route('/festival-corner')
def festival_corner():
    if 'kid_id' not in session:
        return redirect('/')
    
    current_festival = get_current_festival()
    all_festivals = get_all_festivals()
    
    return render_template('festival_corner.html',
                         nickname=session.get('nickname'),
                         current_festival=current_festival,
                         all_festivals=all_festivals)

def get_current_festival():
    """Get the current active festival based on today's date"""
    try:
        with open('data/festivals.json', 'r', encoding='utf-8') as f:
            festivals_data = json.load(f)
        
        today = datetime.now()
        current_month_day = today.strftime('%m-%d')
        
        for festival in festivals_data['festivals']:
            start_date = festival['date_range']['start']
            end_date = festival['date_range']['end']
            
            # Handle year-crossing festivals (like New Year)
            if start_date > end_date:  # Crosses year boundary
                if current_month_day >= start_date or current_month_day <= end_date:
                    return festival
            else:  # Normal date range
                if start_date <= current_month_day <= end_date:
                    return festival
        
        return None
    except Exception as e:
        print(f"Error loading festivals: {e}")
        return None

def get_all_festivals():
    """Get all available festivals for browsing"""
    try:
        with open('data/festivals.json', 'r', encoding='utf-8') as f:
            festivals_data = json.load(f)
        return festivals_data['festivals']
    except Exception as e:
        print(f"Error loading festivals: {e}")
        return []

@app.route('/festival/<festival_id>')
def festival_detail(festival_id):
    if 'kid_id' not in session:
        return redirect('/')
    
    festivals = get_all_festivals()
    festival = None
    
    for f in festivals:
        if f['id'] == festival_id:
            festival = f
            break
    
    if not festival:
        return redirect('/festival-corner')
    
    return render_template('festival_detail.html',
                         nickname=session.get('nickname'),
                         language_preference=session.get('language_preference', 'english'),
                         festival=festival)

@app.route('/festival-activity/<festival_id>/<int:activity_index>')
def festival_activity(festival_id, activity_index):
    if 'kid_id' not in session:
        return redirect('/')
    
    festivals = get_all_festivals()
    festival = None
    
    for f in festivals:
        if f['id'] == festival_id:
            festival = f
            break
    
    if not festival or activity_index >= len(festival['activities']):
        return redirect('/festival-corner')
    
    activity = festival['activities'][activity_index]
    
    return render_template('festival_activity.html',
                         nickname=session.get('nickname'),
                         language_preference=session.get('language_preference', 'english'),
                         festival=festival,
                         activity=activity,
                         activity_index=activity_index)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
