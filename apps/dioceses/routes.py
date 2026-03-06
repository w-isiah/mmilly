import pytz
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from jinja2 import TemplateNotFound

from apps import get_db_connection
from apps.dioceses import blueprint 

# --- Helpers ---

def get_kampala_time():
    """Returns current time in Africa/Kampala."""
    return datetime.now(pytz.timezone("Africa/Kampala"))

def get_segment(request):
    """Extracts the current page name from the request path for UI highlighting."""
    try:
        segment = request.path.split('/')[-1]
        return segment if segment != '' else 'manage_dioceses'
    except:
        return None

# --- Routes ---




@blueprint.route('/manage_dioceses')
def manage_dioceses():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        # Metrics based on your schema
        cursor.execute('SELECT COUNT(id) as total_count FROM dioceses')
        stats = cursor.fetchone()

        # Fetching specific fields: id, name, description, created_at
        cursor.execute('SELECT * FROM dioceses ORDER BY name ASC')
        dioceses = cursor.fetchall()

        return render_template(
            'dioceses/diocese_list.html',
            stats=stats,
            dioceses=dioceses,
            segment='manage_dioceses'
        )
    finally:
        cursor.close()
        connection.close()


        


@blueprint.route('/add_diocese', methods=['POST'])
def add_diocese():
    """Registers a new Diocese at the root level."""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        flash("Registration failed: Diocese name is required.", "warning")
        return redirect(url_for('dioceses_blueprint.manage_dioceses'))

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        sql = "INSERT INTO dioceses (name, description) VALUES (%s, %s)"
        cursor.execute(sql, (name, description))
        connection.commit()
        flash(f"Success! '{name}' Diocese added to the system.", "success")
        
    except Exception as e:
        connection.rollback()
        flash("Database error: Ensure the diocese name is unique.", "danger")
    finally:
        connection.close()

    return redirect(url_for('dioceses_blueprint.manage_dioceses'))


@blueprint.route('/edit_diocese/<int:diocese_id>', methods=['POST'])
def edit_diocese(diocese_id):
    """Updates basic diocese information."""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute('''
            UPDATE dioceses 
            SET name = %s, description = %s
            WHERE id = %s
        ''', (name, description, diocese_id))
        connection.commit()
        flash("Diocese information updated successfully.", "info")
    except Exception as e:
        connection.rollback()
        flash(f"Update failed: {str(e)}", "danger")
    finally:
        connection.close()

    return redirect(url_for('dioceses_blueprint.manage_dioceses'))


@blueprint.route('/delete_diocese/<int:diocese_id>', methods=['POST'])
def delete_diocese(diocese_id):
    """Removes a diocese. Safeguarded by Foreign Key constraints in SQL."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute('DELETE FROM dioceses WHERE id = %s', (diocese_id,))
        connection.commit()
        
        if cursor.rowcount > 0:
            flash("Diocese removed from the registry.", "success")
        else:
            flash("Record not found.", "warning")
            
    except Exception:
        connection.rollback()
        # This will trigger if archdeaconries are still linked to the diocese
        flash("Security Block: Cannot delete a Diocese that still contains Archdeaconries.", "danger")
    finally:
        connection.close()

    return redirect(url_for('dioceses_blueprint.manage_dioceses'))


# --- Generic Routing ---

@blueprint.route('/<template>')
def route_template(template):
    try:
        if not template.endswith('.html'):
            template += '.html'

        segment = get_segment(request)
        return render_template(f"dioceses/{template}", segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    except Exception:
        return render_template('home/page-500.html'), 500