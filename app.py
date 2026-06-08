import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'twoj-sekretny-klucz-tutaj'

# Konfiguracja Bazy Danych pod Render.com (PostgreSQL) lub lokalnie (SQLite)
db_url = os.environ.get('DATABASE_URL')
if db_url:
    # SQLAlchemy wymaga 'postgresql://' zamiast 'postgres://' (często przekazywane przez Render)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mundial.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- FILTERS ---
TEAM_TO_FLAG = {
    'MEX': 'mx', 'RSA': 'za', 'KOR': 'kr', 'CZE': 'cz',
    'CAN': 'ca', 'BIH': 'ba', 'QAT': 'qa', 'SUI': 'ch',
    'BRA': 'br', 'MAR': 'ma', 'HAI': 'ht', 'SCO': 'gb-sct',
    'USA': 'us', 'PAR': 'py', 'AUS': 'au', 'KOS': 'xk',
    'GER': 'de', 'CUW': 'cw', 'JPN': 'jp', 'NGA': 'ng',
    'NED': 'nl', 'ECU': 'ec', 'KSA': 'sa', 'PAN': 'pa',
    'BEL': 'be', 'EGY': 'eg', 'URU': 'uy', 'NZL': 'nz',
    'ESP': 'es', 'CPV': 'cv', 'SRB': 'rs', 'MLI': 'ml',
    'FRA': 'fr', 'SEN': 'sn', 'IRN': 'ir', 'CRC': 'cr',
    'ARG': 'ar', 'ALG': 'dz', 'COL': 'co', 'PER': 'pe',
    'POR': 'pt', 'COD': 'cd', 'WAL': 'gb-wls', 'CMR': 'cm',
    'ENG': 'gb-eng', 'CRO': 'hr', 'CIV': 'ci', 'JAM': 'jm',
    'ITA': 'it', 'UKR': 'ua', 'TUR': 'tr', 'TUN': 'tn',
    'CHI': 'cl', 'SWE': 'se', 'POL': 'pl', 'DEN': 'dk',
    'IRQ': 'iq', 'NOR': 'no', 'AUT': 'at', 'JOR': 'jo',
    'UZB': 'uz', 'GHA': 'gh'
}

@app.template_filter('flag')
def flag_filter(team_code):
    return TEAM_TO_FLAG.get(team_code.upper(), 'xx')

# --- MODELS ---
class User(UserMixin, db.Model):
    __tablename__ = 'typer_users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    predictions = db.relationship('Prediction', backref='user', lazy=True)

class Match(db.Model):
    __tablename__ = 'typer_matches'
    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(50))
    date_time_str = db.Column(db.String(100)) # e.g. "11 Czerwiec - 21:00"
    start_time = db.Column(db.DateTime, nullable=True)
    team1 = db.Column(db.String(10)) # 3-letter code
    team2 = db.Column(db.String(10))
    result_1 = db.Column(db.Integer, nullable=True)
    result_2 = db.Column(db.Integer, nullable=True)
    played = db.Column(db.Boolean, default=False)
    predictions = db.relationship('Prediction', backref='match', lazy=True)

class Prediction(db.Model):
    __tablename__ = 'typer_predictions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('typer_users.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('typer_matches.id'), nullable=False)
    pred_1 = db.Column(db.Integer, nullable=True)
    pred_2 = db.Column(db.Integer, nullable=True)
    points = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- ROUTES ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        user_name = request.form.get('user_name')
        password = request.form.get('password')
        
        user = User.query.filter_by(name=user_name).first()
        if user:
            if user.is_admin:
                if password != 'tonieto':
                    flash('Nieprawidłowe hasło administratora.', 'error')
                    return redirect(url_for('login'))
            login_user(user, remember=True)
            return redirect(url_for('dashboard'))
        else:
            flash('Błąd logowania.', 'error')
            
    # Get all users for the grid
    users = User.query.order_by(User.id).all()
    return render_template('login.html', users=users)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    matches = Match.query.order_by(Match.group_name, Match.start_time).all()
    # Group matches by group_name
    grouped = {}
    for m in matches:
        grouped.setdefault(m.group_name, []).append(m)
        
    all_predictions = Prediction.query.all()
    
    # Dictionary for current user predictions
    pred_dict = {p.match_id: p for p in all_predictions if p.user_id == current_user.id}
    
    # Dictionary for other users predictions: match_id -> [list of dicts]
    others_dict = {}
    users_cache = {u.id: u.name for u in User.query.all()}
    
    for p in all_predictions:
        if p.user_id != current_user.id:
            others_dict.setdefault(p.match_id, []).append({
                'name': users_cache[p.user_id],
                'p1': p.pred_1,
                'p2': p.pred_2,
                'pts': p.points,
                'time': p.updated_at.strftime('%d.%m %H:%M') if p.updated_at else ''
            })
            
    return render_template('dashboard.html', grouped=grouped, pred_dict=pred_dict, others_dict=others_dict)

@app.route('/save_prediction', methods=['POST'])
@login_required
def save_prediction():
    data = request.get_json()
    match_id = data.get('match_id')
    pred_1 = data.get('pred_1')
    pred_2 = data.get('pred_2')
    
    match = db.session.get(Match, match_id)
    if not match:
        return jsonify({'error': 'Nie znaleziono meczu.'}), 404
        
    if match.played:
        return jsonify({'error': 'Ten mecz już się odbył.'}), 400
        
    if match.start_time and datetime.now() >= match.start_time:
        return jsonify({'error': 'Czas na obstawianie tego meczu minął!'}), 400
        
    pred = Prediction.query.filter_by(user_id=current_user.id, match_id=match_id).first()
    if not pred:
        pred = Prediction(user_id=current_user.id, match_id=match_id)
        db.session.add(pred)
        
    try:
        if pred_1 == "" or pred_2 == "":
            pred.pred_1 = None
            pred.pred_2 = None
        else:
            pred.pred_1 = int(pred_1)
            pred.pred_2 = int(pred_2)
        pred.updated_at = datetime.now()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.all()
    
    # Get last 5 matches that have started
    last_5_matches = Match.query.filter(Match.start_time <= datetime.now()).order_by(Match.start_time.desc()).limit(5).all()
    # Zostawiamy order_by(desc), aby pokazywac od najnowszego do najstarszego
    # last_5_matches.reverse()
    
    all_predictions = Prediction.query.all()
    
    leaderboard_data = []
    for u in users:
        u_preds = [p for p in all_predictions if p.user_id == u.id]
        pts = sum(p.points for p in u_preds)
        
        # Collect recent forms (points for last 5 matches)
        recent_forms = []
        for m in last_5_matches:
            m_pred = next((p for p in u_preds if p.match_id == m.id), None)
            recent_forms.append(m_pred)
            
        leaderboard_data.append({'name': u.name, 'points': pts, 'recent': recent_forms})
        
    leaderboard_data.sort(key=lambda x: x['points'], reverse=True)
    return render_template('leaderboard.html', leaderboard=leaderboard_data, last_matches=last_5_matches)

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        flash('Brak uprawnień.', 'error')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        match_id = request.form.get('match_id')
        res_1 = request.form.get('res_1')
        res_2 = request.form.get('res_2')
        
        match = db.session.get(Match, match_id)
        if match:
            if res_1 == "" or res_2 == "":
                match.result_1 = None
                match.result_2 = None
                match.played = False
            else:
                match.result_1 = int(res_1)
                match.result_2 = int(res_2)
                match.played = True
            db.session.commit()
            
            # Recalculate points for this match
            calculate_points(match.id)
            flash('Zapisano wynik!', 'success')
            
    matches = Match.query.order_by(Match.group_name, Match.start_time).all()
    return render_template('admin.html', matches=matches)

def calculate_points(match_id):
    match = db.session.get(Match, match_id)
    if not match or not match.played:
        # Reset points if unplayed
        for p in Prediction.query.filter_by(match_id=match_id).all():
            p.points = 0
        db.session.commit()
        return
        
    a, b = match.result_1, match.result_2
    
    predictions = Prediction.query.filter_by(match_id=match_id).all()
    for p in predictions:
        if p.pred_1 is None or p.pred_2 is None:
            p.points = 0
            continue
            
        u_a, u_b = p.pred_1, p.pred_2
        
        if u_a == a and u_b == b:
            p.points = 10
        elif (u_a > u_b and a > b) or (u_a < u_b and a < b) or (u_a == u_b and a == b):
            p.points = 2
        else:
            p.points = 0
            
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
