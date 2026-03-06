import pytz
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from jinja2 import TemplateNotFound

from apps import get_db_connection
from apps.archdeaconries import blueprint 

# --- Helpers ---

def get_kampala_time():
    """Returns current time in Africa/Kampala."""
    return datetime.now(pytz.timezone("Africa/Kampala"))

# --- Routes ---

@blueprint.route('/manage_archdeaconries')
def manage_archdeaconries():
    """Displays Archdeaconries joined with their Parent Dioceses."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 1. Aggregate Metrics
        cursor.execute('''
            SELECT 
                COUNT(id) as total_count,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_count
            FROM archdeaconries
        ''')
        stats = cursor.fetchone()

        # 2. Fetch Dioceses (Needed for the Add/Edit dropdown menus)
        cursor.execute('SELECT id, name FROM dioceses ORDER BY name ASC')
        dioceses = cursor.fetchall()

        # 3. Fetch Archdeaconries List with Diocese Name JOIN
        cursor.execute('''
            SELECT a.*, d.name as diocese_name 
            FROM archdeaconries a
            INNER JOIN dioceses d ON a.diocese_id = d.id
            ORDER BY a.name ASC
        ''')
        archdeaconries = cursor.fetchall()

        return render_template(
            'archdeaconries/archdeaconry_list.html',
            stats=stats,
            dioceses=dioceses,
            archdeaconries=archdeaconries,
            segment='manage_archdeaconries'
        )
        
    except Exception as e:
        flash(f"Error loading archdeaconry data: {str(e)}", "danger")
        return redirect(url_for('home_blueprint.index'))
    finally:
        cursor.close()
        connection.close()


@blueprint.route('/add_archdeaconry', methods=['POST'])
def add_archdeaconry():
    """Registers a new Archdeaconry linked to a Diocese."""
    
    diocese_id = request.form.get('diocese_id')
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name or not diocese_id:
        flash("Registration failed: Name and Diocese are required.", "warning")
        return redirect(url_for('archdeaconries_blueprint.manage_archdeaconries'))

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        # matches your table: id (auto), diocese_id, name, description, is_active (default 1), created_at (auto)
        sql = '''
            INSERT INTO archdeaconries (diocese_id, name, description, is_active) 
            VALUES (%s, %s, %s, 1)
        '''
        cursor.execute(sql, (diocese_id, name, description))
        connection.commit()
        flash(f"Success! Archdeaconry '{name}' added.", "success")
        
    except Exception as e:
        connection.rollback()
        flash(f"Database error: {str(e)}", "danger")
    finally:
        connection.close()

    return redirect(url_for('archdeaconries_blueprint.manage_archdeaconries'))


@blueprint.route('/edit_archdeaconry/<int:arch_id>', methods=['POST'])
def edit_archdeaconry(arch_id):
    """Updates name, description, status, and parent diocese."""
    
    diocese_id = request.form.get('diocese_id')
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    # Checkbox logic
    is_active = 1 if request.form.get('is_active') in ['True', '1', 'on'] else 0

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute('''
            UPDATE archdeaconries 
            SET diocese_id = %s, name = %s, description = %s, is_active = %s
            WHERE id = %s
        ''', (diocese_id, name, description, is_active, arch_id))
        connection.commit()
        flash("Archdeaconry updated successfully.", "info")
    except Exception as e:
        connection.rollback()
        flash(f"Update failed: {str(e)}", "danger")
    finally:
        connection.close()

    return redirect(url_for('archdeaconries_blueprint.manage_archdeaconries'))


@blueprint.route('/delete_archdeaconry/<int:arch_id>', methods=['POST'])
def delete_archdeaconry(arch_id):
    """Removes an archdeaconry record."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute('DELETE FROM archdeaconries WHERE id = %s', (arch_id,))
        connection.commit()
        
        if cursor.rowcount > 0:
            flash("Archdeaconry removed from system.", "success")
        else:
            flash("Record not found.", "warning")
            
    except Exception as e:
        connection.rollback()
        flash("Cannot delete: This archdeaconry may be linked to active Parishes.", "danger")
    finally:
        connection.close()

    return redirect(url_for('archdeaconries_blueprint.manage_archdeaconries'))