import logging
import pytz
from datetime import datetime
from flask import render_template, request, session, flash, redirect, url_for
from jinja2 import TemplateNotFound

from apps import get_db_connection
from apps.home import blueprint

# --- Helper Functions ---

def get_kampala_time():
    """Returns current time in Africa/Kampala timezone."""
    return datetime.now(pytz.timezone("Africa/Kampala"))

def get_segment(request):
    """Extracts the current page segment for UI active-state tracking."""
    segment = request.path.strip('/').split('/')[-1]
    return segment if segment else 'index'

# --- Routes ---

@blueprint.route('/index')
def index():
    """Main Dashboard: Fetches registry counts and renders role-based views."""
    if 'id' not in session:
        flash('Login required to access this page.', 'error')
        return redirect(url_for('authentication_blueprint.login'))

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor(dictionary=True) as cursor:
            # 1. Verify User and Role
            cursor.execute("SELECT * FROM users WHERE id = %s", (session['id'],))
            user = cursor.fetchone()

            if not user: 
                flash('User not found. Please log in again.', 'error')
                return redirect(url_for('authentication_blueprint.login'))

            # 2. Fetch Registry Statistics
            # Count PWD beneficiaries
            cursor.execute("SELECT COUNT(*) as count FROM pwd")
            pwd_count = cursor.fetchone()['count']

            # Count Ministry Coordinators
            cursor.execute("SELECT COUNT(*) as count FROM Coordinator")
            coordinator_count = cursor.fetchone()['count']

            # Count Parishes/Churches
            cursor.execute("SELECT COUNT(*) as count FROM church")
            parish_count = cursor.fetchone()['count']

            # 3. Define Management Roles
            main_dashboard_roles = [
                'admin', 'director', 'super_admin', 'Head_ICT', 
                'dos', 'co_ordinator', 'department_head'
            ]

            # 4. Role-Based Routing
            if user['role'] in main_dashboard_roles:
                return render_template(
                    'home/sa_index.html', 
                    segment='index',
                    pwd_count=pwd_count,
                    coordinator_count=coordinator_count,
                    parish_count=parish_count,
                    current_time=get_kampala_time()
                )
            
            # Fallback for non-management roles (e.g., applicants or view-only users)
            return render_template(
                'home/other_user_index.html', 
                segment='index', 
                pwd_count=pwd_count
            )

    except Exception as e:
        logging.error(f"[{get_kampala_time()}] Dashboard Error: {str(e)}")
        flash("An error occurred while loading the dashboard.", 'danger')
        return redirect(url_for('authentication_blueprint.login'))
    
    finally:
        if connection:
            connection.close()

@blueprint.route('/<template>')
def route_template(template):
    """Renders dynamic templates from the 'home' directory."""
    segment = get_segment(request)
    
    try:
        if not template.endswith('.html'):
            template += '.html'
        
        return render_template(f"home/{template}", segment=segment)

    except TemplateNotFound:
        logging.warning(f"404 Error: Template 'home/{template}' not found.")
        return render_template('home/page-404.html', segment=segment), 404

    except Exception as e:
        logging.error(f"500 Error rendering 'home/{template}': {str(e)}")
        return render_template('home/page-500.html', segment=segment), 500