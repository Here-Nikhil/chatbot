class PersonalizationEngine:
    def __init__(self):
        self.default_mode = "normal"
        self.user_profiles = {}

    def get_user_mode(self, user_id):
        # Gets if the user is a beginner or normal.
        return self.user_profiles.get(user_id, {}).get("mode", self.default_mode)

    def update_preference(self, user_id, feedback):
        # Changes the mode if the user says it's too hard or easy.
        # checks what the user said to switch modes
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {"mode": self.default_mode, "struggle_count": 0}

        profile = self.user_profiles[user_id]

        if feedback == "switch_beginner" or feedback == "too_hard":
            profile["mode"] = "beginner"
            profile["struggle_count"] += 1
        elif feedback == "switch_normal" or feedback == "too_easy":
            profile["mode"] = "normal"
            profile["struggle_count"] = 0 # Reset struggle count
        
        return profile["mode"]

    def check_struggle(self, user_id, interaction_history):
        # If the user asks too many confusing questions, assume they need help.
        # Start simple for now.
        if not interaction_history:
            return None
            
        last_question = interaction_history[-1].lower()
        if "explain simply" in last_question or "i don't understand" in last_question:
            return self.update_preference(user_id, "too_hard")
            
        return None
