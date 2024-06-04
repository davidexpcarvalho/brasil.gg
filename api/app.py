from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

app = Flask(__name__, template_folder='templates')

DATABASE_URL = 'postgresql://postgres.ogwhaifbcpmhvavyeujd:mj4y,#3%EGP%7SZ@aws-0-sa-east-1.pooler.supabase.com:6543/postgres'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

@app.route('/add_player', methods=['GET', 'POST'])
def add_player_route():
    if request.method == 'POST':
        player_name = request.form['player_name']
        nick = request.form['nick']
        tag_line = request.form['tag_line']
        team_name = request.form['team_name']
        
        add_player(player_name, nick, tag_line, team_name)
        
        return redirect(url_for('add_player_route'))
    
    return render_template('add_player.html')

if __name__ == '__main__':
    app.run(debug=True)
