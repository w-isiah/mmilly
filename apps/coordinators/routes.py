import pytz
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from jinja2 import TemplateNotFound

from apps import get_db_connection
from apps.coordinators import blueprint

# --- Helpers ---

def get_kampala_time():
    """Returns current date in Africa/Kampala timezone."""
    return datetime.now(pytz.timezone("Africa/Kampala")).date()

def get_segment(request):
    """Extracts the current page name for UI highlighting."""
    try:
        segment = request.path.split('/')[-1]
        return segment if segment != '' else 'manage_coordinators'
    except Exception:
        return None

# --- Routes ---

@blueprint.route('/manage_coordinators')
def manage_coordinators():
    """Displays metrics, coordinator list, and church dropdown data."""
    try:
        # Using a single context manager for all initial data fetching
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # 1. Aggregate Metrics
                cursor.execute('''
                    SELECT 
                        COUNT(CoordinatorID) as total_staff,
                        SUM(CASE WHEN IsActive = 1 THEN 1 ELSE 0 END) as active_staff,
                        SUM(CASE WHEN Position = 'Senior Coordinator' THEN 1 ELSE 0 END) as senior_count
                    FROM coordinator
                ''')
                stats = cursor.fetchone()

                # 2. Fetch Coordinator List
                cursor.execute('SELECT * FROM coordinator ORDER BY LastName ASC')
                coordinators = cursor.fetchall()

                # 3. Fetch Church List for Modals (using your 'church' table schema)
                cursor.execute('SELECT id, church_name FROM church WHERE is_active = 1 ORDER BY church_name ASC')
                churches = cursor.fetchall()

        # Position Options (Matching MariaDB ENUM)
        positions = [
            'Department Head', 'Deputy Head', 'Senior Coordinator', 
            'Coordinator', 'Assistant Coordinator'
        ]

        return render_template(
            'coordinators/coordinator_list.html',
            stats=stats,
            coordinators=coordinators,
            churches=churches,  # Now correctly passed to template
            positions=positions,
            segment='manage_coordinators'
        )
        
    except Exception as e:
        flash(f"Error loading staff data: {str(e)}", "danger")
        return redirect(url_for('home_blueprint.index'))


@blueprint.route('/add_coordinator', methods=['POST'])
def add_coordinator():
    """Registers a new staff member with automatic Kampala date."""
    form = request.form
    first_name = form.get('first_name', '').strip()
    last_name  = form.get('last_name', '').strip()
    phone      = form.get('phone', '').strip()
    position   = form.get('position')
    
    if not all([first_name, last_name, phone, position]):
        flash("Registration failed: Required fields (*) cannot be empty.", "warning")
        return redirect(url_for('coordinators_blueprint.manage_coordinators'))

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                sql = '''
                    INSERT INTO coordinator 
                        (Title, FirstName, LastName, PhoneNumber, AlternativePhone, Email, Position, DateJoined, IsActive)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
                '''
                cursor.execute(sql, (
                    form.get('title'),
                    first_name,
                    last_name,
                    phone,
                    form.get('alt_phone', '').strip() or None,
                    form.get('email', '').strip().lower() or None,
                    position,
                    get_kampala_time(),
                ))
            connection.commit()
            flash(f"Success! {first_name} {last_name} has been registered.", "success")
            
    except Exception as e:
        flash(f"Database error: {str(e)}", "danger")
        
    return redirect(url_for('coordinators_blueprint.manage_coordinators'))


@blueprint.route('/edit_coordinator/<int:coord_id>', methods=['POST'])
def edit_coordinator(coord_id):
    """Updates existing coordinator details."""
    is_active = 1 if request.form.get('is_active') in ['True', '1', 'on'] else 0

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                sql = '''
                    UPDATE coordinator 
                    SET Title = %s, FirstName = %s, LastName = %s, 
                        PhoneNumber = %s, Email = %s, Position = %s, IsActive = %s
                    WHERE CoordinatorID = %s
                '''
                cursor.execute(sql, (
                    request.form.get('title'),
                    request.form.get('first_name'),
                    request.form.get('last_name'),
                    request.form.get('phone'),
                    request.form.get('email'),
                    request.form.get('position'),
                    is_active,
                    coord_id
                ))
            connection.commit()
            flash("Staff profile updated successfully.", "info")
    except Exception as e:
        flash(f"Update failed: {str(e)}", "danger")

    return redirect(url_for('coordinators_blueprint.manage_coordinators'))


@blueprint.route('/delete_coordinator/<int:coord_id>', methods=['POST'])
def delete_coordinator(coord_id):
    """Removes a coordinator record."""
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM coordinator WHERE CoordinatorID = %s', (coord_id,))
                if cursor.rowcount > 0:
                    connection.commit()
                    flash("Staff member removed from system.", "success")
                else:
                    flash("Record not found.", "warning")
    except Exception:
        flash("Action Denied: This coordinator is currently linked to active records.", "danger")

    return redirect(url_for('coordinators_blueprint.manage_coordinators'))

# --- Generic Routing ---

@blueprint.route('/<template>')
def route_template(template):
    try:
        if not template.endswith('.html'):
            template += '.html'
        segment = get_segment(request)
        return render_template(f"coordinators/{template}", segment=segment)
    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    except Exception:
        return render_template('home/page-500.html'), 500