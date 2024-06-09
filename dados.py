import pandas as pd

def excel_to_json(excel_file, json_file):
    # Ler o arquivo Excel
    df = pd.read_excel(excel_file)
    
    # Converter para JSON
    df.to_json(json_file, orient='records', indent=4)
    print(f"Arquivo JSON salvo em {json_file}")

if __name__ == "__main__":
    excel_to_json('player_statistics_rows.csv', 'player_statistics_rows.json')
  excel_to_json('underperforming_positions_rows.csv', 'underperforming_positions_rows.json')
