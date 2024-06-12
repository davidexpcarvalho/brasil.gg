import requests
import psycopg2
import json
import os

# Configurar variáveis de ambiente
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
RIOT_API_KEY = os.getenv('RIOT_API_KEY')

# Conectar ao banco de dados
def connect_db():
    return psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )

# Verificar se a tabela 'players' existe
def check_table_exists(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'players'
            );
        """)
        return cur.fetchone()[0]

# Criar a tabela 'players' se não existir
def create_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE players (
                summoner_id VARCHAR PRIMARY KEY,
                league_points INT,
                rank VARCHAR,
                wins INT,
                losses INT,
                veteran BOOLEAN,
                inactive BOOLEAN,
                fresh_blood BOOLEAN,
                hot_streak BOOLEAN
            );
        """)
        conn.commit()

# Atualizar estrutura da tabela
def update_table_structure(conn, api_response):
    existing_columns = set()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'players';
        """)
        existing_columns = set([row[0] for row in cur.fetchall()])
    
    api_columns = set(api_response[0].keys())
    
    # Adicionar novas colunas
    for column in api_columns - existing_columns:
        with conn.cursor() as cur:
            cur.execute(f"ALTER TABLE players ADD COLUMN {column} VARCHAR;")
    
    # Remover colunas que não existem mais na API
    for column in existing_columns - api_columns:
        with conn.cursor() as cur:
            cur.execute(f"ALTER TABLE players DROP COLUMN {column};")
    
    conn.commit()

# Atualizar dados dos jogadores
def update_players_data(conn, api_response):
    with conn.cursor() as cur:
        # Obter todos os summoner_ids existentes
        cur.execute("SELECT summoner_id FROM players;")
        existing_ids = set([row[0] for row in cur.fetchall()])
        
        api_ids = set(player['summonerId'] for player in api_response)
        
        # Inserir ou atualizar registros
        for player in api_response:
            if player['summonerId'] in existing_ids:
                cur.execute("""
                    UPDATE players SET
                    league_points = %(leaguePoints)s,
                    rank = %(rank)s,
                    wins = %(wins)s,
                    losses = %(losses)s,
                    veteran = %(veteran)s,
                    inactive = %(inactive)s,
                    fresh_blood = %(freshBlood)s,
                    hot_streak = %(hotStreak)s
                    WHERE summoner_id = %(summonerId)s;
                """, player)
            else:
                cur.execute("""
                    INSERT INTO players (summoner_id, league_points, rank, wins, losses, veteran, inactive, fresh_blood, hot_streak)
                    VALUES (%(summonerId)s, %(leaguePoints)s, %(rank)s, %(wins)s, %(losses)s, %(veteran)s, %(inactive)s, %(freshBlood)s, %(hotStreak)s);
                """, player)
        
        # Remover registros que não estão mais na API
        for summoner_id in existing_ids - api_ids:
            cur.execute("DELETE FROM players WHERE summoner_id = %s;", (summoner_id,))
    
    conn.commit()

# Função principal
def main():
    conn = connect_db()
    try:
        if not check_table_exists(conn):
            create_table(conn)
        
        # Fazer requisição à API da Riot
        response = requests.get(f"https://br1.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5?api_key={RIOT_API_KEY}")
        api_response = response.json()['entries']
        
        update_table_structure(conn, api_response)
        update_players_data(conn, api_response)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
