from flask import Flask, request, redirect, url_for, render_template

app = Flask(__name__)

# Rota para adicionar um novo jogador
@app.route('/add_player', methods=['GET', 'POST'])
def add_player_route():
    if request.method == 'POST':
        player_name = request.form['player_name']
        nick = request.form['nick']
        tag_line = request.form['tag_line']
        team_name = request.form['team_name']
        
        # Função para adicionar o jogador
        add_player(player_name, nick, tag_line, team_name)
        
        return redirect(url_for('add_player_route'))
    
    return render_template('add_player.html')

# Função para adicionar um jogador (substitua isso pela sua lógica de adicionar jogador)
def add_player(player_name, nick, tag_line, team_name):
    # Sua lógica para adicionar um jogador ao banco de dados
    pass

# Rota inicial (exemplo)
@app.route('/')
def index():
    return "Hello, World!"

if __name__ == '__main__':
    app.run(debug=True)
