from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, session, jsonify
from flask_login import login_required
from werkzeug.utils import secure_filename
import os, requests
from website.authentication.auth import token_required
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


# Set up logging
logging.basicConfig(level=logging.INFO)


views = Blueprint('views', __name__, template_folder='templates')

API_URL = os.getenv('API_URL', 'http://localhost:5000')  # Use env variable for API URL
UPLOAD_FOLDER = '/tmp/uploads'  # Use writable directory on Heroku
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def record_user_history(action):
    token = session.get('access_token')
    if token:
        headers = {'Authorization': f'Bearer {token}'}
        data = {'action': action}
        response = requests.post(f"{API_URL}/user_history", json=data, headers=headers)
        if response.status_code != 201:
            flash('Failed to record user history', 'error')

@views.route('/')
@views.route('/landing')
def landing():
    return render_template('landing.html')

@views.route('/learn_more')
def learn_more():
    return render_template('learn_more.html')

@views.route('/dashboard')
@token_required
def dashboard():
    record_user_history("entered dashboard")


    token = session.get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f"{API_URL}/user_history", headers=headers)

    if response.status_code == 200:
        all_history_items = response.json()

        # Use a set to track seen actions to remove duplicates
        seen_actions = set()
        unique_filtered_items = []
        for item in all_history_items:
            if item['action'] in ("entered wikidoc", "entered codedoc", "entered source-lightning", "entered pack-man", "entered source-mail") and item['action'] not in seen_actions:
                unique_filtered_items.append(item)
                seen_actions.add(item['action'])

        # Now unique_filtered_items contains unique items by action, 
        # but you might want to limit to the last 5 unique items if the list is too long
        if len(unique_filtered_items) > 5:
            unique_filtered_items = unique_filtered_items[:5]
        
        free_token_limit = 50000000000000000
        #TODO get token usage from the API
        token_count_url = f'{API_URL}/user/token_usage'
        headers = {'Authorization': f'Bearer {token}'}
        try:
            response = requests.get(token_count_url, headers=headers)
            if response.status_code == 200:
                token_data = response.json()

                tokens_used = token_data.get('total_tokens')
            else:
                print(f"Failed to get token count. Status code: {response.status_code}, Response: {response.text}")

        except requests.RequestException as e:
            print(f"Error fetching token count: {e}")


        

        # Ensure the token percentage is properly calculated
        if free_token_limit > 0:
            token_percentage_used = (tokens_used / free_token_limit) * 100
        else:
            token_percentage_used = 0
        

        return render_template('dashboard.html', last_5_history_items=unique_filtered_items, free_token_limit=free_token_limit, tokens_used=tokens_used, token_percentage_used=token_percentage_used)
    else:
        flash('Failed to retrieve user history', 'error')
        return redirect(url_for('views.landing'))

@views.route('/updates')
@token_required
def updates():
    response = requests.get(f"{API_URL}/platform_updates")
    if response.status_code == 200:
        all_updates = response.json()
        record_user_history("entered updates")
        return render_template('updates.html', all_updates=all_updates)
    else:
        flash('Failed to retrieve updates', 'error')
        return redirect(url_for('views.landing'))

@views.route('/content')
@token_required
def content():
    record_user_history("entered content")
    return render_template('content.html')

@views.route('/content/wikidoc')
@token_required
def launch_wikidoc():
    return redirect(url_for('service.wikidoc'))

@views.route('/content/codedoc')
@token_required
def launch_codedoc():
    return redirect(url_for('service.codedoc'))

@views.route('/content/source-lightning')
@token_required
def launch_source_lightning():
    return redirect(url_for('service.source_lightning'))

@views.route('/content/pack-man')
@token_required
def launch_pack_man():
    return redirect(url_for('service.pack_man'))


@views.route('/content/imagen')
@token_required
def launch_imagen():
    return redirect(url_for('service.imagen'))


@views.route('/docs')
def documentation():
    record_user_history("entered docs")
    return render_template('docs.html')

@views.route('/user_settings')
@token_required
def user_settings():
    record_user_history("entered settings")
    return render_template('user_settings.html')

@views.route('/premium_info')
def premium_info():
    return render_template('premium_info.html')

# Download boilerplate landing.html example
DOWNLOAD_DIRECTORY = os.path.join(os.getcwd(), 'SourceLightning')
@views.route('/download_plate/<filename>')
def download_plate(filename):
    # Prevent directory traversal vulnerability
    safe_path = safe_join(DOWNLOAD_DIRECTORY, filename)
    # Check if the file exists
    if not os.path.isfile(safe_path):
        abort(404)
    # Serve the file for download
    return send_from_directory(DOWNLOAD_DIRECTORY, filename, as_attachment=True)

@views.route('/rag-api', methods=['POST'])
def rag_api():
    # Initialize the session
    session = requests.Session()
    # Define the base URL
    base_url = 'https://sb-general-llm-api-1d86f3b698a2.herokuapp.com'

    # 1. Upload the file
    upload_url = f'{base_url}/upload'
    file = request.files.get('file')

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = session.post(upload_url, files=files)
            upload_response = response.json()
            print("Upload response:", upload_response)

        # 2. Retrieve the list of uploaded files
        retrieve_files_url = f'{base_url}/retrieve-files'
        response = session.get(retrieve_files_url)
        retrieve_files_response = response.json()
        print("Retrieve files response:", retrieve_files_response)

        # 3. Get GPT-3 response
        gpt_response_url = f'{base_url}/gpt-response'
        data = {'user_message': 'Explain the content of the uploaded file'}
        response = session.post(gpt_response_url, json=data)
        gpt_response = response.json()
        print("GPT response:", gpt_response)

        # 4. Delete the session and all associated files
        delete_session_url = f'{base_url}/delete-session'
        response = session.delete(delete_session_url)
        delete_session_response = response.json()
        print("Delete session response:", delete_session_response)

        return jsonify(message=gpt_response.get('message', 'No message'), error=gpt_response.get('error'))
    else:
        return jsonify(error="Invalid file type"), 400


@views.route('/rag-api-sentiment', methods=['POST'])
def rag_api_sentiment():
    data = {'user_message': request.form.get('prompt', '')}
    session = requests.Session()
    base_url = 'https://sb-general-llm-api-1d86f3b698a2.herokuapp.com'

    # Get sentiment response
    sentiment_response_url = f'{base_url}/sentiment-pipe'
    response = session.post(sentiment_response_url, json=data)
    sentiment_response = response.json()
    print("Sentiment response:", sentiment_response)
    return jsonify(message=sentiment_response.get('message', 'No message'), error=sentiment_response.get('error'))


# support ticket form
@views.route('/platform-support', methods=['GET','POST'])
@token_required
def platform_support():
    return render_template('support.html')


# send support ticket
@views.route('/send_message', methods=['POST'])
def send_message_route():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    # Check if all fields are completed
    if not name or not email or not message:
        flash('All fields are required!', 'danger')
        return redirect(url_for('index'))

    # Combine name, email, and message into a single string to return
    full_message = f"Name: {name}\nEmail: {email}\nMessage: {message}"

    try:
        # Create the email content
        msg = MIMEMultipart()
        msg['From'] = os.getenv('GMAIL_USERNAME')
        msg['To'] = os.getenv('GMAIL_USERNAME')
        msg['Subject'] = "SourceBox Support Ticket Request"

        # Attach the message
        msg.attach(MIMEText(full_message, 'plain'))

        # Connect to the server and send the email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(os.getenv('GMAIL_USERNAME'), os.getenv('GOOGLE_PASSWORD'))  # Hide before GitHub push
        server.send_message(msg)
        server.quit()

        flash('Message sent successfully!', 'success')
    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"SMTP Authentication Error: {e}")
        flash(f'Failed to send message. Error: {str(e)}', 'danger')
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        flash(f'Failed to send message. Error: {str(e)}', 'danger')

    return redirect(url_for('views.platform_support'))



# user support chatbot
@views.route('/chat_assistant', methods=['POST'])
def chat_assistant_route():
    user_message = request.json.get("message")

    client = OpenAI(
        # This is the default and can be omitted
        api_key = os.getenv('OPENAI_API_KEY')
    )

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": user_message,
            }
        ],
        model="gpt-3.5-turbo",
    )

    # Access the content using the 'message' attribute of the Choice object
    assistant_message = chat_completion.choices[0].message.content
    print(assistant_message)
    return jsonify({"message": assistant_message})
