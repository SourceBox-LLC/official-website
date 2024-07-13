from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import safe_join
from .. import db
from website.models import User, UserHistory



service = Blueprint('service', __name__, template_folder='templates')


def record_user_history(action):
     #record user history
    history = UserHistory(user_id=current_user.id, action=action)
    db.session.add(history)
    db.session.commit()



@service.route('/service/wikidoc')
@login_required
def wikidoc():
    record_user_history("entered wikidoc")

    return render_template('wikidoc.html')


@service.route('/service/codedoc')
@login_required
def codedoc():
    record_user_history("entered codedoc")

    return render_template('codedoc.html')


@service.route('/service/source-lightning')
@login_required
def source_lightning():
    record_user_history("entered source-lightning")

    return render_template('source_lightning.html')



@service.route('/service/pack-man')
@login_required
def pack_man():
    record_user_history("entered pack-man")
    
    return render_template('pack_man.html')


@service.route('/service/source-mail')
@login_required
def source_mail():
    record_user_history("entered source-mail")

    return render_template('source_mail.html')