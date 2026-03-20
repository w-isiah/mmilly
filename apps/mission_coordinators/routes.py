from datetime import datetime, timezone, timedelta
from flask import render_template, request, redirect, url_for, flash, session
from apps.utils.decorators import login_required
from apps import get_db_connection
from apps.mission_coordinators import blueprint

# --- Configuration & Constants ---
POSITION_OPTIONS = ['Coordinator', 'Assistant Coordinator']

# --- Helpers ---

def get_kampala_time():
    """Returns current date/time in East Africa Time (UTC+3)."""
    eat_offset = timezone(timedelta(hours=3))
    return datetime.now(eat_offset)

def clean_form_data(form_dict):
    """Trims whitespace and handles empty strings as None for the DB."""
    return {k: (v.strip() if v and isinstance(v, str) else v) for k, v in form_dict.items()}

# --- Routes ---
@blueprint.route('/manage_mission_coordinators')
@login_required
def manage_mission_coordinators():
    """Main dashboard for Mission Coordinators."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                
                # 1. Fetch Detailed List with Station Info
                # This stays because it populates your main table
                cursor.execute('''
                    SELECT 
                        mc.*, 
                        ch.church_name, 
                        p.name AS parish_name 
                    FROM mission_coordinator mc
                    LEFT JOIN church ch ON mc.church_id = ch.id
                    LEFT JOIN parishes p ON mc.parish_id = p.id
                    ORDER BY mc.IsActive DESC, mc.LastName ASC
                ''')
                coordinators = cursor.fetchall()

                # 2. Fetch Dropdown Data for the Modals
                cursor.execute('SELECT id, church_name FROM church WHERE is_active = 1 ORDER BY church_name')
                churches = cursor.fetchall()
                
                cursor.execute('SELECT id, name FROM parishes WHERE is_active = 1 ORDER BY name')
                parishes = cursor.fetchall()

        return render_template(
            'mission_Coordinators/mission_coodinators_list.html',
            coordinators=coordinators,
            churches=churches,
            parishes=parishes,
            positions=POSITION_OPTIONS,
            segment='manage_mission',
            current_date=get_kampala_time().date()
        )
    except Exception as e:
        # Logging the error is helpful for debugging later
        print(f"Error in manage_mission_coordinators: {e}")
        flash("System Error: Could not load coordinator registry.", "danger")
        return redirect(url_for('home_blueprint.index'))


@blueprint.route('/add_mission_coordinator', methods=['POST'])
@login_required
def add_mission_coordinator():
    """Registers a new coordinator."""
    data = clean_form_data(request.form)
    
    if not all([data.get('FirstName'), data.get('LastName'), data.get('PhoneNumber')]):
        flash("Required fields: Names and Primary Phone.", "warning")
        return redirect(url_for('mission_coordinators_blueprint.manage_mission_coordinators'))

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                sql = '''
                    INSERT INTO mission_coordinator 
                    (FirstName, LastName, Title, PhoneNumber, AlternativePhone, 
                     Email, Position, DateJoined, IsActive, Notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                '''
                params = (
                    data.get('FirstName'), data.get('LastName'), data.get('Title'),
                    data.get('PhoneNumber'), data.get('AlternativePhone'),
                    data.get('Email').lower() if data.get('Email') else None,
                    data.get('Position'),
                    data.get('DateJoined') or get_kampala_time().date(),
                    1, data.get('Notes')
                )
                cursor.execute(sql, params)
            conn.commit()
            flash(f"Coordinator {data['FirstName']} added successfully.", "success")
    except Exception as e:
        flash(f"Database Error: {str(e)}", "danger")
        
    return redirect(url_for('mission_coordinators_blueprint.manage_mission_coordinators'))


@blueprint.route('/edit_mission_coordinator/<int:coord_id>', methods=['POST'])
@login_required
def edit_mission_coordinator(coord_id):
    """Updates profile details. This matches the URL your template is calling."""
    data = clean_form_data(request.form)
    # Checkbox logic: if present in request.form, it's active
    is_active = 1 if request.form.get('IsActive') else 0

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                sql = '''
                    UPDATE mission_coordinator 
                    SET FirstName = %s, LastName = %s, Title = %s, 
                        PhoneNumber = %s, Email = %s, Position = %s, 
                        IsActive = %s, Notes = %s
                    WHERE CoordinatorID = %s
                '''
                params = (
                    data.get('FirstName'), data.get('LastName'), data.get('Title'),
                    data.get('PhoneNumber'), data.get('Email'), data.get('Position'),
                    is_active, data.get('Notes'), coord_id
                )
                cursor.execute(sql, params)
            conn.commit()
            flash("Profile updated successfully.", "info")
    except Exception as e:
        flash(f"Update failed: {str(e)}", "danger")

    return redirect(url_for('mission_coordinators_blueprint.manage_mission_coordinators'))


@blueprint.route('/assign_mission_coordinator/<int:coord_id>', methods=['POST'])
@login_required
def assign_mission_coordinator(coord_id):
    """Handles Parish/Church assignments."""
    if session.get('role') != 'super_admin':
        flash("Access Denied: Super Admin only.", "danger")
        return redirect(url_for('mission_coordinators_blueprint.manage_mission_coordinators'))

    assignment_type = request.form.get('assignment_type') 
    raw_id = request.form.get('assigned_id')
    
    # Securely handle ID conversion
    assigned_id = int(raw_id) if raw_id and str(raw_id).isdigit() else None
    
    p_id = assigned_id if assignment_type == 'parish' else None
    c_id = assigned_id if assignment_type == 'church' else None
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE mission_coordinator 
                    SET parish_id = %s, church_id = %s 
                    WHERE CoordinatorID = %s
                ''', (p_id, c_id, coord_id))
            conn.commit()
            flash("Station assignment updated.", "success")
    except Exception as e:
        flash(f"Assignment failed: {str(e)}", "danger")
    
    return redirect(url_for('mission_coordinators_blueprint.manage_mission_coordinators'))


@blueprint.route('/delete_mission_coordinator/<int:coord_id>', methods=['POST'])
@login_required
def delete_mission_coordinator(coord_id):
    """Permanently deletes a record."""
    if session.get('role') != 'super_admin':
        flash("Action Restricted.", "danger")
        return redirect(url_for('mission_coordinators_blueprint.manage_mission_coordinators'))

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM mission_coordinator WHERE CoordinatorID = %s", (coord_id,))
            conn.commit()
            flash("Coordinator removed from registry.", "warning")
    except Exception as e:
        flash(f"Error deleting record: {str(e)}", "danger")

    return redirect(url_for('mission_coordinators_blueprint.manage_mission_coordinators'))