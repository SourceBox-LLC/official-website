from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, session, jsonify, send_from_directory
from flask_login import login_required
from werkzeug.utils import secure_filename
import os
import requests
from website.authentication.auth import token_required
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import logging
from openai import OpenAI
from dotenv import load_dotenv
import shutil
import tempfile
import subprocess
import stripe
import markdown

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@views.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').lower().strip()

    if not query:
        flash('Please enter a search term.', 'danger')
        return redirect(url_for('views.landing'))

    available_pages = [
        {'name': 'Dashboard', 'url': url_for('views.dashboard')},
        {'name': 'Updates', 'url': url_for('views.updates')},
        {'name': 'Services', 'url': url_for('views.content')},
        {'name': 'DeepQuery', 'url': url_for('views.launch_deepquery')},
        {'name': 'Source Lightning', 'url': url_for('views.launch_source_lightning')},
        {'name': 'Pack-Man', 'url': url_for('views.launch_pack_man')},
        {'name': 'VideoGen', 'url': url_for('views.launch_videogen')},
        {'name': 'U-Studio', 'url': url_for('views.launch_u_studio')},
        {'name': 'Documentation', 'url': url_for('views.documentation')},
        {'name': 'User Settings', 'url': url_for('views.user_settings')},
        {'name': 'Premium Info', 'url': url_for('views.premium_info')},
        {'name': 'Platform Support', 'url': url_for('views.platform_support')},
        {'name': 'Learn More', 'url': url_for('views.learn_more')}
    ]

    # Filter results based on the search query
    results = []
    for page in available_pages:
        if query in page['name'].lower():
            results.append(page)

    if not results:
        flash('No matching pages found.', 'warning')
        return redirect(url_for('views.landing'))

    return render_template('search_results.html', query=query, results=results)

@views.route('/')
def landing():
    return render_template('landing.html')

@views.route('/dashboard')
@token_required
def dashboard():
    record_user_history("entered dashboard")

    token = session.get('access_token')
    headers = {'Authorization': f'Bearer {token}'}

    # Attempt to fetch user ID
    user_id_url = f"{API_URL}/user/id"
    user_id_response = requests.get(user_id_url, headers=headers)
    if user_id_response.status_code == 200:
        user_id = user_id_response.json().get('user_id')
    else:
        logger.warning("Failed to retrieve user ID from %s. Proceeding without user_id-based features.", user_id_url)
        user_id = None

    # Check if the user is premium only if we have a user_id
    is_premium = False
    if user_id:
        premium_status_url = f"{API_URL}/user/{user_id}/premium/status"
        premium_resp = requests.get(premium_status_url, headers=headers)
        if premium_resp.status_code == 200:
            premium_data = premium_resp.json()
            is_premium = premium_data.get('premium_status', False)
        else:
            logger.warning("Could not retrieve premium status for user_id=%s", user_id)

    # Fetch user history
    history_resp = requests.get(f"{API_URL}/user_history", headers=headers)
    if history_resp.status_code == 200:
        all_history_items = history_resp.json()

        # Use a set to track seen actions to remove duplicates
        seen_actions = set()
        unique_filtered_items = []
        for item in all_history_items:
            if item['action'] in (
                "entered wikidoc",
                "entered source-lightning",
                "entered pack-man",
                "entered source-mail"
            ) and item['action'] not in seen_actions:
                unique_filtered_items.append(item)
                seen_actions.add(item['action'])

        # Limit to five items
        if len(unique_filtered_items) > 5:
            unique_filtered_items = unique_filtered_items[:5]

        # Token usage logic
        free_token_limit = 1000000
        token_count_url = f"{API_URL}/user/token_usage"
        token_count_response = requests.get(token_count_url, headers=headers)
        if token_count_response.status_code == 200:
            tokens_used = token_count_response.json().get('total_tokens', 0)
        else:
            logger.warning("Failed to retrieve token usage; defaulting tokens_used=0.")
            tokens_used = 0

        token_percentage_used = (tokens_used / free_token_limit) * 100 if free_token_limit > 0 else 0

        return render_template(
            'dashboard.html',
            is_premium=is_premium,
            last_5_history_items=unique_filtered_items,
            free_token_limit=free_token_limit,
            tokens_used=tokens_used,
            token_percentage_used=token_percentage_used
        )
    else:
        flash("Failed to retrieve user history.", "warning")
        return render_template(
            'dashboard.html',
            is_premium=is_premium,
            last_5_history_items=[],
            free_token_limit=0,
            tokens_used=0,
            token_percentage_used=0
        )

@views.route('/updates')
def updates():
    # Use the new '/platform_updates/list' endpoint to get updates
    response = requests.get(f"{API_URL}/platform_updates/list")
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

    token = session.get('access_token')
    headers = {'Authorization': f'Bearer {token}'}

    # Attempt to retrieve user ID
    user_id_url = f"{API_URL}/user/id"
    user_id_response = requests.get(user_id_url, headers=headers)
    if user_id_response.status_code == 200:
        user_id = user_id_response.json().get('user_id')
    else:
        logger.warning("Failed to retrieve user ID from %s. Continuing without user-specific data.", user_id_url)
        user_id = None

    # Check if user is premium only if user_id exists
    is_premium = False
    if user_id:
        premium_status_url = f"{API_URL}/user/{user_id}/premium/status"
        premium_resp = requests.get(premium_status_url, headers=headers)
        if premium_resp.status_code == 200:
            premium_data = premium_resp.json()
            is_premium = premium_data.get('premium_status', False)
        else:
            logger.warning("Could not retrieve premium status for user_id=%s", user_id)

    return render_template('content.html', is_premium=is_premium)

@views.route('/content/deepquery')
@token_required
def launch_deepquery():
    return redirect(url_for('service.deepquery'))

@views.route('/content/source-lightning')
@token_required
def launch_source_lightning():
    return redirect(url_for('service.source_lightning'))

@views.route('/content/pack-man')
@token_required
def launch_pack_man():
    return redirect(url_for('service.pack_man'))

@views.route('/premium_info')
@token_required
def premium_info():
    # Fetch the token from the session
    token = session.get('access_token')
    headers = {'Authorization': f'Bearer {token}'}

    # Fetch the user ID
    user_id_url = f"{API_URL}/user/id"
    user_id_response = requests.get(user_id_url, headers=headers)
    if user_id_response.status_code == 200:
        user_id = user_id_response.json().get('user_id')
    else:
        flash('Failed to retrieve user ID', 'error')
        return redirect(url_for('views.landing'))

    # Check if the user is a premium member
    premium_status_url = f"{API_URL}/user/{user_id}/premium/status"
    response = requests.get(premium_status_url, headers=headers)
    if response.status_code == 200:
        premium_data = response.json()
        is_premium = premium_data.get('premium_status', False)
    else:
        is_premium = False

    # Redirect to the dashboard if the user is already premium
    if is_premium:
        return redirect(url_for('views.dashboard'))
    else:
        return render_template('premium_info.html')

@views.route('/user_settings')
@token_required
def user_settings():
    record_user_history("entered user_settings")

    token = session.get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    user_id_url = f"{API_URL}/user/id"

    user_id_response = requests.get(user_id_url, headers=headers)
    if user_id_response.status_code == 200:
        user_id = user_id_response.json().get('user_id')
    else:
        logger.warning("Failed to retrieve user ID from %s. Some profile data may be unavailable.", user_id_url)
        user_id = None

    # Proceed with partial data if user_id is None
    return render_template('user_settings.html', user_id=user_id)

@views.route('/documentation')
def documentation():
    record_user_history("entered documentation")
    return render_template('docs.html')

@views.route('/platform_support')
def platform_support():
    record_user_history("entered support")
    return render_template('support.html')

@views.route('/learn_more')
def learn_more():
    record_user_history("entered learn_more")
    return render_template('learn_more.html')

@views.route('/documentation/help')
def documentation_help():
    record_user_history("entered doc help")
    return render_template('help.html')

# First route for support messages
@views.route('/send_message', methods=['POST'])
def send_support_message():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    if not name or not email or not message:
        flash('All fields are required!', 'danger')
        return redirect(url_for('index'))

    full_message = f"Name: {name}\nEmail: {email}\nMessage: {message}"

    try:
        msg = MIMEMultipart()
        msg['From'] = os.getenv('GMAIL_USERNAME')
        msg['To'] = os.getenv('GMAIL_USERNAME')
        msg['Subject'] = "SourceBox Support Ticket Request"

        msg.attach(MIMEText(full_message, 'plain'))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(os.getenv('GMAIL_USERNAME'), os.getenv('GOOGLE_PASSWORD'))
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


# premium unsubscribe page
@views.route('/premium_unsubscribe', methods=['GET', 'POST'])
@token_required
def premium_unsubscribe():
    return render_template('premium_unsubscribe.html')

# confirmed premium unsubscribe
@views.route('/premium_unsubscribe_confirm', methods=['POST'])
@token_required
def premium_unsubscribe_confirm():
    # Get the user's token from the session
    token = session.get('access_token')
    headers = {'Authorization': f'Bearer {token}'}

    # Fetch the user ID from your API
    user_id_url = f"{API_URL}/user/id"
    user_id_response = requests.get(user_id_url, headers=headers)

    if user_id_response.status_code == 200:
        user_id = user_id_response.json().get('user_id')
        logger.info(f"User ID {user_id} retrieved successfully.")
    else:
        logger.error("Failed to retrieve user ID.")
        flash('Failed to retrieve user ID', 'error')
        return redirect(url_for('views.user_settings'))

    # Get the Stripe subscription ID from your API
    stripe_subscription_url = f"{API_URL}/user/{user_id}/stripe_subscription"
    stripe_response = requests.get(stripe_subscription_url, headers=headers)

    if stripe_response.status_code == 200:
        stripe_subscription_id = stripe_response.json().get('stripe_subscription_id')

        # Check if the subscription ID exists and is valid
        if not stripe_subscription_id:
            logger.error(f"No active Stripe subscription ID found for user {user_id}.")
            flash('Your subscription is not active or already canceled. Please contact support if this is an error.', 'error')
            return redirect(url_for('views.user_settings'))
        else:
            logger.info(f"Retrieved Stripe subscription ID: {stripe_subscription_id}")

            # Cancel the Stripe subscription at the end of the billing cycle
            try:
                stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
                stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=True  # Cancel at the end of the billing cycle
                )
                logger.info(f"Subscription {stripe_subscription_id} set to cancel at period end.")
                flash('Your subscription has been canceled. Premium access will continue until the end of the billing period.', 'success')

                # Do not remove premium status yet. We wait for the Stripe webhook (customer.subscription.deleted)
                # to handle the actual removal at the end of the billing cycle.

            except stripe.error.StripeError as e:
                logger.error(f"Stripe error during subscription cancellation: {e}")
                flash('Failed to cancel your Stripe subscription. Please contact support.', 'error')
                return redirect(url_for('views.user_settings'))
    else:
        logger.error(f"Failed to retrieve Stripe subscription for user {user_id}.")
        flash('Failed to retrieve your Stripe subscription. Please contact support.', 'error')
        return redirect(url_for('views.user_settings'))

    # Redirect the user to the dashboard
    return redirect(url_for('views.dashboard'))

# Download boilerplate landing.html example
@views.route('/download_plate/<filename>')
def download_plate(filename):

    def clone_and_zip_repo(REPO_URL, repo_name):
        # Get the current working directory
        cwd = os.getcwd()
        
        # Create a temporary directory in the current working directory
        temp_dir = tempfile.mkdtemp(dir=cwd)
        print(f"Cloning repository to temporary folder in CWD: {temp_dir}")
        
        try:
            # Clone the repository using subprocess
            subprocess.run(["git", "clone", REPO_URL, temp_dir], check=True)
            print(f"Repository successfully cloned to {temp_dir}")
            
            # Create a parent folder in the temp directory named after the repo
            parent_folder_name = f"{repo_name}_repo"
            parent_folder_path = os.path.join(temp_dir, parent_folder_name)
            os.makedirs(parent_folder_path)
            
            # Move the cloned repo contents into the parent folder
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if item != parent_folder_name:  # Skip the parent folder itself
                    shutil.move(item_path, parent_folder_path)
            
            # Create a zip file from the parent folder
            zip_filename = os.path.join(cwd, f'{parent_folder_name}.zip')
            shutil.make_archive(zip_filename.replace('.zip', ''), 'zip', temp_dir, parent_folder_name)
            print(f"Repository successfully zipped at {zip_filename}")
            
            return zip_filename
        except subprocess.CalledProcessError as e:
            print(f"Error cloning repository: {e}")
            return None
        finally:
            # Clean up the temporary directory
            shutil.rmtree(temp_dir)
            print(f"Temporary directory {temp_dir} has been removed.")


    def serve_repo(REPO_URL, repo_name):
        # Clone and zip the repo, then get the zip file path
        zip_file_path = clone_and_zip_repo(REPO_URL, repo_name)
            
        if zip_file_path and os.path.exists(zip_file_path):
            # Store the zip file path in the request context for deletion later
            request.zip_file_path = zip_file_path
                
            # Serve the zip file to the user for download
            return send_from_directory(os.path.dirname(zip_file_path), os.path.basename(zip_file_path), as_attachment=True)
        else:
            abort(500, description="Error cloning or zipping the repository")
    
    PC_SCANNER_REPO = "https://github.com/SourceBox-LLC/SourceLighting-PC-scannerApp.git"
    VANILLA_GPT_REPO = "https://github.com/SourceBox-LLC/SourceLightning-Vanilla-GPT.git"
    VANILLA_CLAUD_REPO = "https://github.com/SourceBox-LLC/SourceLightning-Vanilla-Claude.git"

    if filename == "pc_scanner":
        return serve_repo(PC_SCANNER_REPO, "pc_scanner")
    elif filename == "vanilla_gpt":
        return serve_repo(VANILLA_GPT_REPO, "vanilla_gpt")
    elif filename == "vanilla_claud":
        return serve_repo(VANILLA_CLAUD_REPO, "vanilla_claud")
    else:
        abort(404, description="Repository not found")

@views.route('/rag-api', methods=['POST'])
def rag_api():
    try:
        # Get the new base URL of the external API
        base_url = 'https://sb-general-llm-api-248b890f970f.herokuapp.com/landing-rag-example'

        # Check if the request has JSON content type, otherwise handle form data
        if request.content_type == 'application/json':
            data = request.get_json()
        else:
            data = request.form

        prompt = data.get('prompt')

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        # Prepare the payload to send to the external API
        payload = {"prompt": prompt}

        # Make the POST request to the external API
        response = requests.post(base_url, json=payload)

        # Check if the request was successful
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to get a response from external API", "details": response.text}), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@views.route('/rag-api-sentiment', methods=['POST'])
def rag_api_sentiment():
    try:
        # Get the base URL of the external sentiment analysis API
        base_url = 'https://sb-general-llm-api-248b890f970f.herokuapp.com/landing-sentiment-example'

        # Check if the request has JSON content type, otherwise handle form data
        if request.content_type == 'application/json':
            data = request.get_json()  # Handle JSON request
        else:
            data = request.form  # Handle form data request

        prompt = data.get('prompt')

        # Validate the prompt
        if not prompt or not isinstance(prompt, str) or not prompt.strip():
            return jsonify({"error": "Prompt is required"}), 400

        # Prepare the payload to send to the external API
        payload = {"prompt": prompt}

        # Make a POST request to the external API
        response = requests.post(base_url, json=payload)

        # Check if the request to the external API was successful
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to get a response from external API", "details": response.text}), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@views.route('/rag-api-webscrape', methods=['POST'])
def rag_api_webscrape():
    try:
        # Get the base URL of the external web scraping API
        base_url = 'https://sb-general-llm-api-248b890f970f.herokuapp.com/landing-webscrape-example'

        # Check if the request has JSON content type, otherwise handle form data
        if request.content_type == 'application/json':
            data = request.get_json()  # Handle JSON request
        else:
            data = request.form  # Handle form data request

        prompt = data.get('prompt')

        # Validate the prompt
        if not prompt or not isinstance(prompt, str) or not prompt.strip():
            return jsonify({"error": "Prompt is required"}), 400

        # Prepare the payload to send to the external API
        payload = {"prompt": prompt}

        # Make a POST request to the external API
        response = requests.post(base_url, json=payload)

        # Check if the request to the external API was successful
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to get a response from external API", "details": response.text}), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@views.route('/rag-api-image', methods=['POST'])
def image_generation():
    try:
        # Get the base URL of the external image generation API
        base_url = 'https://sb-general-llm-api-248b890f970f.herokuapp.com/landing-imagegen-example'

        # Check if the request has JSON content type, otherwise handle form data
        if request.content_type == 'application/json':
            data = request.get_json()  # Handle JSON request
        else:
            data = request.form  # Handle form data request

        prompt = data.get('prompt')

        # Validate the prompt
        if not prompt or not isinstance(prompt, str) or not prompt.strip():
            return jsonify({"error": "Prompt is required"}), 400

        # Prepare the payload to send to the external API
        payload = {"prompt": prompt}

        # Make a POST request to the external API
        response = requests.post(base_url, json=payload)

        # Check if the request to the external API was successful
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to get a response from external API", "details": response.text}), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@views.route('/rag-api-transcript', methods=['GET'])
def audio_transcript():
    try:
        # Define the URL for the existing transcription resource
        base_url = 'https://sb-general-llm-api-248b890f970f.herokuapp.com/landing-transcript-example'

        # Make the GET request to the transcription resource
        response = requests.get(base_url)

        # Check if the request to the external API was successful
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to get a response from transcription resource", "details": response.text}), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# support ticket form
@views.route('/platform-support', methods=['GET','POST'])
def platform_support_page():
    return render_template('support.html')

@views.route('/send_message', methods=['POST'])
def send_contact_message():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    if not name or not email or not message:
        flash('All fields are required!', 'danger')
        return redirect(url_for('index'))

    full_message = f"Name: {name}\nEmail: {email}\nMessage: {message}"

    try:
        msg = MIMEMultipart()
        msg['From'] = os.getenv('GMAIL_USERNAME')
        msg['To'] = os.getenv('GMAIL_USERNAME')
        msg['Subject'] = "SourceBox Support Ticket Request"

        msg.attach(MIMEText(full_message, 'plain'))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(os.getenv('GMAIL_USERNAME'), os.getenv('GOOGLE_PASSWORD'))
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

@views.route('/chat_assistant', methods=['POST'])
def chat_assistant_route():
    user_message = request.json.get("message")

    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": user_message,
            }
        ],
        model="gpt-3.5-turbo",
    )

    assistant_message = chat_completion.choices[0].message.content
    print(assistant_message)
    return jsonify({"message": assistant_message})


