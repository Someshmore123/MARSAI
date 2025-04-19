from flask import Flask, render_template, session, redirect, jsonify, request
from functools import wraps
import pymongo
import openai
from bson import ObjectId
from passlib.hash import pbkdf2_sha256
import uuid

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

base_url="https://openrouter.ai/api/v1"
api_key="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"


# ✅ Database Connection
client = pymongo.MongoClient('mongodb+srv://somesh_more:Somesh123@mars.w1br07q.mongodb.net/MarsGPT')
db = client.get_database('MarsGPT')

# ✅ Login Required Decorator
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user' in session:
            return f(*args, **kwargs)
        return redirect('/login')
    return wrap

# ✅ Routes
@app.route("/login")
def login_page():
    return render_template("home.html")

@app.route('/user/signup', methods=['POST'])
def signup():
    return User().signup()

@app.route('/user/signout')
def signout():
    session.clear()
    return redirect('/login')

@app.route('/user/login', methods=['POST'])
def login():
    return User().login()

@app.route('/dashboard/')
@login_required
def dashboard():
    user_id = session.get('user', {}).get('_id')
    myChats = list(db.chats.find({"user_id": user_id})) if user_id else []
    return render_template("index.html", myChats=myChats, user=session.get('user'))

@app.route("/")
def home():
    myChats = list(db.chats.find({}))  
    user = session.get('user')  
    return render_template("index.html", myChats=myChats, user=user)

# ✅ Retrieve a specific chat by chat_id
@app.route("/chat/<chat_id>", methods=["GET"])
def view_chat(chat_id):
    chat = db.chats.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        return "Chat not found", 404
    return jsonify({"question": chat.get('question'), "answer": chat.get('answer')})

@app.route("/api", methods=["GET", "POST"])
def qa():
    if request.method == "POST":
        question = request.json.get("question")

        if not question:
            print("❌ ERROR: No question received in request!")
            return jsonify({"error": "No question provided"}), 400

        print(f"✅ Received Question: {question}")

        # ✅ Check if the question exists in the database
        chat = db.chats.find_one({"question": question})
        if chat:
            print("✅ Answer found in database!")
            return jsonify({"question": question, "answer": chat['answer']})

        # ✅ Generate a new response using OpenAI (Fixed API Key Issue)
        try:
            print("🔄 Calling OpenAI API...")

            # ✅ Create OpenAI client correctly
            client = openai.OpenAI(api_key="your_openrouter_api_key_here")

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": question}],
                temperature=0.7,
                max_tokens=200
            )

            if not response or not response.choices:
                print("❌ ERROR: Empty response from OpenAI!")
                return jsonify({"error": "AI did not return a response"}), 500

            answer = response.choices[0].message.content.strip().replace("\n", "<br/>")
            print(f"✅ AI Response: {answer}")

            if 'user' in session:
                db.chats.insert_one({"user_id": session['user']['_id'], "question": question, "answer": answer})

            return jsonify({"question": question, "answer": answer})

        except openai.APIError as e:
            print(f"❌ OpenAI API Error: {e}")
            return jsonify({"error": str(e)}), 500

    return jsonify({"result": "Welcome to the API! Send a POST request with a question."})

# ✅ User Class for Signup & Login
class User:
    def start_session(self, user):
        del user['password']
        session['user'] = user
        return jsonify(user), 200

    def signup(self):
        user = {
            "_id": uuid.uuid4().hex,
            "name": request.form.get('name'),
            "email": request.form.get('email'),
            "password": pbkdf2_sha256.hash(request.form.get('password'))
        }

        if db.users.find_one({"email": user['email']}):
            return jsonify({"error": "Email already in use"}), 400

        if db.users.insert_one(user):
            return self.start_session(user)

        return jsonify({"error": "Signup failed"}), 400

    def login(self):
        user = db.users.find_one({"email": request.form.get('email')})

        if user and pbkdf2_sha256.verify(request.form.get('password'), user['password']):
            return self.start_session(user)

        return jsonify({"error": "Invalid login credentials"}), 401

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

