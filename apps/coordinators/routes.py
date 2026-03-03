import pytz
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from jinja2 import TemplateNotFound

from apps import get_db_connection
from apps.coordinators import blueprint

# --- Helpers ---

def get_kampala_time():
    """Returns current time in Africa/Kampala."""
    return datetime.now(pytz.timezone("Africa/Kampala"))

def get_segment(request):
    """Extracts the current page name from the request path for UI highlighting."""
    try:
        segment = request.path.split('/')[-1]
        return segment if segment != '' else 'manage_coordinators'
    except:
        return None

# --- Routes ---

@blueprint.route('/manage_coordinators')
def manage_coordinators():
    """Displays the departmental hierarchy and coordinator list."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 1. Aggregate Metrics
        cursor.execute('''
            SELECT 
                COUNT(CoordinatorID) as total_staff,
                SUM(CASE WHEN IsActive = TRUE THEN 1 ELSE 0 END) as active_staff,
                SUM(CASE WHEN Position = 'Senior Coordinator' THEN 1 ELSE 0 END) as senior_count
            FROM Coordinator
        ''')
        stats = cursor.fetchone()

        # 2. Fetch Coordinator List
        cursor.execute('SELECT * FROM Coordinator ORDER BY LastName ASC')
        coordinators = cursor.fetchall()

        # 3. Position Options (Matching SQL ENUM)
        positions = [
            'Department Head', 'Deputy Head', 'Senior Coordinator', 
            'Coordinator', 'Assistant Coordinator'
        ]

        return render_template(
            'coordinators/coordinator_list.html',
            stats=stats,
            coordinators=coordinators,
            positions=positions,
            segment='manage_coordinators'
        )
        
    except Exception as e:
        flash(f"Error loading staff data: {str(e)}", "danger")
        return redirect(url_for('home_blueprint.index'))
    finally:
        cursor.close()
        connection.close()

from flask import request, flash, redirect, url_for
from datetime import datetime

@blueprint.route('/add_coordinator', methods=['POST'])
def add_coordinator():
    """Registers a new staff member."""
    # 1. Capture and Clean Data
    # .strip() prevents leading/trailing spaces from breaking searches
    first_name = request.form.get('first_name', '').strip()
    last_name  = request.form.get('last_name', '').strip()
    phone      = request.form.get('phone', '').strip()
    position   = request.form.get('position')
    date_joined = request.form.get('date_joined')

    # Optional fields
    data = {
        'title':       request.form.get('title'),
        'first_name':  first_name,
        'last_name':   last_name,
        'phone':       phone,
        'alt_phone':   request.form.get('alt_phone', '').strip() or None,
        'email':       request.form.get('email', '').strip().lower() or None, # Store email in lowercase
        'position':    position,
        'date_joined': date_joined,
        'notes':       request.form.get('notes', '').strip() or None
    }

    # 2. Validation
    required_fields = ['first_name', 'last_name', 'phone', 'position', 'date_joined']
    if not all(data[field] for field in required_fields):
        flash("Registration failed: Missing required fields marked with (*).", "warning")
        return redirect(url_for('coordinators_blueprint.manage_coordinators'))

    # 3. Database Operation
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = '''
                INSERT INTO Coordinator 
                    (Title, FirstName, LastName, PhoneNumber, AlternativePhone, Email, Position, DateJoined, Notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(sql, (
                data['title'], data['first_name'], data['last_name'], data['phone'],
                data['alt_phone'], data['email'], data['position'], data['date_joined'], data['notes']
            ))
        
        connection.commit()
        flash(f"Success! {data['first_name']} {data['last_name']} added to the registry.", "success")
        
    except Exception as e:
        connection.rollback()
        # Log the error here for the developer, show a clean message to the user
        print(f"Error occurred: {e}") 
        flash("A database error occurred. Please ensure the email is unique.", "danger")
        
    finally:
        connection.close()

    return redirect(url_for('coordinators_blueprint.manage_coordinators'))





    

@blueprint.route('/edit_coordinator/<int:coord_id>', methods=['POST'])
def edit_coordinator(coord_id):
    """Updates existing coordinator details."""
    # Capture and sanitize active status
    is_active = True if request.form.get('is_active') in ['True', '1', 'on'] else False

    update_values = (
        request.form.get('title'),
        request.form.get('first_name'),
        request.form.get('last_name'),
        request.form.get('phone'),
        request.form.get('email'),
        request.form.get('position'),
        is_active,
        coord_id
    )

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute('''
            UPDATE Coordinator 
            SET Title = %s, FirstName = %s, LastName = %s, 
                PhoneNumber = %s, Email = %s, Position = %s, IsActive = %s
            WHERE CoordinatorID = %s
        ''', update_values)
        connection.commit()
        flash("Staff profile updated successfully.", "info")
    except Exception as e:
        connection.rollback()
        flash(f"Update failed: {str(e)}", "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('coordinators_blueprint.manage_coordinators'))


@blueprint.route('/delete_coordinator/<int:coord_id>', methods=['POST'])
def delete_coordinator(coord_id):
    """Removes a coordinator record if no dependencies exist."""
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute('DELETE FROM Coordinator WHERE CoordinatorID = %s', (coord_id,))
        connection.commit()
        
        if cursor.rowcount > 0:
            flash("Staff member removed from system.", "success")
        else:
            flash("Record not found.", "warning")
            
    except Exception as e:
        connection.rollback()
        # This catch handles the MySQL 'ON DELETE RESTRICT' trigger
        flash("Cannot delete: This coordinator is still linked to active churches.", "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('coordinators_blueprint.manage_coordinators'))


# --- Generic Routing ---

@blueprint.route('/<template>')
def route_template(template):
    """Dynamic routing for coordinator templates."""
    try:
        if not template.endswith('.html'):
            template += '.html'

        segment = get_segment(request)
        return render_template(f"coordinators/{template}", segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    except Exception:
        return render_template('home/page-500.html'), 500