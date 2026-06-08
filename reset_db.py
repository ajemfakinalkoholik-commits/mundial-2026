import os
import random
from datetime import datetime, timedelta
from app import app, db, User, Match, Prediction, calculate_points
import matches_data

def reset_and_seed():
    with app.app_context():
        print("Usuwanie wszystkich tabel...")
        db.drop_all()
        print("Tworzenie nowych tabel...")
        db.create_all()
        
        print("Tworzenie użytkowników...")
        player_names = ['Mariusz', 'Michał', 'Karol', 'Szymon', 'Kuba', 'Artur', 'Przemek', 'Kamil']
        
        for name in player_names:
            is_admin = (name == 'Kamil')
            # Używamy name jako email tymczasowo aby spełnić wymóg unique=True (lub zostawiamy sztuczny email)
            email = f"{name.lower()}@typer.local"
            user = User(email=email, name=name, is_admin=is_admin)
            db.session.add(user)
        db.session.commit()
        
        print("Ładowanie meczów...")
        groups = matches_data.GROUPS
        matches = matches_data.MATCHES
        for g_name, match_list in matches.items():
            g_safe = g_name.replace('Group', 'Grupa')
            for m in match_list:
                date_time = m['date']
                try:
                    d_part = date_time.split('|')[0].strip()
                    t_part = date_time.split('|')[1].strip().split(' ')[0]
                    st = datetime.strptime(f"{d_part} {t_part}", "%Y-%m-%d %H:%M")
                except Exception:
                    st = None
                    
                t1, _ = update_excel.get_team_info(m['team1'])
                t2, _ = update_excel.get_team_info(m['team2'])
                
                new_match = Match(
                    group_name=g_safe,
                    date_time_str=date_time,
                    start_time=st,
                    team1=t1,
                    team2=t2
                )
                db.session.add(new_match)
        db.session.commit()
        
        print("Symulacja kilku rozegranych meczów...")
        # Get first 5 matches
        first_5 = Match.query.order_by(Match.id).limit(5).all()
        users = User.query.all()
        
        for match in first_5:
            match.start_time = datetime.now() - timedelta(days=1)
            match.played = True
            match.result_1 = random.randint(0, 3)
            match.result_2 = random.randint(0, 3)
            
            for u in users:
                pred = Prediction(
                    user_id=u.id, 
                    match_id=match.id,
                    pred_1=random.randint(0, 3),
                    pred_2=random.randint(0, 3)
                )
                db.session.add(pred)
        
        db.session.commit()
        
        for match in first_5:
            calculate_points(match.id)
            
        print("Baza zresetowana i w pełni załadowana (z testowymi wynikami)!")

if __name__ == '__main__':
    reset_and_seed()
