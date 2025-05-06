from flask import Flask, request, jsonify, render_template
import os
import random
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = Flask(__name__)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Game state
game_state = {
    "player_name": "",
    "location": "Twilight Clearing",
    "inventory": ["Rusty Sword", "Old Map"],
    "stats": {
        "health": 10,
        "courage": 3,
        "wisdom": 2,
        "charisma": 2,
        "luck": 1
    },
    "history": [],
    "current_event": "",
    "round": 0
}

@app.route("/")
def home():
    return render_template("rpg_game.html")

@app.route("/start_game", methods=["POST"])
def start_game():
    game_state["player_name"] = request.json["player_name"]
    game_state["round"] = 1
    game_state["inventory"] = ["Rusty Sword", "Old Map"]
    game_state["location"] = "Twilight Clearing"
    game_state["stats"] = {
        "health": 10,
        "courage": 3,
        "wisdom": 2,
        "charisma": 2,
        "luck": 1
    }
    game_state["history"] = []

    intro_event = generate_story_event()
    game_state["current_event"] = intro_event

    return jsonify({
        "message": f"Welcome, {game_state['player_name']}! Your adventure begins in the {game_state['location']}.",
        "event": intro_event,
        "inventory": game_state["inventory"],
        "stats": game_state["stats"]
    })

@app.route("/respond_to_event", methods=["POST"])
def respond_to_event():
    player_action = request.json["action"]
    game_state["round"] += 1

    stat_used = detect_stat_from_action(player_action)
    stat_value = game_state["stats"].get(stat_used, 0)
    triggered = random.random() < 0.4  # 40% chance to trigger stat check
    success = None
    result_description = "none"

    if triggered:
        success_chance = stat_value / 10
        success = random.random() < success_chance
        result_description = "success" if success else "failure"

        if not success:
            game_state["stats"]["health"] = max(0, game_state["stats"]["health"] - 1)
        else:
            if stat_used and stat_used != "health":
                game_state["stats"][stat_used] = game_state["stats"].get(stat_used, 0) + 1

    game_state["history"].append({
        "round": game_state["round"],
        "action": player_action,
        "event": game_state["current_event"],
        "stat_used": stat_used,
        "triggered": triggered,
        "success": success
    })

    story_context = (
        f"Scene: {game_state['current_event']}\n"
        f"Player action: {player_action}\n"
        f"Stat challenge: {stat_used} ({stat_value}) - {result_description}\n"
        f"Player stats: {game_state['stats']}"
    )

    next_event = call_groq_for_result(story_context)
    game_state["current_event"] = next_event

    return jsonify({
        "outcome": next_event,
        "inventory": game_state["inventory"],
        "stats": game_state["stats"],
        "stat_used": stat_used,
        "success": success,
        "triggered": triggered
    })

@app.route("/get_choices", methods=["POST"])
def get_choices():
    try:
        context = game_state["current_event"]
        response = groq_client.chat.completions.create(
            model="allam-2-7b",
            messages=[
                {"role": "system", "content": (
                    "You are a fantasy RPG assistant. Based on the current scene, suggest 3 or 4 possible player actions. "
                    "For each action, assign a stat (or 'none') and potential reward (like +1 LUCK). Format:\n"
                    "1. Talk to the merchant | stat: charisma | reward: gold\n"
                    "2. Sneak past the guard | stat: luck | reward: access"
                )},
                {"role": "user", "content": f"Scene: {context}"}
            ]
        )

        if hasattr(response, 'choices') and len(response.choices) > 0:
            text = response.choices[0].message.content.strip()
            return jsonify({"choices": parse_detailed_choices(text)})
    except Exception as e:
        print(f"Error getting choices: {e}")

    return jsonify({"choices": []})

def generate_story_event():
    try:
        response = groq_client.chat.completions.create(
            model="allam-2-7b",
            messages=[
                {"role": "system", "content": (
                    "You are a fantasy RPG narrator. Begin an adventure in 'Twilight Clearing'. End with 'What do you do?'"
                )}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating story: {e}")
        return "You awaken in a foggy glade. What do you do?"

def call_groq_for_result(context):
    try:
        response = groq_client.chat.completions.create(
            model="allam-2-7b",
            messages=[
                {"role": "system", "content": (
                    "You are a fantasy RPG narrator. Continue the scene with the given stat challenge result. "
                    "Be vivid and end with 'What do you do next?'. Include exact stat result info in the output."
                )},
                {"role": "user", "content": context}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating outcome: {e}")
        return "You hesitate. Nothing changes. What do you do next?"

def detect_stat_from_action(action):
    action = action.lower()
    if any(w in action for w in ["fight", "charge", "resist"]): return "courage"
    if any(w in action for w in ["think", "study", "solve"]): return "wisdom"
    if any(w in action for w in ["charm", "talk", "convince"]): return "charisma"
    if any(w in action for w in ["sneak", "chance", "luck"]): return "luck"
    return random.choice(["courage", "wisdom", "charisma", "luck"])

def parse_detailed_choices(text):
    choices = []
    for line in text.strip().split("\n"):
        if '|' in line:
            parts = line.split('|')
            action = parts[0].strip().split('.', 1)[-1].strip()
            stat = parts[1].split(':')[-1].strip() if 'stat:' in parts[1] else "none"
            reward = parts[2].split(':')[-1].strip() if len(parts) > 2 else "none"
            stat_value = game_state["stats"].get(stat, 0)
            chance = int(stat_value * 10)
            choices.append({
                "action": action,
                "stat": stat,
                "reward": reward,
                "chance": chance
            })
    return choices
if __name__ == "__main__":
    app.run(debug=True)