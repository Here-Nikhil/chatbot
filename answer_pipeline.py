import json
import os
import subprocess
import sys
from personalization_logic import PersonalizationEngine

# --- Install stuff if it's not there ---
def install_and_import(package, import_name):
    try:
        __import__(import_name)
    except ImportError:
        print(f"[System] '{package}' library not found. Installing now...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"[System] {package} installed. Retrying...")
            __import__(import_name)
        except Exception as e:
            print(f"[ERROR] Failed to install {package}: {e}")


# 1. python-dotenv (for .env)
try:
    from dotenv import load_dotenv
except ImportError:
    print(f"[System] 'python-dotenv' library not found. Installing now...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
        print(f"[System] python-dotenv installed. Retrying...")
        from dotenv import load_dotenv
    except Exception as e:
        print(f"[ERROR] Failed to install python-dotenv: {e}")
        # We can continue, but API key might not load unless set elsewhere
        def load_dotenv(): pass

# Load environment variables
load_dotenv()

# 2. google-genai (for Gemini)
# We keep the import logical check inside the function or global, 
# but let's pre-check globally for smoother user experience if desired,
# OR keep the specific lazy load. Let's keep specific lazy load for 'google-generativeai' 
# inside the function so it doesn't crash start-up if internet is bad.

def call_gemini_api(prompt):
    # Talks to Google Gemini. install it if it's missing.
    # HARDCODED KEY AS REQUESTED (Moved to .env)
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        return "[ERROR] GOOGLE_API_KEY not found in environment variables. Please check your .env file."
    
    try:
        from google import genai
    except ImportError:
        print("[System] 'google-genai' library not found. Installing now...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "google-genai"])
            print("[System] Installation complete. Retrying...")
            from google import genai
        except Exception as e:
            return f"[ERROR] Failed to auto-install google-genai: {str(e)}"

    try:
        # New SDK Client Initialization
        client = genai.Client(api_key=api_key)
        
        # Using a model confirmed to be in the user's list
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite', 
            contents=prompt
        )
        return response.text

    except Exception as e:
        # If 404/Not Found, prompt user to check key access
        return f"[ERROR] API Call Failed: {str(e)}"

    except Exception as e:
        return f"[ERROR] API Call Failed: {str(e)}"

class FinancialBot:
    def __init__(self, eng_path="financial_content.json", hi_path="financial_content_hi.json"):
        self.personalization = PersonalizationEngine()
        self.content_eng = self.load_content(eng_path)
        self.content_hi = self.load_content(hi_path)
        
    def load_content(self, path):
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle legacy format where root was a dict with "topics" key
                if isinstance(data, dict) and "topics" in data:
                    # Convert legacy dict to list format for consistency if possible, 
                    # or just return the values list if it was a dict of objects
                    weights = []
                    for key, val in data["topics"].items():
                        # Inject the key as 'topic' if missing
                        if "topic" not in val:
                            val["topic"] = key
                        weights.append(val)
                    return weights
                return data if isinstance(data, list) else []
        except Exception as e:
            print(f"[ERROR] Loading {path}: {e}")
            return []

    def find_topic(self, user_question, content_list):
        """
        Finds the most relevant topic using simple keyword matching (Set Intersection).
        Returns the best matching topic object or None.
        """
        if not content_list or not isinstance(content_list, list):
            return None

        user_tokens = set(user_question.lower().split())
        best_topic = None
        max_overlap = 0

        for item in content_list:
            # Get the topic name/title
            topic_name = item.get("topic", "")
            if not topic_name: 
                continue
                
            # Tokenize topic title
            topic_tokens = set(topic_name.lower().split())
            
            # Calculate overlap
            overlap = len(user_tokens.intersection(topic_tokens))
            
            # Simple heuristic: exact phrase match gets a boost
            if topic_name.lower() in user_question.lower():
                overlap += 2
            
            if overlap > max_overlap:
                max_overlap = overlap
                best_topic = item
        
        # threshold: at least 1 significant token match or phrase match
        return best_topic if max_overlap > 0 else None

    def construct_prompt(self, user_question, topic_data, mode, language):
        # Determine keys based on language
        suffix = "_hi" if language == "hi" else ""
        
        # Fetch fields with fallback to English keys if specific lang key missing
        # (Useful if mixed content, but assuming strict schema here)
        simple_key = f"simple_explanation{suffix}"
        normal_key = f"normal_explanation{suffix}"
        faq_key = f"faq{suffix}"
        examples_key = f"examples{suffix}" # Assuming examples might be localized too if present
        
        # Fallbacks for robustness
        explanation = topic_data.get(simple_key) or topic_data.get("simple_explanation", "")
        if mode != "beginner":
             explanation = topic_data.get(normal_key) or topic_data.get("normal_explanation", "")
        
        # FAQs (List)
        faqs = topic_data.get(faq_key) or topic_data.get("faq", [])
        formatted_faqs = ""
        if isinstance(faqs, list):
            # Handle if FAQs are strings or objects
            if faqs and isinstance(faqs[0], dict) and 'q' in faqs[0]:
                formatted_faqs = "\n".join([f"Q: {f['q']} A: {f['a']}" for f in faqs])
            else:
                 formatted_faqs = "\n".join([f"- {f}" for f in faqs])

        # Construct context
        context_block = f"{explanation}\n\nCommon Questions:\n{formatted_faqs}"

        system_instruction = "Explain simply. Imagine explaining to a 10-year-old."
        if mode != "beginner":
            system_instruction = "Explain normally. Professional but accessible."

        return f"""
CONTEXT:
{context_block}

USER QUESTION:
{user_question}

INSTRUCTIONS: 
{system_instruction}
Answer based ONLY on the provided context if possible.
"""

    def get_answer(self, user_id, user_question, language="en"):
        # 1. Check if they need help
        self.personalization.check_struggle(user_id, [user_question])
        current_mode = self.personalization.get_user_mode(user_id)
        
        # Select content based on language
        active_content = self.content_hi if language == "hi" else self.content_eng

        # 2. Find topic
        topic_obj = self.find_topic(user_question, active_content)
        
        if not topic_obj:
            refusal_msg = "I can only help you with the financial topics in my database."
            if language == "hi":
                refusal_msg = "Maaf karein, main keval database mein upalabdh vitteey vishayon par madad kar sakta hoon."
            
            return {
                "response": refusal_msg,
                "mode_used": current_mode,
                "topic_found": None
            }
            
        # 3. Make the prompt
        prompt = self.construct_prompt(user_question, topic_obj, current_mode, language)
        
        # 4. Ask the AI
        response = call_gemini_api(prompt)
        
        return {
            "response": response,
            "mode_used": current_mode,
            "topic_found": topic_obj.get("topic")
        }

if __name__ == "__main__":
    bot = FinancialBot()
    current_lang = "en" # Default language
    
    print("--- Person B Financial Bot Logic (Simulated AI) ---")
    print("Type 'quit' to exit.")
    print("Commands: 'struggle' (Beginner Mode), 'hindi' (Switch to Hindi), 'english' (Switch to English)")
    print("-" * 50)

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            break
            
        if user_input.lower() == 'struggle':
            bot.personalization.update_preference("current_user", "switch_beginner")
            print("[System] Mode switched to Beginner due to user struggle.")
            continue
            
        if user_input.lower() == 'hindi':
            current_lang = "hi"
            print("[System] Language switched to Hindi.")
            continue

        if user_input.lower() == 'english':
            current_lang = "en"
            print("[System] Language switched to English.")
            continue
            
        # Get answer
        result = bot.get_answer("current_user", user_input, language=current_lang)
        
        # Print formatted output
        print(f"Bot ({result['mode_used']} mode, {current_lang}):")
        print(result['response'])
        
        if result['topic_found']:
            print(f"\n[Debug] Topic: {result['topic_found']}")
