import pytz
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from jinja2 import TemplateNotFound

from apps import get_db_connection
from apps.parishes import blueprint 

# --- Helpers ---

def get_kampala_time():
    """Returns current time in Africa/Kampala."""
    return datetime.now(pytz.timezone("Africa/Kampala"))

def get_segment(request):
    try:
        segment = request.path.split('/')[-1]
        return segment if segment != '' else 'manage_parishes'
    except:
        return None

# --- Routes ---

@blueprint.route('/manage_parishes')
def manage_parishes():
    """Displays Parishes joined with parent Archdeaconries."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 1. Aggregate Metrics
        cursor.execute('''
            SELECT 
                COUNT(id) as total_count,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_count
            FROM parishes
        ''')
        stats = cursor.fetchone()

        # 2. Fetch Archdeaconries (Needed for the Add/Edit dropdown menus)
        cursor.execute('SELECT id, name FROM archdeaconries WHERE is_active = 1 ORDER BY name ASC')
        archdeaconries = cursor.fetchall()

        # 3. Fetch Parishes with JOIN to get Archdeaconry Name
        cursor.execute('''
            SELECT p.*, a.name as archdeaconry_name 
            FROM parishes p
            INNER JOIN archdeaconries a ON p.archdeaconry_id = a.id
            ORDER BY p.name ASC
        ''')
        parishes = cursor.fetchall()

        return render_template(
            'parishes/parish_list.html',
            stats=stats,
            archdeaconries=archdeaconries,
            parishes=parishes,
            segment='manage_parishes'
        )
        
    except Exception as e:
        flash(f"Error loading parish data: {str(e)}", "danger")
        return redirect(url_for('home_blueprint.index'))
    finally:
        cursor.close()
        connection.close()


@blueprint.route('/add_parish', methods=['POST'])
def add_parish():
    """Registers a new Parish linked to an Archdeaconry."""
    archdeaconry_id = request.form.get('archdeaconry_id')
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name or not archdeaconry_id:
        flash("Registration failed: Name and Archdeaconry are required.", "warning")
        return redirect(url_for('parishes_blueprint.manage_parishes'))

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        # Matches your schema: archdeaconry_id, name, description, is_active (tinyint)
        sql = '''
            INSERT INTO parishes (archdeaconry_id, name, description, is_active) 
            VALUES (%s, %s, %s, 1)
        '''
        cursor.execute(sql, (archdeaconry_id, name, description))
        connection.commit()
        flash(f"Success! Parish '{name}' added to the registry.", "success")
        
    except Exception as e:
        connection.rollback()
        flash(f"Database error: {str(e)}", "danger")
    finally:
        connection.close()

    return redirect(url_for('parishes_blueprint.manage_parishes'))


@blueprint.route('/edit_parish/<int:parish_id>', methods=['POST'])
def edit_parish(parish_id):
    """Updates parish details including parent archdeaconry and status."""
    archdeaconry_id = request.form.get('archdeaconry_id')
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    # tinyint(4) logic
    is_active = 1 if request.form.get('is_active') in ['True', '1', 'on'] else 0

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute('''
            UPDATE parishes 
            SET archdeaconry_id = %s, name = %s, description = %s, is_active = %s
            WHERE id = %s
        ''', (archdeaconry_id, name, description, is_active, parish_id))
        connection.commit()
        flash("Parish updated successfully.", "info")
    except Exception as e:
        connection.rollback()
        flash(f"Update failed: {str(e)}", "danger")
    finally:
        connection.close()

    return redirect(url_for('parishes_blueprint.manage_parishes'))


@blueprint.route('/delete_parish/<int:parish_id>', methods=['POST'])
def delete_parish(parish_id):
    """Removes a parish record."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute('DELETE FROM parishes WHERE id = %s', (parish_id,))
        connection.commit()
        flash("Parish removed from system.", "success")
    except Exception as e:
        connection.rollback()
        flash("Cannot delete: This parish is linked to active member records.", "danger")
    finally:
        connection.close()

    return redirect(url_for('parishes_blueprint.manage_parishes'))