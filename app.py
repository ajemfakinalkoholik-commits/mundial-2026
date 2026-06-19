import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

def pl_now():
    # Czas w Polsce (CEST = UTC+2 latem, UTC+1 zima). Zakładamy czas letni dla Mundialu 2026.
    return datetime.utcnow() + timedelta(hours=2)

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
    highlights_url = db.Column(db.String(255), nullable=True)
    predictions = db.relationship('Prediction', backref='match', lazy=True)

class Prediction(db.Model):
    __tablename__ = 'typer_predictions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('typer_users.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('typer_matches.id'), nullable=False)
    pred_1 = db.Column(db.Integer, nullable=True)
    pred_2 = db.Column(db.Integer, nullable=True)
    points = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=pl_now)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- ROUTES ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        logout_user()
    resp = make_response(redirect(url_for('login')))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        logout_user()
    
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
    sort_by = request.args.get('sort', 'group')
    filter_val = request.args.get('filter', 'all')
    
    # Base query for matches
    matches_query = Match.query
    
    if filter_val == 'upcoming':
        matches_query = matches_query.filter_by(played=False)
    elif filter_val == 'unpredicted':
        matches_query = matches_query.filter_by(played=False)
        # We will filter out predicted ones in Python since it's easier without a complex join right now
    
    if sort_by == 'date':
        matches = matches_query.order_by(Match.start_time).all()
        grouped = {}
        for m in matches:
            date_key = m.date_time_str.split('|')[0].strip() if '|' in m.date_time_str else "Inne"
            if date_key not in grouped:
                grouped[date_key] = []
            grouped[date_key].append(m)
    else:
        matches = matches_query.order_by(Match.group_name, Match.start_time).all()
        grouped = {}
        for m in matches:
            if m.group_name not in grouped:
                grouped[m.group_name] = []
            grouped[m.group_name].append(m)
            
    all_predictions = Prediction.query.all()
    
    # Dictionary for current user predictions
    pred_dict = {p.match_id: p for p in all_predictions if p.user_id == current_user.id}
    
    # Apply 'unpredicted' filter by removing matches the user has already predicted
    if filter_val == 'unpredicted':
        new_grouped = {}
        for g_name, m_list in grouped.items():
            filtered_list = [m for m in m_list if m.id not in pred_dict or pred_dict[m.id].pred_1 is None]
            if filtered_list:
                new_grouped[g_name] = filtered_list
        grouped = new_grouped
            
    # Data for the leaderboard
    users = User.query.all()
    finished = Match.query.filter_by(played=True).order_by(Match.start_time.desc()).limit(2).all()
    finished.reverse()
    upcoming = Match.query.filter_by(played=False).order_by(Match.start_time.asc()).limit(2).all()
    target_matches = finished + upcoming
    
    all_predictions = Prediction.query.all()
    
    leaderboard_data = []
    for u in users:
        u_preds = [p for p in all_predictions if p.user_id == u.id]
        pts = sum(p.points for p in u_preds)
        recent_forms = []
        for m in target_matches:
            m_pred = next((p for p in u_preds if p.match_id == m.id), None)
            recent_forms.append(m_pred)
        leaderboard_data.append({'name': u.name, 'points': pts, 'recent': recent_forms})
    leaderboard_data.sort(key=lambda x: x['points'], reverse=True)
    
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
            
    return render_template('dashboard.html', grouped=grouped, pred_dict=pred_dict, others_dict=others_dict, now=pl_now(), leaderboard=leaderboard_data, last_matches=target_matches, filter_val=filter_val, sort_by=sort_by)

@app.route('/fix_times')
@login_required
def fix_times():
    if not current_user.is_admin:
        return "Brak uprawnień"
    
    predictions = Prediction.query.all()
    for p in predictions:
        if p.updated_at:
            p.updated_at = p.updated_at + timedelta(hours=2)
    db.session.commit()
    return "Poprawiono czasy wszystkich zakładów o +2 godziny!"

import csv
from io import StringIO
from flask import Response

@app.route('/export_csv')
@login_required
def export_csv():
    if not current_user.is_admin:
        return "Brak uprawnień", 403
        
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Gracz', 'Mecz', 'Czas rozpoczecia', 'Typ_1', 'Typ_2', 'Data i godzina typu', 'Punkty'])
    
    predictions = Prediction.query.join(User).join(Match).order_by(Match.start_time.desc(), User.name).all()
    for p in predictions:
        match_str = f"{p.match.team1}-{p.match.team2}"
        start_time = p.match.start_time.strftime('%Y-%m-%d %H:%M') if p.match.start_time else 'Brak'
        p1 = p.pred_1 if p.pred_1 is not None else '-'
        p2 = p.pred_2 if p.pred_2 is not None else '-'
        up_time = p.updated_at.strftime('%Y-%m-%d %H:%M:%S') if p.updated_at else 'Brak'
        
        cw.writerow([p.user.name, match_str, start_time, p1, p2, up_time, p.points])
        
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=typy_logi.csv"
    output.headers["Content-type"] = "text/csv"
    return output

import json

@app.route('/export_backup')
@login_required
def export_backup():
    if not current_user.is_admin:
        return "Brak uprawnień", 403
        
    users = User.query.all()
    matches = Match.query.all()
    predictions = Prediction.query.all()
    
    data = {
        "users": [{"id": u.id, "email": u.email, "name": u.name, "is_admin": u.is_admin} for u in users],
        "matches": [{"id": m.id, "group_name": m.group_name, "date_time_str": m.date_time_str, "team1": m.team1, "team2": m.team2, "result_1": m.result_1, "result_2": m.result_2, "played": m.played, "start_time": m.start_time.isoformat() if m.start_time else None, "highlights_url": m.highlights_url} for m in matches],
        "predictions": [{"id": p.id, "user_id": p.user_id, "match_id": p.match_id, "pred_1": p.pred_1, "pred_2": p.pred_2, "points": p.points, "updated_at": p.updated_at.isoformat() if p.updated_at else None} for p in predictions]
    }
    
    output = make_response(json.dumps(data, indent=2))
    output.headers["Content-Disposition"] = "attachment; filename=baza_mundial.json"
    output.headers["Content-type"] = "application/json"
    return output

@app.route('/import_backup', methods=['POST'])
@login_required
def import_backup():
    if not current_user.is_admin:
        return "Brak uprawnień", 403
        
    if 'backup_file' not in request.files:
        flash('Nie wybrano pliku', 'danger')
        return redirect(url_for('admin'))
        
    file = request.files['backup_file']
    if file.filename == '':
        flash('Nie wybrano pliku', 'danger')
        return redirect(url_for('admin'))
        
    if file:
        try:
            data = json.load(file)
            
            # Wyczyść obecne tabele
            Prediction.query.delete()
            Match.query.delete()
            # Nie usuwamy konta admina, który właśnie to wgrywa, resztę usuwamy
            User.query.filter(User.id != current_user.id).delete()
            
            db.session.commit()
            
            # Dodaj/aktualizuj Userów
            for u in data.get('users', []):
                existing = db.session.get(User, u['id'])
                if existing:
                    existing.email = u['email']
                    existing.name = u['name']
                    existing.is_admin = u.get('is_admin', False)
                else:
                    new_u = User(id=u['id'], email=u['email'], name=u['name'], is_admin=u.get('is_admin', False))
                    db.session.add(new_u)
                    
            # Dodaj Mecze
            for m in data.get('matches', []):
                st = datetime.fromisoformat(m['start_time']) if m['start_time'] else None
                new_m = Match(id=m['id'], group_name=m['group_name'], date_time_str=m['date_time_str'], team1=m['team1'], team2=m['team2'], result_1=m['result_1'], result_2=m['result_2'], played=m['played'], start_time=st, highlights_url=m.get('highlights_url'))
                db.session.add(new_m)
                
            # Dodaj Zakłady
            for p in data.get('predictions', []):
                up_at = datetime.fromisoformat(p['updated_at']) if p.get('updated_at') else None
                new_p = Prediction(id=p['id'], user_id=p['user_id'], match_id=p['match_id'], pred_1=p['pred_1'], pred_2=p['pred_2'], points=p['points'], updated_at=up_at)
                db.session.add(new_p)
                
            db.session.commit()
            flash('Baza danych pomyślnie przywrócona z kopii!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Wystąpił błąd podczas przywracania: {str(e)}', 'danger')
            
    return redirect(url_for('admin'))

@app.route('/save_prediction', methods=['POST'])
@login_required
def save_prediction():
    if request.is_json:
        data = request.get_json()
        match_id = data.get('match_id')
        pred_1 = data.get('pred_1')
        pred_2 = data.get('pred_2')
    else:
        match_id = request.form.get('match_id')
        pred_1 = request.form.get('pred_1')
        pred_2 = request.form.get('pred_2')
    
    match = db.session.get(Match, match_id)
    if not match:
        return jsonify({'error': 'Nie znaleziono meczu.'}), 404
        
    if match.played:
        return jsonify({'error': 'Ten mecz już się odbył.'}), 400
        
    if match.start_time and pl_now() >= match.start_time:
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
        pred.updated_at = pl_now()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.all()
    
    # Get 2 most recently finished matches
    finished = Match.query.filter_by(played=True).order_by(Match.start_time.desc()).limit(2).all()
    finished.reverse() # chronological order
    
    # Get 2 next upcoming matches
    upcoming = Match.query.filter_by(played=False).order_by(Match.start_time.asc()).limit(2).all()
    
    target_matches = finished + upcoming
    
    all_predictions = Prediction.query.all()
    
    leaderboard_data = []
    for u in users:
        u_preds = [p for p in all_predictions if p.user_id == u.id]
        pts = sum(p.points for p in u_preds)
        
        # Collect forms for the target matches
        recent_forms = []
        for m in target_matches:
            m_pred = next((p for p in u_preds if p.match_id == m.id), None)
            recent_forms.append(m_pred)
            
        leaderboard_data.append({'name': u.name, 'points': pts, 'recent': recent_forms})
        
    leaderboard_data.sort(key=lambda x: x['points'], reverse=True)
    return render_template('leaderboard.html', leaderboard=leaderboard_data, last_matches=target_matches)

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        flash('Brak uprawnień.', 'error')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        old_name = request.form.get('old_name')
        new_name = request.form.get('new_name')
        if old_name and new_name:
            user = User.query.filter_by(name=old_name).first()
            if user:
                user.name = new_name
                db.session.commit()
                flash(f'Zmieniono imię gracza na: {new_name}!', 'success')
            return redirect(url_for('admin'))

        match_id = request.form.get('match_id')
        res_1 = request.form.get('res_1')
        res_2 = request.form.get('res_2')
        
        new_date = request.form.get('new_date')
        highlights_url = request.form.get('highlights_url')
        
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
                
            if new_date:
                try:
                    # Format z przeglądarki: YYYY-MM-DDTHH:MM
                    st = datetime.strptime(new_date, "%Y-%m-%dT%H:%M")
                    match.start_time = st
                    match.date_time_str = f"{st.strftime('%Y-%m-%d')} | {st.strftime('%H:%M')}"
                except Exception:
                    pass
            
            if highlights_url is not None:
                match.highlights_url = highlights_url.strip() if highlights_url.strip() else None
                    
            db.session.commit()
            
            # Recalculate points for this match
            calculate_points(match.id)
            flash('Zapisano wynik!', 'success')
            return redirect(url_for('admin') + f'#match-{match.id}')
    matches = Match.query.order_by(Match.start_time).all()
    all_users = User.query.order_by(User.name).all()
    return render_template('admin.html', matches=matches, all_users=all_users)

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

with app.app_context():
    # Bezpieczna migracja - dodanie kolumny na skróty wideo
    from sqlalchemy import text
    try:
        db.session.execute(text("ALTER TABLE typer_matches ADD COLUMN highlights_url VARCHAR(255)"))
        db.session.commit()
        print("Pomyślnie dodano kolumnę highlights_url do bazy.")
    except Exception as e:
        # Kolumna już istnieje lub inny błąd, ignorujemy
        db.session.rollback()
        
    # Czyszczenie dopisków w dacie
    try:
        matches = Match.query.all()
        for m in matches:
            if m.date_time_str:
                m.date_time_str = m.date_time_str.replace(' (Edytowane)', '').replace(' (Czas PL)', '').strip()
        db.session.commit()
    except Exception as e:
        db.session.rollback()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
