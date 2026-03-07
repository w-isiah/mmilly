from datetime import datetime, timezone, timedelta
from flask import render_template, request, redirect, url_for, flash,session
from jinja2 import TemplateNotFound
from apps.utils.decorators import login_required  # Adjust path as needed
from apps import get_db_connection
from apps.coordinators import blueprint

# --- Helpers ---

def get_kampala_time():
    """Returns current date in East Africa Time (UTC+3) without pytz."""
    # EAT is UTC+3
    eat_offset = timezone(timedelta(hours=3))
    return datetime.now(eat_offset).date()

def get_segment(request):
    """Extracts the current page name for UI highlighting."""
    try:
        segment = request.path.split('/')[-1]
        return segment if segment != '' else 'manage_coordinators'
    except Exception:
        return None



@blueprint.route('/manage_coordinators')
@login_required
def manage_coordinators():
    """Displays metrics, coordinator list, and support data for assignments."""
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # 1. Aggregate Metrics
                cursor.execute('''
                    SELECT 
                        COUNT(CoordinatorID) as total_staff,
                        SUM(CASE WHEN IsActive = 1 THEN 1 ELSE 0 END) as active_staff
                    FROM coordinator
                ''')
                stats = cursor.fetchone()

                # 2. Fetch Coordinators with exclusive Church OR Parish names
                cursor.execute('''
                    SELECT coord.*, ch.church_name, p.name as parish_name 
                    FROM coordinator coord
                    LEFT JOIN church ch ON coord.church_id = ch.id
                    LEFT JOIN parishes p ON coord.parish_id = p.id
                    ORDER BY coord.FirstName ASC
                ''')
                coordinators = cursor.fetchall()

                # 3. Fetch Active Support Data for the Assignment Modals
                cursor.execute('SELECT id, church_name FROM church WHERE is_active = 1 ORDER BY church_name')
                churches = cursor.fetchall()
                
                cursor.execute('SELECT id, name FROM parishes WHERE is_active = 1 ORDER BY name')
                parishes = cursor.fetchall()

        positions = ['Coordinator', 'Assistant Coordinator']

        return render_template(
            'coordinators/coordinator_list.html',
            stats=stats,
            coordinators=coordinators,
            churches=churches,
            parishes=parishes,
            positions=positions,
            segment='manage_coordinators'
        )
        
    except Exception as e:
        flash(f"Error loading coordinator data: {str(e)}", "danger")
        return redirect(url_for('home_blueprint.index'))


@blueprint.route('/assign_coordinator/<int:coord_id>', methods=['POST'])
@login_required
def assign_coordinator(coord_id):
    """Exclusively assigns a coordinator to exactly ONE location or removes it."""
    
    # Security: Only Super Admins should manage assignments
    if session.get('role') != 'super_admin':
        flash("Unauthorized: Only Admins can change assignments.", "danger")
        return redirect(url_for('coordinators_blueprint.manage_coordinators'))

    # Get data from the toggle-based form
    assignment_type = request.form.get('assignment_type') # 'none', 'parish', or 'church'
    assigned_id = request.form.get('assigned_id')
    
    # Initialize both as None (This handles the 'unassign' case)
    parish_id = None
    church_id = None

    # Apply the exclusive assignment logic
    if assignment_type == 'parish' and assigned_id:
        parish_id = assigned_id
    elif assignment_type == 'church' and assigned_id:
        church_id = assigned_id
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Update the record. If type was 'none', both columns become NULL.
                cursor.execute('''
                    UPDATE coordinator 
                    SET parish_id = %s, church_id = %s 
                    WHERE CoordinatorID = %s
                ''', (parish_id, church_id, coord_id))
            conn.commit()
            
            # Contextual feedback for the user
            if not parish_id and not church_id:
                flash("Coordinator has been unassigned from all locations.", "info")
            else:
                flash(f"Coordinator successfully assigned to {assignment_type}.", "success")
                
    except Exception as e:
        flash(f"Database Error: {str(e)}", "danger")
    
    return redirect(url_for('coordinators_blueprint.manage_coordinators'))


@blueprint.route('/add_coordinator', methods=['POST'])
def add_coordinator():
    """Registers a new coordinator (Church and Parish IDs removed from insert)."""
    form = request.form
    
    # Required fields (removed church_id and parish_id requirements)
    required = ['FirstName', 'LastName', 'PhoneNumber']
    if not all(form.get(field) for field in required):
        flash("Registration failed: Missing required fields.", "warning")
        return redirect(url_for('coordinators_blueprint.manage_coordinators'))

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                # Removed church_id and parish_id from column list and values
                sql = '''
                    INSERT INTO coordinator 
                        (FirstName, LastName, Title, PhoneNumber, AlternativePhone, 
                         Email, Position, DateJoined, IsActive, Notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
                '''
                cursor.execute(sql, (
                    form.get('FirstName').strip(),
                    form.get('LastName').strip(),
                    form.get('Title'),
                    form.get('PhoneNumber').strip(),
                    form.get('AlternativePhone', '').strip() or None,
                    form.get('Email', '').strip().lower() or None,
                    form.get('Position'),
                    get_kampala_time(),
                    form.get('Notes', '').strip() or None
                ))
            connection.commit()
            flash("Coordinator successfully added to the registry!", "success")
            
    except Exception as e:
        flash(f"Database error: {str(e)}", "danger")
        
    return redirect(url_for('coordinators_blueprint.manage_coordinators'))


@blueprint.route('/edit_coordinator/<int:coord_id>', methods=['POST'])
def edit_coordinator(coord_id):
    """Updates existing coordinator (Church and Parish IDs removed from update)."""
    form = request.form
    is_active = 1 if form.get('IsActive') in ['True', '1', 'on'] else 0

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                # Removed church_id and parish_id from the SET clause
                sql = '''
                    UPDATE coordinator 
                    SET FirstName = %s, LastName = %s, Title = %s, 
                        PhoneNumber = %s, AlternativePhone = %s, Email = %s, 
                        Position = %s, IsActive = %s, Notes = %s
                    WHERE CoordinatorID = %s
                '''
                cursor.execute(sql, (
                    form.get('FirstName'), 
                    form.get('LastName'), 
                    form.get('Title'),
                    form.get('PhoneNumber'), 
                    form.get('AlternativePhone'),
                    form.get('Email', '').strip().lower() or None, 
                    form.get('Position'),
                    is_active, 
                    form.get('Notes'), 
                    coord_id
                ))
            connection.commit()
            flash("Staff profile updated successfully.", "info")
    except Exception as e:
        flash(f"Update failed: {str(e)}", "danger")

    return redirect(url_for('coordinators_blueprint.manage_coordinators'))