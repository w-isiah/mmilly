import pytz
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from jinja2 import TemplateNotFound

from apps import get_db_connection
from apps.church import blueprint

# --- Helpers ---

def get_kampala_time():
    """Returns current time in Africa/Kampala."""
    return datetime.now(pytz.timezone("Africa/Kampala"))

def get_segment(request):
    """Extracts the current page name from the request path."""
    try:
        segment = request.path.split('/')[-1]
        return segment if segment != '' else 'pwd'
    except:
        return None

# --- Routes ---

@blueprint.route('/manage_churches')
def manage_churches():
    """
    Church Management Dashboard: Displays church statistics, 
    the list of registered churches, and metadata for coordinators.
    """
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 1. Aggregate Church Metrics
        # This counts total churches, active status, and unique geographical distribution
        cursor.execute('''
            SELECT 
                COUNT(ChurchID) as total_churches,
                SUM(CASE WHEN IsActive = TRUE THEN 1 ELSE 0 END) as active_count,
                COUNT(DISTINCT Archdeaconry) as total_archdeaconries,
                COUNT(DISTINCT District) as total_districts
            FROM church
        ''')
        stats = cursor.fetchone()

        # 2. Fetch Church List with Coordinator Info
        # This provides the main table view for the church directory
        cursor.execute('''
            SELECT 
                ch.*, 
                CONCAT(c.Title, ' ', c.FirstName, ' ', c.LastName) as CoordinatorName,
                c.PhoneNumber as CoordinatorPhone
            FROM church ch
            JOIN coordinator c ON ch.CoordinatorID = c.CoordinatorID
            ORDER BY ch.CreatedAt DESC
        ''')
        churches = cursor.fetchall()

        # 3. Fetch Metadata for Dropdowns (Used in "Add Church" Modal)
        # We need a list of all coordinators so we can assign one to a new church
        cursor.execute('''
            SELECT 
                CoordinatorID, 
                FirstName, 
                LastName, 
                Title
            FROM coordinator 
            ORDER BY LastName ASC
        ''')
        coordinators = cursor.fetchall()

        return render_template(
            'church/church_directory.html',  # Ensure this matches your template path
            stats=stats, 
            churches=churches,
            coordinators=coordinators,
            segment='manage_churches'
        )
        
    except Exception as e:
        # Use current_app.logger.error(e) if logging is configured
        flash(f"Error loading Church data: {str(e)}", "danger")
        return redirect(url_for('home_blueprint.index'))
    finally:
        cursor.close()
        connection.close()








@blueprint.route('/add_church', methods=['POST'])
def add_church():
    """Registers a new Church and links it to a Coordinator."""
    
    # 1. Capture Form Data from the Church Modal
    church_name  = request.form.get('church_name')
    archdeaconry = request.form.get('archdeaconry')
    parish       = request.form.get('parish')
    district     = request.form.get('district')
    coordinator_id = request.form.get('coordinator_id')

    # 2. Basic validation
    # CoordinatorID is NOT NULL in your schema, so it is strictly required
    if not all([church_name, archdeaconry, parish, district, coordinator_id]):
        flash("Missing required fields. Please ensure Church Name, Location, and Coordinator are provided.", "warning")
        return redirect(url_for('church_blueprint.manage_churches'))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 3. Insert the new Church record
        # We include IsActive (default TRUE) and CreatedAt (default CURRENT_TIMESTAMP)
        cursor.execute('''
            INSERT INTO church 
                (ChurchName, Archdeaconry, Parish, District, CoordinatorID, IsActive)
            VALUES (%s, %s, %s, %s, %s, TRUE)
        ''', (church_name, archdeaconry, parish, district, coordinator_id))
        
        connection.commit()
        flash(f"Successfully registered {church_name} under the {archdeaconry} Archdeaconry.", "success")
        
    except Exception as e:
        connection.rollback()
        # Common error here might be a Foreign Key constraint if CoordinatorID doesn't exist
        flash(f"Database Error: {str(e)}", "danger")
    finally:
        cursor.close()
        connection.close()

    # Redirect back to the church directory list
    return redirect(url_for('church_blueprint.manage_churches'))




@blueprint.route('/edit-church/<int:church_id>', methods=['POST'])
def edit_church(church_id):
    """Updates an existing Church record based on church_id."""
    
    # 1. Capture updated data from the form
    church_name  = request.form.get('church_name')
    archdeaconry = request.form.get('archdeaconry')
    parish       = request.form.get('parish')
    district     = request.form.get('district')
    coordinator_id = request.form.get('coordinator_id')
    is_active    = request.form.get('is_active') == 'True' # Optional: if you add a status toggle

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 2. Update the Church record
        cursor.execute('''
            UPDATE church 
            SET ChurchName = %s, 
                Archdeaconry = %s, 
                Parish = %s, 
                District = %s, 
                CoordinatorID = %s
            WHERE ChurchID = %s
        ''', (church_name, archdeaconry, parish, district, coordinator_id, church_id))
        
        connection.commit()
        flash(f"Church '{church_name}' updated successfully.", "success")
            
    except Exception as e:
        connection.rollback()
        flash(f"Error: Could not update church details. {str(e)}", "danger")
    finally:
        cursor.close()
        connection.close()

    # 3. Redirect back to the church management dashboard
    return redirect(url_for('church_blueprint.manage_churches'))




@blueprint.route('/delete-church/<int:church_id>', methods=['POST'])
def delete_church(church_id):
    """Removes a church from the registry."""
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # The database will prevent deletion if PWD beneficiaries 
        # are still linked to this ChurchID (RESTRICT constraint).
        cursor.execute('DELETE FROM church WHERE ChurchID = %s', (church_id,))
        connection.commit()
        
        if cursor.rowcount > 0:
            flash("Church record removed from the system.", "success")
        else:
            flash("Church record not found or already removed.", "warning")
            
    except Exception as e:
        connection.rollback()
        # Custom message for Foreign Key violations
        flash(f"Error: Cannot delete this church. It may have registered PWDs or active records linked to it. {str(e)}", "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('church_blueprint.manage_churches'))

    
    



# --- Generic Routing ---

@blueprint.route('/<template>')
def route_template(template):
    """Dynamic routing for pwd-related HTML files."""
    try:
        if not template.endswith('.html'):
            template += '.html'

        segment = get_segment(request)
        # Serving from app/templates/pwd/
        return render_template(f"pwd/{template}", segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    except Exception:
        return render_template('home/page-500.html'), 500