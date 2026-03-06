import pytz
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from jinja2 import TemplateNotFound

from apps import get_db_connection
from apps.disability_types import blueprint # Assuming your blueprint is named this

# --- Helpers ---

def get_kampala_time():
    """Returns current time in Africa/Kampala."""
    return datetime.now(pytz.timezone("Africa/Kampala"))

def get_segment(request):
    """Extracts the current page name from the request path for UI highlighting."""
    try:
        segment = request.path.split('/')[-1]
        return segment if segment != '' else 'manage_disability_types'
    except:
        return None

# --- Routes ---

@blueprint.route('/manage_disability_types')
def manage_disability_types():
    """Displays the list of disability categories and usage statistics."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 1. Aggregate Metrics
        cursor.execute('''
            SELECT 
                COUNT(id) as total_types,
                SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) as active_types
            FROM disability_types
        ''')
        stats = cursor.fetchone()

        # 2. Fetch Disability Types List
        cursor.execute('SELECT * FROM disability_types ORDER BY name ASC')
        disability_types = cursor.fetchall()

        return render_template(
            'disability_types/disability_type_list.html',
            stats=stats,
            disability_types=disability_types,
            segment='manage_disability_types'
        )
        
    except Exception as e:
        flash(f"Error loading disability categories: {str(e)}", "danger")
        return redirect(url_for('home_blueprint.index'))
    finally:
        cursor.close()
        connection.close()


@blueprint.route('/add_disability_type', methods=['POST'])
def add_disability_type():
    """Registers a new disability category."""
    
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        flash("Registration failed: Name is required.", "warning")
        return redirect(url_for('disability_types_blueprint.manage_disability_types'))

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = '''
                INSERT INTO disability_types (name, description, is_active)
                VALUES (%s, %s, %s)
            '''
            cursor.execute(sql, (name, description, True))
        
        connection.commit()
        flash(f"Success! Category '{name}' added to the registry.", "success")
        
    except Exception as e:
        connection.rollback()
        flash("Database error: Ensure the category name is unique.", "danger")
    finally:
        connection.close()

    return redirect(url_for('disability_types_blueprint.manage_disability_types'))


@blueprint.route('/edit_disability_type/<int:type_id>', methods=['POST'])
def edit_disability_type(type_id):
    """Updates existing disability category details."""
    is_active = True if request.form.get('is_active') in ['True', '1', 'on'] else False

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute('''
            UPDATE disability_types 
            SET name = %s, description = %s, is_active = %s
            WHERE id = %s
        ''', (name, description, is_active, type_id))
        connection.commit()
        flash("Category updated successfully.", "info")
    except Exception as e:
        connection.rollback()
        flash(f"Update failed: {str(e)}", "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('disability_types_blueprint.manage_disability_types'))


@blueprint.route('/delete_disability_type/<int:type_id>', methods=['POST'])
def delete_disability_type(type_id):
    """Removes a disability category if no student records are linked to it."""
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute('DELETE FROM disability_types WHERE id = %s', (type_id,))
        connection.commit()
        
        if cursor.rowcount > 0:
            flash("Category removed from system.", "success")
        else:
            flash("Record not found.", "warning")
            
    except Exception as e:
        connection.rollback()
        # Handle Foreign Key constraints if students are already linked to this type
        flash("Cannot delete: This type is currently assigned to existing user records.", "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('disability_types_blueprint.manage_disability_types'))


# --- Generic Routing ---

@blueprint.route('/<template>')
def route_template(template):
    """Dynamic routing for disability templates."""
    try:
        if not template.endswith('.html'):
            template += '.html'

        segment = get_segment(request)
        return render_template(f"disabilities/{template}", segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    except Exception:
        return render_template('home/page-500.html'), 500