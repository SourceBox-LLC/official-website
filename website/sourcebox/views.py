from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, session, jsonify, send_from_directory
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
import shutil, tempfile, subprocess
import stripe

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

    # Fetch the user ID first
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
        is_premium = False  # Default to non-premium if there's an issue

    # Fetch user history
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

        # Now unique_filtered_items contains unique items by action
        if len(unique_filtered_items) > 5:
            unique_filtered_items = unique_filtered_items[:5]

        # Token usage logic
        free_token_limit = 1000000
        token_count_url = f'{API_URL}/user/token_usage'
        response = requests.get(token_count_url, headers=headers)
        tokens_used = response.json().get('total_tokens', 0)

        token_percentage_used = (tokens_used / free_token_limit) * 100 if free_token_limit > 0 else 0

        # Pass the premium status and token usage data to the template
        return render_template(
            'dashboard.html',
            is_premium=is_premium,
            last_5_history_items=unique_filtered_items,
            free_token_limit=free_token_limit,
            tokens_used=tokens_used,
            token_percentage_used=token_percentage_used
        )
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

    # Fetch the access token from the session
    token = session.get('access_token')
    headers = {'Authorization': f'Bearer {token}'}

    # Fetch the user ID first
    user_id_url = f"{API_URL}/user/id"
    user_id_response = requests.get(user_id_url, headers=headers)
    if user_id_response.status_code == 200:
        user_id = user_id_response.json().get('user_id')
    else:
        flash('Failed to retrieve user ID', 'error')
        return redirect(url_for('views.landing'))

    # Check if the user is a premium member
    premium_status_url = f"{API_URL}/user/{user_id}/premium/status"
    premium_response = requests.get(premium_status_url, headers=headers)
    
    if premium_response.status_code == 200:
        premium_data = premium_response.json()
        is_premium = premium_data.get('premium_status', False)
    else:
        is_premium = False  # Default to non-premium if there's an issue

    # Render the content page and pass the premium status
    return render_template('content.html', is_premium=is_premium)


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


@views.route('/content/videogen')
@token_required
def launch_videogen():
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

    # Allow access only if the user is premium
    if is_premium:
        return redirect(url_for('service.videogen'))
    else:
        flash('Access to VideoGen is only available to premium members. Learn more about premium benefits.', 'warning')
        return redirect(url_for('views.premium_info'))


@views.route('/content/u-studio')
@token_required
def launch_u_studio():
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

    # Allow access only if the user is premium
    if is_premium:
        return redirect(url_for('service.u_studio'))
    else:
        flash('Access to U-Studio is only available to premium members. Learn more about premium benefits.', 'warning')
        return redirect(url_for('views.premium_info'))



@views.route('/docs')
def documentation():
    record_user_history("entered docs")
    return render_template('docs.html')

@views.route('/user_settings')
@token_required
def user_settings():
    record_user_history("entered settings")

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
        is_premium = False  # Default to non-premium if there's an issue

    return render_template('user_settings.html', is_premium=is_premium)

# premium unsubscribe page
@views.route('/premium_unsubscribe', methods=['GET', 'POST'])
@token_required
def premium_unsubscribe():
    return render_template('premium_unsubscribe.html')



# confirmed premium unsubscribe
# Confirmed premium unsubscribe
@views.route('/premium_unsubscribe_confirm', methods=['POST'])
@token_required
def premium_unsubscribe_confirm():
    logger.info("Premium unsubscribe process started.")

    # Get the user's token from the session
    token = session.get('access_token')
    headers = {'Authorization': f'Bearer {token}'}

    # Fetch the user ID from your API
    user_id_url = f"{API_URL}/user/id"
    try:
        user_id_response = requests.get(user_id_url, headers=headers)
        user_id_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to retrieve user ID: {e}", exc_info=True)
        flash('Failed to retrieve user ID. Please try again later.', 'error')
        return redirect(url_for('views.user_settings'))

    user_id = user_id_response.json().get('user_id')
    if not user_id:
        logger.error("User ID is missing from API response.")
        flash('Failed to retrieve user ID. Please contact support.', 'error')
        return redirect(url_for('views.user_settings'))

    logger.info(f"Successfully retrieved user ID: {user_id}")

    # Get the Stripe subscription ID from your API
    stripe_subscription_url = f"{API_URL}/user/{user_id}/stripe_subscription"
    try:
        stripe_response = requests.get(stripe_subscription_url, headers=headers)
        stripe_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to retrieve Stripe subscription: {e}", exc_info=True)
        flash('Failed to retrieve Stripe subscription. Please try again later.', 'error')
        return redirect(url_for('views.user_settings'))

    stripe_subscription_id = stripe_response.json().get('stripe_subscription_id')
    logger.info(f"Retrieved Stripe subscription ID: {stripe_subscription_id}")

    # Ensure the stripe_subscription_id is a valid string
    if isinstance(stripe_subscription_id, str) and stripe_subscription_id:
        try:
            # Cancel the Stripe subscription at the end of the billing cycle
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=True  # Cancel at the end of the billing cycle
            )
            logger.info(f"Successfully canceled subscription {stripe_subscription_id} for user {user_id}")
            flash('Your subscription has been canceled. Premium access will continue until the end of the billing period.', 'success')

            # Remove premium status via your API
            remove_premium_url = f"{API_URL}/user/{user_id}/premium/remove"
            response = requests.put(remove_premium_url, headers=headers)

            if response.status_code == 200:
                logger.info(f"Premium status successfully removed for user {user_id}.")
                flash('Your premium status has been updated.', 'success')
            else:
                logger.error(f"Failed to remove premium status for user {user_id}. API Response: {response.text}")
                flash('Failed to update your premium status. Please try again later.', 'error')
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error when canceling subscription for user {user_id}: {e}", exc_info=True)
            flash('Failed to cancel your Stripe subscription. Please contact support.', 'error')
            return redirect(url_for('views.user_settings'))
    else:
        logger.error(f"Invalid Stripe subscription ID for user {user_id}: {stripe_subscription_id}")
        flash('Invalid Stripe subscription ID. Please contact support.', 'error')
        return redirect(url_for('views.user_settings'))

    # Redirect the user to the dashboard
    return redirect(url_for('views.dashboard'))







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


