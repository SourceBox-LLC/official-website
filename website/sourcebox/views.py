from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, send_from_directory, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import safe_join, secure_filename
import os, requests
from website.models import PlatformUpdates
from website.models import User, UserHistory
from .. import db

views = Blueprint('views', __name__, template_folder='templates')

UPLOAD_FOLDER = '/workspaces/SourceBox-official-website/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def record_user_history(action):
    # record user history
    history = UserHistory(user_id=current_user.id, action=action)
    db.session.add(history)
    db.session.commit()

@views.route('/')
@views.route('/landing')
def landing():
    return render_template('landing.html')

@views.route('/dashboard')
@login_required
def dashboard():
    record_user_history("entered dashboard")
    user_id = current_user.id
    
    # Retrieve all history items (you might limit this if it's a very large dataset)
    all_history_items = UserHistory.query.filter_by(user_id=user_id).order_by(UserHistory.timestamp.desc()).all()
    
    # Use a set to track seen actions to remove duplicates
    seen_actions = set()
    unique_filtered_items = []
    for item in all_history_items:
        if item.action in ("entered wikidoc", "entered codedoc", "entered source-lightning", "entered pack-man", "entered source-mail") and item.action not in seen_actions:
            unique_filtered_items.append(item)
            seen_actions.add(item.action)
    
    # Now unique_filtered_items contains unique items by action, 
    # but you might want to limit to the last 5 unique items if the list is too long
    if len(unique_filtered_items) > 5:
        unique_filtered_items = unique_filtered_items[:5]
    
    return render_template('dashboard.html', last_5_history_items=unique_filtered_items)

@views.route('/updates')
def updates():
    all_updates = PlatformUpdates.query.all()
    record_user_history("entered updates")
    return render_template('updates.html', all_updates=all_updates)

@views.route('/content')
@login_required
def content():
    record_user_history("entered content")
    return render_template('content.html')

@views.route('/content/wikidoc')
@login_required
def launch_wikidoc():
    return redirect(url_for('service.wikidoc'))

@views.route('/content/codedoc')
@login_required
def launch_codedoc():
    return redirect(url_for('service.codedoc'))

@views.route('/content/source-lightning')
@login_required
def launch_source_lightning():
    return redirect(url_for('service.source_lightning'))

@views.route('/content/pack-man')
@login_required
def launch_pack_man():
    return redirect(url_for('service.pack_man'))

@views.route('/content/source-mail')
@login_required
def launch_source_mail():
    return redirect(url_for('service.source_mail'))

@views.route('/docs')
def documentation():
    record_user_history("entered docs")
    return render_template('docs.html')

@views.route('/user_settings')
@login_required
def user_settings():
    record_user_history("entered settings")
    return render_template('user_settings.html')

@views.route('/premium_info')
def premeum_info():
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
    data = {'user_message': 'You suck I hate you!'}
    session = requests.Session()
    base_url = 'https://sourcebox-rag-api-9f82a9c7f128.herokuapp.com'
    # 3. Get sentiment response
    sentiment_response_url = f'{base_url}/sentiment-pipe'
    response = session.post(sentiment_response_url, json=data)
    sentiment_response = response.json()
    print("sentiment response:", sentiment_response)
    return jsonify(message=sentiment_response.get('message', 'No message'), error=sentiment_response.get('error'))
