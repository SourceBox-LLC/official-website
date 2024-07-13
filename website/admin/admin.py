from flask import Blueprint, render_template, request, redirect, url_for, flash;
from flask_login import login_required
from website.models import User
from website.models import PlatformUpdates
from .. import db


admin = Blueprint('admin', __name__, template_folder='templates')

@admin.route('/admin')
def admin_page():
    all_users = User.query.all()
    return render_template('admin.html', all_users=all_users)




@admin.route('/admin/user_search', methods=['GET', 'POST'])
def user_search():
    all_users = User.query.all()
    if request.method == 'POST':
        requested_user = request.form.get('username')
        requested_email = request.form.get('email')
        requested_id = request.form.get('user_id')

        user_results = User.query.filter_by(username=requested_user).first()
        email_results = User.query.filter_by(email=requested_email).first()
        id_results = User.query.filter_by(id=requested_id).first()

        if user_results:
            return render_template('admin.html', results=[user_results], all_users=all_users)
        elif email_results:
            return render_template('admin.html', results=[email_results], all_users=all_users)
        elif id_results:
            return render_template('admin.html', results=[id_results], all_users=all_users)
        else:
            flash('User not found', category='error')
        
    return render_template('admin.html', all_users=all_users)


#deletes user from database
@admin.route('/admin/delete_user', methods=['GET', 'POST'])
def delete_user():
    all_users = User.query.all()
    if request.method == 'POST':
        del_user = request.form.get('user_id_delete')
        del_user = User.query.filter_by(id=del_user).first()
        if del_user:
            db.session.delete(del_user)
            db.session.commit()
            flash('User deleted', category='success')
        
    return render_template('admin.html', all_users=all_users,)




@admin.route('/admin/reset_email', methods=['GET', 'POST'])
def reset_email():
    all_users = User.query.all()
    if request.method == 'POST':
        reset_email = request.form.get('user_id_email')
        reset_email = User.query.filter_by(id=reset_email).first()
        #TODO: reset email
        if reset_email:
            print("reset email success!")#!debug
        else:
            print("reset email failed!")#!debug
        
    return render_template('admin.html', all_users=all_users,)




@admin.route('/admin/reset_password', methods=['GET', 'POST'])
def reset_password():
    all_users = User.query.all()
    if request.method == 'POST':
        reset_password = request.form.get('user_id_password')
        reset_password = User.query.filter_by(id=reset_password).first()
        #TODO: reset password
        if reset_password:
            print("reset email success!")#!debug
        else:
            print("reset email failed!")#!debug
        
    return render_template('admin.html', all_users=all_users,)



@admin.route('/admin/platform_update', methods=['GET', 'POST'])
def platform_update():
    all_users = User.query.all()
    if request.method == 'POST':
        update_title = request.form.get('update_title')
        update_content = request.form.get('message')
        if update_title and update_content:
            #add update to database
            add_update = PlatformUpdates(title=update_title, content=update_content)
            db.session.add(add_update)
            db.session.commit()

            print("update platform success!")#!debug
            print(f"platform update title: {update_title}")#!debug
            print(f"Platform update: {update_content}")#!debug
            show_preview = True
            return render_template('admin.html', all_users=all_users, show_preview=show_preview, update_content=update_content, update_title=update_title)

        else:
            show_preview = False
            print("update platform failed!")#!debug
    
    return render_template('admin.html', all_users=all_users)



@admin.route('/admin/push_update', methods=['GET', 'POST'])
def push_update():
    return redirect(url_for('views.updates'))
    

@admin.route('/admin/user_history', methods=['GET', 'POST'])
def user_history():
    all_users = User.query.all()
    if request.method == 'POST':
        user_id = request.form.get("view_user_history")
        user = User.query.filter_by(id=user_id).first()
        if user:
            history_list = []
            for history in user.history:
                history_list.append(f"Action: {history.action}, Timestamp: {history.timestamp}")
            history = history_list

            return render_template('admin.html', all_users=all_users, history=history)
    return render_template('admin.html', all_users=all_users)





@admin.route('/admin/logout', methods=['GET', 'POST'])
def logout():
    return redirect(url_for('auth.login'))