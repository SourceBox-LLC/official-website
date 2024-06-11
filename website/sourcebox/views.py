from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, send_from_directory, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import safe_join, secure_filename
import os, requests
from website.models import PlatformUpdates
from website.models import User, UserHistory
from .. import db

views = Blueprint('views', __name__, template_folder='templates')


def record_user_history(action):
     #record user history
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


#download boilerplate landing.html example
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

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@views.route('/g-thropic-api', methods=['POST'])
def g_thropic_api():
    print("Route /g-thropic-api accessed")
    print("Request method:", request.method)

    if 'file' not in request.files:
        print("No file part in the request")
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    prompt = request.form.get('prompt')

    if not prompt:
        print("No prompt provided")
        return jsonify({"error": "No prompt provided"}), 400

    print(f"Prompt received by user: {prompt}")
    print(f"Filename received: {file.filename}")



    def rag_function(file, prompt):
        print("Inside rag_function")
        BASE_URL = "https://1rhj1momh3.execute-api.us-east-2.amazonaws.com/first-deploy"
        headers = {
            "Accept": "application/json"
        }

        if file.filename == '':
            print("No selected file")
            return jsonify({"error": "No selected file"}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join('/workspaces/python-11/uploads', filename)  # Change this to your desired upload path
            print(f"Saving file to {file_path}")
            file.save(file_path)

            # Now handle the file upload part
            with open(file_path, 'rb') as f:
                files = {'file': f}
                print("Sending POST request to /openai-rag-test with file...")
                response = requests.post(BASE_URL + f"/openai-rag-test?prompt={prompt}", headers=headers, files=files)

                print(f"POST /openai-rag-test response: {response.json()}")
                print(f"Response status code: {response.status_code}")
                return response
        else:
            print("File type not allowed")
            return jsonify({"error": "File type not allowed"}), 400

    result = rag_function(file, prompt)
    if isinstance(result, requests.Response):
        print("Returning JSON response from RAG function")
        print(result)
        return jsonify(result.json())
    print("Returning result directly from RAG function")
    return result
