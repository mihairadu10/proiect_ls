from flask import Flask, request, jsonify, render_template
import os
from dotenv import load_dotenv
from groq import Groq
import random
import csv
import html
import re
import time

load_dotenv()

app = Flask(__name__)

import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def call_groq_chat(prompt, model="llama-3-70b-8192"):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a game master for Cards Against Humanity."},
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
    

# Funcție să încarce answers.csv
def load_answers():
    with open('answers.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        return [row['answer'] for row in reader]

# Funcție să încarce questions.csv
def load_questions():
    with open('questions.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        return [row['question'] for row in reader]

# Încarcăm datele la pornirea serverului
answers = load_answers()
questions = load_questions()

# Starea jocului
game_state = {}

@app.route("/")
def home():
    return render_template("cards_game.html")

@app.route("/start_game", methods=["POST"])
def start_game():
    game_state["player_name"] = request.json["player_name"]
    game_state["round"] = 1
    game_state["player_score"] = 0
    game_state["bot_score"] = 0
    game_state["player_cards"] = fetch_random_cards()
    game_state["round_start_time"] = time.time()  # Pornim timerul

    question = get_random_question()

    return jsonify({
        "message": f"Jocul a început! Bun venit {game_state['player_name']}! Să începem cu runda {game_state['round']}.",
        "question": question,
        "cards": game_state["player_cards"]
    })

@app.route("/next_round", methods=["POST"])
def next_round():
    game_state["round"] += 1
    game_state["round_start_time"] = time.time()  # Resetăm timerul

    question = get_random_question()

    return jsonify({
        "message": f"Runda {game_state['round']} a început! Alege un răspuns amuzant:",
        "question": question,
        "cards": game_state["player_cards"],
    })

@app.route("/play_round", methods=["POST"])
def play_round():
    user_answers = request.json["answers"]
    question = request.json["question"]

    # Verificăm dacă jucătorul a răspuns în timp
    round_time_limit = 30  # 30 de secunde
    elapsed_time = time.time() - game_state.get("round_start_time", 0)

    if elapsed_time > round_time_limit:
        # Dacă a depășit timpul, automat pierde runda
        round_winner = "bot"
        message = "Ai depășit timpul! Botul câștigă această rundă."
    else:
        # Alegem câștigător random
        round_winner = "player" if random.choice([True, False]) else "bot"
        message = f"Răspunsul tău: {user_answers}\nRăspunsul botului: {get_random_answer()}\n{round_winner.capitalize()} câștigă această rundă!"

    if round_winner == "player":
        game_state["player_score"] += 1
    else:
        game_state["bot_score"] += 1

    # Scoatem cărțile jucate
    for answer in user_answers:
        if answer in game_state["player_cards"]:
            game_state["player_cards"].remove(answer)

    # Completăm cărțile până la 5
    new_cards_needed = 5 - len(game_state["player_cards"])
    if new_cards_needed > 0:
        new_cards = fetch_random_cards(count=new_cards_needed)
        game_state["player_cards"].extend(new_cards)

    # Resetăm timpul pentru noua rundă
    game_state["round_start_time"] = time.time()

    return jsonify({
        "message": message,
        "score": f"Scor: {game_state['player_name']} - {game_state['player_score']} | Bot - {game_state['bot_score']}",
        "question": get_random_question(),
        "cards": game_state["player_cards"],
    })

def get_random_question():
    return random.choice(questions)

def get_random_answer():
    return random.choice(answers)

def fetch_random_cards(count=5):
    selected_answers = random.sample(answers, min(count, len(answers)))

    try:
        response = groq_client.chat.completions.create(
            model="llama-3-70b-8192",
            messages=[
                {"role": "system", "content": f"You are a game master for Cards Against Humanity. Generate {count} random answer cards based on the following subset: " + ', '.join(selected_answers)},
            ]
        )

        if hasattr(response, 'choices') and len(response.choices) > 0:
            content = response.choices[0].message.content.split("\n")
            decoded_content = [decode_html_entities(card.strip()) for card in content if re.match(r'^\d+\.', card.strip())]
            decoded_content = decoded_content[-count:] if len(decoded_content) > count else decoded_content
        else:
            decoded_content = []
    except Exception as e:
        print(f"Error fetching cards: {e}")
        decoded_content = selected_answers

    return decoded_content

def decode_html_entities(text):
    return html.unescape(text)

if __name__ == "__main__":
    app.run(debug=True)
