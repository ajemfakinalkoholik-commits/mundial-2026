import os
import random
from datetime import datetime, timedelta
from app import app, db, User, Match, Prediction, calculate_points
import matches_data

def get_team_info(country_name):
    mapping = {
        'Mexico': ('MEX', 'mx'), 'South Africa': ('RSA', 'za'), 'South Korea': ('KOR', 'kr'), 'Czech Republic': ('CZE', 'cz'),
        'Canada': ('CAN', 'ca'), 'Bosnia and Herzegovina': ('BIH', 'ba'), 'Qatar': ('QAT', 'qa'), 'Switzerland': ('SUI', 'ch'),
        'Brazil': ('BRA', 'br'), 'Morocco': ('MAR', 'ma'), 'Haiti': ('HAI', 'ht'), 'Scotland': ('SCO', 'gb-sct'),
        'United States': ('USA', 'us'), 'Paraguay': ('PAR', 'py'), 'Australia': ('AUS', 'au'), 'Kosovo': ('KOS', 'xk'),
        'Germany': ('GER', 'de'), 'Curaçao': ('CUW', 'cw'), 'Japan': ('JPN', 'jp'), 'Nigeria': ('NGA', 'ng'),
        'Netherlands': ('NED', 'nl'), 'Ecuador': ('ECU', 'ec'), 'Saudi Arabia': ('KSA', 'sa'), 'Panama': ('PAN', 'pa'),
        'Belgium': ('BEL', 'be'), 'Egypt': ('EGY', 'eg'), 'Uruguay': ('URU', 'uy'), 'New Zealand': ('NZL', 'nz'),
        'Spain': ('ESP', 'es'), 'Cape Verde': ('CPV', 'cv'), 'Serbia': ('SRB', 'rs'), 'Mali': ('MLI', 'ml'),
        'France': ('FRA', 'fr'), 'Senegal': ('SEN', 'sn'), 'Iran': ('IRN', 'ir'), 'Costa Rica': ('CRC', 'cr'),
        'Argentina': ('ARG', 'ar'), 'Algeria': ('ALG', 'dz'), 'Colombia': ('COL', 'co'), 'Peru': ('PER', 'pe'),
        'Portugal': ('POR', 'pt'), 'DR Congo': ('COD', 'cd'), 'Wales': ('WAL', 'gb-wls'), 'Cameroon': ('CMR', 'cm'),
        'England': ('ENG', 'gb-eng'), 'Croatia': ('CRO', 'hr'), 'Ivory Coast': ('CIV', 'ci'), 'Jamaica': ('JAM', 'jm'),
        'Italy': ('ITA', 'it'), 'Ukraine': ('UKR', 'ua'), 'Turkey': ('TUR', 'tr'), 'Tunisia': ('TUN', 'tn'),
        'Chile': ('CHI', 'cl'), 'Sweden': ('SWE', 'se'), 'Poland': ('POL', 'pl'), 'Denmark': ('DEN', 'dk'),
        'Iraq': ('IRQ', 'iq'), 'Norway': ('NOR', 'no'), 'Austria': ('AUT', 'at'), 'Jordan': ('JOR', 'jo'),
        'Uzbekistan': ('UZB', 'uz'), 'Ghana': ('GHA', 'gh')
    }
    val = mapping.get(country_name, (country_name[:3].upper(), 'xx'))
    return val[0], f"https://flagcdn.com/w40/{val[1]}.png"


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
                    
                t1, _ = get_team_info(m['team1'])
                t2, _ = get_team_info(m['team2'])
                
                new_match = Match(
                    group_name=g_safe,
                    date_time_str=date_time,
                    start_time=st,
                    team1=t1,
                    team2=t2
                )
                db.session.add(new_match)
        db.session.commit()
        
        print("Baza zresetowana i gotowa do prawdziwej gry!")

if __name__ == '__main__':
    reset_and_seed()
