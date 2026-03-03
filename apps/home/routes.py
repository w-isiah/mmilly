from apps.home import blueprint
from flask import render_template, request, session, flash, redirect, url_for
from flask_login import login_required, current_user
from jinja2 import TemplateNotFound
from apps import get_db_connection
import logging

from flask import render_template, redirect, url_for, flash
from apps import get_db_connection
from datetime import datetime
import pytz

def get_kampala_time():
    """Returns current time in Africa/Kampala."""
    return datetime.now(pytz.timezone("Africa/Kampala"))






@blueprint.route('/index')
def index():
    if 'id' not in session:
        flash('Login required to access this page.', 'error')
        return redirect(url_for('authentication_blueprint.login'))

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor(dictionary=True) as cursor:
            # 1. Verify User
            cursor.execute("SELECT * FROM users WHERE id = %s", (session['id'],))
            user = cursor.fetchone()

            if not user: 
                flash('User not found. Please log in again.', 'error')
                return redirect(url_for('authentication_blueprint.login'))

            # 2. Fetch Core Statistics Only
            cursor.execute("SELECT COUNT(*) as count FROM PWD")
            pwd_count = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM Coordinator")
            coordinator_count = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM Church")
            parish_count = cursor.fetchone()['count']

            # 3. Role-Based Rendering
            main_dashboard_roles = [
                'admin', 'director', 'super_admin', 'Head_ICT', 
                'dos', 'co_ordinator', 'department_head'
            ]

            if user['role'] in main_dashboard_roles:
                return render_template('home/sa_index.html', 
                                     segment='index',
                                     pwd_count=pwd_count,
                                     coordinator_count=coordinator_count,
                                     parish_count=parish_count,
                                     current_time=get_kampala_time())
            
            return render_template('home/other_user_index.html', segment='index', pwd_count=pwd_count)

    except Exception as e:
        print(f"[{get_kampala_time()}] Dashboard Error: {e}")
        flash("A dashboard error occurred.", 'danger')
        return redirect(url_for('authentication_blueprint.login'))
    finally:
        if connection:
            connection.close()









@blueprint.route('/<template>')
def route_template(template):
    """
    Renders dynamic templates from the 'home' folder.
    """
    try:
        if not template.endswith('.html'):
            template += '.html'
        
        segment = get_segment(request)
        return render_template("home/" + template, segment=segment)

    except TemplateNotFound:
        logging.error(f"Template {template} not found")
        return render_template('home/page-404.html', segment=segment), 404

    except Exception as e:
        logging.error(f"Error rendering template {template}: {str(e)}")
        return render_template('home/page-500.html', segment=segment), 500

def get_segment(request):
    """
    Extracts the last part of the URL path to identify the current page.
    """
    segment = request.path.strip('/').split('/')[-1]
    if not segment:
        segment = 'index'
    return segment
