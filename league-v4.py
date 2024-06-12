import requests
import mysql.connector
import json
import os
import time

# Configurar variáveis de ambiente
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
RIOT_API_KEY = os.getenv('RIOT_API_KEY')

# Conectar ao banco de dados
def connect_db():
    print("Conectando ao banco de dados...")
    return mysql.connector.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )

# Verificar se a tabela 'players' existe
def check_table_exists(conn):
    print("Verificando se a tabela 'players' existe...")
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
    print("Criando a tabela 'players'...")
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
    print("Tabela 'players' criada com sucesso.")

# Imprimir estrutura da tabela
def print_table_structure(conn):
    print("Imprimindo estrutura da tabela 'players'...")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = 'players';
    """, (DB_NAME,))
    columns = cursor.fetchall()
    cursor.close()
    print("Estrutura da tabela 'players':")
    for column in columns:
        print(f"{column[0]}: {column[1]}")

# Atualizar estrutura da tabela
def update_table_structure(conn, api_response):
    print("Atualizando estrutura da tabela 'players'...")
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
        print(f"Coluna '{column}' adicionada.")
    
    # Remover colunas que não existem mais na API
    for column in existing_columns - api_columns:
        if column != "summonerId":  # Não remover a coluna chave primária
            cursor.execute(f"ALTER TABLE players DROP COLUMN {column};")
            print(f"Coluna '{column}' removida.")
    
    conn.commit()
    cursor.close()
    print("Estrutura da tabela 'players' atualizada.")

# Atualizar dados dos jogadores
def update_players_data(conn, api_response):
    print("Atualizando dados dos jogadores...")
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
            print(f"Jogador {player['summonerId']} atualizado.")
        else:
            cursor.execute("""
                INSERT INTO players (summonerId, leaguePoints, rank, wins, losses, veteran, inactive, freshBlood, hotStreak)
                VALUES (%(summonerId)s, %(leaguePoints)s, %(rank)s, %(wins)s, %(losses)s, %(veteran)s, %(inactive)s, %(freshBlood)s, %(hotStreak)s);
            """, player)
            print(f"Jogador {player['summonerId']} inserido.")
