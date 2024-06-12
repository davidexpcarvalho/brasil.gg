import requests
import mysql.connector
import json
import os
import time
import logging

# Configurar o logging
logging.basicConfig(filename='league_script.log', level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(message)s')

# Configurar variáveis de ambiente
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
RIOT_API_KEY = os.getenv('RIOT_API_KEY')

# Verificar se as variáveis de ambiente estão definidas
if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME, RIOT_API_KEY]):
    logging.error("Uma ou mais variáveis de ambiente não estão definidas.")
    raise EnvironmentError("Verifique as variáveis de ambiente.")

# Conectar ao banco de dados
def connect_db():
    logging.info("Conectando ao banco de dados...")
    return mysql.connector.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )

# Verificar se a tabela 'players' existe
def check_table_exists(conn):
    logging.info("Verificando se a tabela 'players' existe...")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_name = 'players';
    """, (DB_NAME,))
    exists = cursor.fetchone()[0] == 1
    cursor.close()
    return exists

# Criar a tabela 'players' se não existir
def create_table(conn):
    logging.info("Criando a tabela 'players'...")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            summonerId VARCHAR(255) PRIMARY KEY,
            leaguePoints INT,
            rank VARCHAR(10),
            wins INT,
            losses INT,
            veteran BOOLEAN,
            inactive BOOLEAN,
            freshBlood BOOLEAN,
            hotStreak BOOLEAN
        );
    """)
    conn.commit()
    cursor.close()
    logging.info("Tabela 'players' criada com sucesso.")

# Imprimir estrutura da tabela
def print_table_structure(conn):
    logging.info("Imprimindo estrutura da tabela 'players'...")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = 'players';
    """, (DB_NAME,))
    columns = cursor.fetchall()
    cursor.close()
    logging.info("Estrutura da tabela 'players':")
    for column in columns:
        logging.info(f"{column[0]}: {column[1]}")

# Atualizar estrutura da tabela
def update_table_structure(conn, api_response):
    logging.info("Atualizando estrutura da tabela 'players'...")
    existing_columns = set()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = %s AND table_name = 'players';
    """, (DB_NAME,))
    existing_columns = set(row[0] for row in cursor.fetchall())
    
    api_columns = set(api_response[0].keys())
    
    # Adicionar novas colunas
    for column in api_columns - existing_columns:
        cursor.execute(f"ALTER TABLE players ADD COLUMN {column} VARCHAR(255);")
        logging.info(f"Coluna '{column}' adicionada.")
    
    # Remover colunas que não existem mais na API
    for column in existing_columns - api_columns:
        if column != "summonerId":  # Não remover a coluna chave primária
            cursor.execute(f"ALTER TABLE players DROP COLUMN {column};")
            logging.info(f"Coluna '{column}' removida.")
    
    conn.commit()
    cursor.close()
    logging.info("Estrutura da tabela 'players' atualizada.")

# Atualizar dados dos jogadores
def update_players_data(conn, api_response):
    logging.info("Atualizando dados dos jogadores...")
    cursor = conn.cursor()
    
    # Obter todos os summonerIds existentes
    cursor.execute("SELECT summonerId FROM players;")
    existing_ids = set(row[0] for row in cursor.fetchall())
    
    api_ids = set(player['summonerId'] for player in api_response)
    
    # Inserir ou atualizar registros
    for player in api_response:
        if player['summonerId'] in existing_ids:
            cursor.execute("""
                UPDATE players SET
                leaguePoints = %(leaguePoints)s,
                rank = %(rank)s,
                wins = %(wins)s,
                losses = %(losses)s,
                veteran = %(veteran)s,
                inactive = %(inactive)s,
                freshBlood = %(freshBlood)s,
                hotStreak = %(hotStreak)s
                WHERE summonerId = %(summonerId)s;
            """, player)
            logging.info(f"Jogador {player['summonerId']} atualizado.")
        else:
            cursor.execute("""
                INSERT INTO players (summonerId, leaguePoints, rank, wins, losses, veteran, inactive, freshBlood, hotStreak)
                VALUES (%(summonerId)s, %(leaguePoints)s, %(rank)s, %(wins)s, %(losses)s, %(veteran)s, %(inactive)s, %(freshBlood)s, %(hotStreak)s);
            """, player)
            logging.info(f"Jogador {player['summonerId']} inserido.")
    
    # Remover registros que não estão mais na API
    for summonerId in existing_ids - api_ids:
        cursor.execute("DELETE FROM players WHERE summonerId = %s;", (summonerId,))
        logging.info(f"Jogador {summonerId} removido.")
    
    conn.commit()
    cursor.close()
    logging.info("Dados dos jogadores atualizados.")

# Função para obter dados da API com controle de taxa de requisições
def get_league_data(url):
    logging.info(f"Fazendo requisição para {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        time.sleep(1)  # Aguardar 1 segundo entre as requisições
        return response.json().get('entries', [])
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"Erro HTTP ao fazer requisição para {url}: {http_err}")
    except requests.exceptions.RequestException as err:
        logging.error(f"Erro ao fazer requisição para {url}: {err}")
    return []

# Função principal
def main():
    conn = None
    try:
        conn = connect_db()
        if not check_table_exists(conn):
            create_table(conn)
        print_table_structure(conn)

        all_players = []
        queues = ["RANKED_SOLO_5x5"]
        tiers = ["CHALLENGER", "GRANDMASTER", "MASTER"]
        divisions = ["I", "II", "III", "IV"]
        
        # Obter dados dos Challenger, Grandmaster e Master
        for tier in tiers:
            for queue in queues:
                url = f"https://br1.api.riotgames.com/lol/league/v4/{tier.lower()}leagues/by-queue/{queue}?api_key={RIOT_API_KEY}"
                all_players.extend(get_league_data(url))
        
        # Obter dados das outras divisões
        for queue in queues:
            for tier in ["DIAMOND", "PLATINUM", "GOLD", "SILVER", "BRONZE", "IRON"]:
                for division in divisions:
                    url = f"https://br1.api.riotgames.com/lol/league/v4/entries/{queue}/{tier}/{division}?api_key={RIOT_API_KEY}"
                    all_players.extend(get_league_data(url))
        
        # Atualizar a estrutura da tabela e os dados
        if all_players:
            update_table_structure(conn, all_players)
            update_players_data(conn, all_players)
    except Exception as e:
        logging.error(f"Ocorreu um erro: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
