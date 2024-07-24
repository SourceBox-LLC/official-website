from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import requests
import os

admin = Blueprint('admin', __name__, template_folder='templates')

API_URL = os.getenv('API_URL', 'http://localhost:5000')  # Use env variable for API URL

def get_headers():
    token = session.get('access_token')
    return {'Authorization': f'Bearer {token}'} if token else {}

@admin.route('/admin')
def admin_page():
    headers = get_headers()
    response = requests.get(f"{API_URL}/users", headers=headers)
    if response.status_code == 200:
        all_users = response.json()
        return render_template('admin.html', all_users=all_users)
    else:
        flash("Failed to load users", category='error')
        return redirect(url_for('auth.login'))

@admin.route('/admin/user_search', methods=['GET', 'POST'])
def user_search():
    headers = get_headers()
    all_users_response = requests.get(f"{API_URL}/users", headers=headers)
    if all_users_response.status_code != 200:
        flash("Failed to load users", category='error')
        return redirect(url_for('auth.login'))
    
    all_users = all_users_response.json()

    if request.method == 'POST':
        requested_user = request.form.get('username')
        requested_email = request.form.get('email')
        requested_id = request.form.get('user_id')

        if requested_user:
            user_response = requests.get(f"{API_URL}/users?username={requested_user}", headers=headers)
        elif requested_email:
            user_response = requests.get(f"{API_URL}/users?email={requested_email}", headers=headers)
        elif requested_id:
            user_response = requests.get(f"{API_URL}/users?id={requested_id}", headers=headers)
        else:
            user_response = None
        
        if user_response and user_response.status_code == 200:
            results = user_response.json()
            return render_template('admin.html', results=[results], all_users=all_users)
        else:
            flash('User not found', category='error')

    return render_template('admin.html', all_users=all_users)

@admin.route('/admin/delete_user', methods=['GET', 'POST'])
def delete_user():
    headers = get_headers()
    all_users_response = requests.get(f"{API_URL}/users", headers=headers)
    if all_users_response.status_code != 200:
        flash("Failed to load users", category='error')
        return redirect(url_for('auth.login'))
    
    all_users = all_users_response.json()

    if request.method == 'POST':
        user_id = request.form.get('user_id_delete')
        delete_response = requests.delete(f"{API_URL}/users/{user_id}", headers=headers)
        if delete_response.status_code == 200:
            flash('User deleted', category='success')
        else:
            flash('Failed to delete user', category='error')

    return render_template('admin.html', all_users=all_users)

@admin.route('/admin/reset_email', methods=['GET', 'POST'])
def reset_email():
    headers = get_headers()
    all_users_response = requests.get(f"{API_URL}/users", headers=headers)
    if all_users_response.status_code != 200:
        flash("Failed to load users", category='error')
        return redirect(url_for('auth.login'))
    
    all_users = all_users_response.json()

    if request.method == 'POST':
        user_id = request.form.get('user_id_email')
        new_email = request.form.get('new_email')
        response = requests.put(f"{API_URL}/users/{user_id}/email", json={'new_email': new_email}, headers=headers)
        if response.status_code == 200:
            flash("Email reset successful", category='success')
        else:
            flash("Failed to reset email", category='error')

    return render_template('admin.html', all_users=all_users)

@admin.route('/admin/reset_password', methods=['GET', 'POST'])
def reset_password():
    headers = get_headers()
    all_users_response = requests.get(f"{API_URL}/users", headers=headers)
    if all_users_response.status_code != 200:
        flash("Failed to load users", category='error')
        return redirect(url_for('auth.login'))
    
    all_users = all_users_response.json()

    if request.method == 'POST':
        user_id = request.form.get('user_id_password')
        new_password = request.form.get('new_password')
        response = requests.put(f"{API_URL}/users/{user_id}/password", json={'new_password': new_password}, headers=headers)
        if response.status_code == 200:
            flash("Password reset successful", category='success')
        else:
            flash("Failed to reset password", category='error')

    return render_template('admin.html', all_users=all_users)

@admin.route('/admin/platform_update', methods=['GET', 'POST'])
def platform_update():
    headers = get_headers()
    all_users_response = requests.get(f"{API_URL}/users", headers=headers)
    if all_users_response.status_code != 200:
        flash("Failed to load users", category='error')
        return redirect(url_for('auth.login'))
    
    all_users = all_users_response.json()

    if request.method == 'POST':
        update_title = request.form.get('update_title')
        update_content = request.form.get('message')
        if update_title and update_content:
            response = requests.post(f"{API_URL}/platform_updates", json={'title': update_title, 'content': update_content}, headers=headers)
            if response.status_code == 201:
                flash("Platform update added", category='success')
            else:
                flash("Failed to add platform update", category='error')
    
    return render_template('admin.html', all_users=all_users)

@admin.route('/admin/user_history', methods=['GET', 'POST'])
def user_history():
    headers = get_headers()
    all_users_response = requests.get(f"{API_URL}/users", headers=headers)
    if all_users_response.status_code != 200:
        flash("Failed to load users", category='error')
        return redirect(url_for('auth.login'))
    
    all_users = all_users_response.json()

    if request.method == 'POST':
        user_id = request.form.get("view_user_history")
        response = requests.get(f"{API_URL}/users/{user_id}/history", headers=headers)
        if response.status_code == 200:
            history = response.json()
            return render_template('admin.html', all_users=all_users, history=history)
        else:
            flash("Failed to retrieve user history", category='error')

    return render_template('admin.html', all_users=all_users)

@admin.route('/admin/logout', methods=['GET', 'POST'])
def logout():
    session.pop('access_token', None)
    return redirect(url_for('auth.login'))
