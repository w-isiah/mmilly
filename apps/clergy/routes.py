import pytz
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from jinja2 import TemplateNotFound

from apps import get_db_connection
from apps.clergy import blueprint

# --- Helpers ---

def get_kampala_time():
    """Returns current time in Africa/Kampala."""
    return datetime.now(pytz.timezone("Africa/Kampala"))

def get_segment(request):
    """Extracts the current page name for UI highlighting."""
    try:
        segment = request.path.split('/')[-1]
        return segment if segment != '' else 'manage_clergy'
    except Exception:
        return None

# --- Routes ---

@blueprint.route('/manage_clergy')
def manage_clergy():
    """Displays the clergy list joined with the churches table."""
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # Joined with 'churches' table as per your schema
                cursor.execute('''
                    SELECT c.*, ch.church_name 
                    FROM clergy c
                    LEFT JOIN church ch ON c.church_id = ch.id
                    ORDER BY c.last_name ASC, c.first_name ASC
                ''')
                clergy_list = cursor.fetchall()

                # Fetching active churches for dropdown menus
                cursor.execute('SELECT id, church_name FROM church ORDER BY church_name ASC')
                churches = cursor.fetchall()

        return render_template(
            'clergy/clergy_list.html',
            clergy_list=clergy_list,
            churches=churches,
            segment='manage_clergy'
        )
    except Exception as e:
        flash(f"Database Error: {str(e)}", "danger")
        return redirect(url_for('home_blueprint.index'))

@blueprint.route('/add_clergy', methods=['POST'])
def add_clergy():
    """Handles insertion into the clergy table."""
    form = request.form
    try:
        # Handle empty church_id for Foreign Key compatibility
        church_id = form.get('church_id') if form.get('church_id') else None
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                sql = """INSERT INTO clergy (church_id, title, first_name, last_name, 
                                            other_names, gender, phone_number, email, is_active) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)"""
                
                cur.execute(sql, (
                    church_id, 
                    form.get('title'), 
                    form.get('first_name'), 
                    form.get('last_name'),
                    form.get('other_names'), 
                    form.get('gender'), 
                    form.get('phone_number'),
                    form.get('email')
                ))
            conn.commit()
            flash("Clergy member registered successfully.", "success")
    except Exception as e:
        flash(f"Registration failed: {str(e)}", "danger")
    return redirect(url_for('clergy_blueprint.manage_clergy'))

@blueprint.route('/edit_clergy/<int:id>', methods=['POST'])
def edit_clergy(id):
    """Handles updates for a specific clergy record."""
    form = request.form
    is_active = 1 if form.get('is_active') else 0
    church_id = form.get('church_id') if form.get('church_id') else None
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                sql = """UPDATE clergy SET 
                            church_id=%s, title=%s, first_name=%s, last_name=%s, 
                            other_names=%s, gender=%s, phone_number=%s, email=%s, 
                            is_active=%s 
                         WHERE id=%s"""
                
                cur.execute(sql, (
                    church_id, 
                    form.get('title'), 
                    form.get('first_name'), 
                    form.get('last_name'),
                    form.get('other_names'), 
                    form.get('gender'), 
                    form.get('phone_number'),
                    form.get('email'), 
                    is_active, 
                    id
                ))
            conn.commit()
            flash("Profile updated successfully.", "info")
    except Exception as e:
        flash(f"Update failed: {str(e)}", "danger")
    return redirect(url_for('clergy_blueprint.manage_clergy'))

@blueprint.route('/delete_clergy/<int:id>', methods=['POST'])
def delete_clergy(id):
    """Removes a record from the clergy table."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM clergy WHERE id = %s", (id,))
            conn.commit()
            flash("Record deleted successfully.", "success")
    except Exception as e:
        # Usually fails if there are linked records in other tables
        flash("Record cannot be deleted (linked to other data).", "danger")
    return redirect(url_for('clergy_blueprint.manage_clergy'))

# --- Generic Routing ---

@blueprint.route('/<template>')
def route_template(template):
    """Dynamic routing for clergy templates."""
    try:
        if not template.endswith('.html'):
            template += '.html'
        segment = get_segment(request)
        return render_template(f"clergy/{template}", segment=segment)
    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    except Exception:
        return render_template('home/page-500.html'), 500