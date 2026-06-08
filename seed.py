import update_excel
from app import app, db, User, Match

def seed():
    with app.app_context():
        db.create_all()
        
        # 1. Create Users
        admin_email = 'ajemfakinalkoholik@gmail.com'
        player_emails = ['kamilciach@gmail.com', 'kamilciach2@gmail.com']
        
        if not User.query.filter_by(email=admin_email).first():
            admin = User(email=admin_email, name='Admin (Ty)', is_admin=True)
            db.session.add(admin)
            
        for i, pe in enumerate(player_emails):
            if not User.query.filter_by(email=pe).first():
                user = User(email=pe, name=f'Gracz {i+1}', is_admin=False)
                db.session.add(user)
                
        db.session.commit()
        
        # 2. Add Matches
        if Match.query.count() == 0:
            groups, matches = update_excel.parse_schedule()
            for g_name, match_list in matches.items():
                g_safe = g_name.replace('Group', 'Grupa')
                for m in match_list:
                    date_time = m['date']
                    
                    # Parse "2026-06-11 | 21:00 (Czas PL)"
                    try:
                        from datetime import datetime
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
            print("Zaladowano mecze do bazy!")

if __name__ == '__main__':
    seed()
