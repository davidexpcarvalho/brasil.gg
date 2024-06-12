import os
import pandas as pd
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def connect_db():
    db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

def get_match_details(session):
    query = "SELECT * FROM match_details;"
    df = pd.read_sql(query, session.bind)
    return df

def calculate_statistics(df):
    if 'teamPosition' not in df.columns:
        raise KeyError("A coluna 'teamPosition' não está presente no DataFrame.")
    results = []
    for player, data in df.groupby('player_name'):
        player_stats = {
            'player_name': player,
            'champions_played': data['champion'].value_counts().to_dict(),
            'champion_wins': data[data['win'] == True]['champion'].value_counts().to_dict()
        }
        win_rates = {champ: player_stats['champion_wins'].get(champ, 0) / count for champ, count in player_stats['champions_played'].items()}
        player_stats['win_rate'] = win_rates
        results.append(player_stats)
    return results

def create_statistics_tables(session):
    session.execute(text("DROP TABLE IF EXISTS player_statistics;"))
    session.execute(text("""
    CREATE TABLE IF NOT EXISTS player_statistics (
        player_name VARCHAR(50),
        champion VARCHAR(50),
        games_played INTEGER,
        wins INTEGER,
        win_rate FLOAT,
        PRIMARY KEY (player_name, champion)
    );
    """))

def clear_statistics_tables(session):
    session.execute(text("DELETE FROM player_statistics;"))

def save_statistics_to_db(session, player_stats):
    for stats in player_stats:
        for champion, games_played in stats['champions_played'].items():
            wins = stats['champion_wins'].get(champion, 0)
            win_rate = stats['win_rate'].get(champion, 0)
            session.execute(text("""
            INSERT INTO player_statistics (player_name, champion, games_played, wins, win_rate)
            VALUES (:player_name, :champion, :games_played, :wins, :win_rate)
            ON CONFLICT (player_name, champion) DO UPDATE
            SET games_played = EXCLUDED.games_played,
                wins = EXCLUDED.wins,
                win_rate = EXCLUDED.win_rate;
            """), {
                'player_name': stats['player_name'], 'champion': champion, 
                'games_played': games_played, 'wins': wins, 'win_rate': win_rate
            })
    session.commit()

def main():
    session = connect_db()
    create_statistics_tables(session)
    clear_statistics_tables(session)
    match_details = get_match_details(session)
    player_stats = calculate_statistics(match_details)
    save_statistics_to_db(session, player_stats)
    session.close()

if __name__ == "__main__":
    main()
