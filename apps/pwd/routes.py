import pytz
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from jinja2 import TemplateNotFound

from apps import get_db_connection
from apps.pwd import blueprint

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

@blueprint.route('/manage_pwds')
def manage_pwds():
    """
    PWD Management Dashboard: Displays registration statistics, 
    the list of PWDs, and metadata for churches and coordinators.
    """
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 1. Aggregate PWD Metrics (The "Stats Cards")
        cursor.execute('''
            SELECT 
                COUNT(PWDID) as total_registered,
                SUM(CASE WHEN Gender = 'Male' THEN 1 ELSE 0 END) as male_count,
                SUM(CASE WHEN Gender = 'Female' THEN 1 ELSE 0 END) as female_count,
                COUNT(DISTINCT ChurchID) as active_churches
            FROM PWD
            WHERE IsActive = TRUE
        ''')
        stats = cursor.fetchone()

        # 2. Fetch PWD List with Church and Coordinator Info
        # This provides the main table view
        cursor.execute('''
            SELECT 
                p.*, 
                ch.ChurchName, 
                ch.Parish,
                CONCAT(c.Title, ' ', c.FirstName, ' ', c.LastName) as CoordinatorName
            FROM PWD p
            JOIN Church ch ON p.ChurchID = ch.ChurchID
            JOIN Coordinator c ON ch.CoordinatorID = c.CoordinatorID
            WHERE p.IsActive = TRUE
            ORDER BY p.RegistrationDate DESC
        ''')
        pwds = cursor.fetchall()

        # 3. Fetch Metadata for Dropdowns (Used in "Add PWD" Modal)
        # Fetch Churches so we can link PWDs to them
        cursor.execute('''
            SELECT ch.ChurchID, ch.ChurchName, ch.Archdeaconry, 
                   CONCAT(c.FirstName, ' ', c.LastName) as CoordinatorName
            FROM Church ch
            JOIN Coordinator c ON ch.CoordinatorID = c.CoordinatorID
            WHERE ch.IsActive = TRUE
            ORDER BY ch.ChurchName ASC
        ''')
        churches = cursor.fetchall()

        # Fetch Disability Types (If you want to keep this dynamic)
        disability_types = ['Physical', 'Visual', 'Hearing', 'Speech', 'Intellectual', 'Mental', 'Multiple', 'Other']

        return render_template(
            'pwd/pwd_dashboard.html', 
            stats=stats, 
            pwds=pwds,
            churches=churches,
            disability_types=disability_types,
            segment='manage_pwd'
        )
        
    except Exception as e:
        flash(f"Error loading PWD data: {str(e)}", "danger")
        return redirect(url_for('home_blueprint.index'))
    finally:
        cursor.close()
        connection.close()


@blueprint.route('/add_pwd', methods=['POST'])
def add_pwd():
    """Registers a new PWD and links them to a specific church."""
    
    # 1. Capture Form Data
    first_name      = request.form.get('first_name')
    last_name       = request.form.get('last_name')
    gender          = request.form.get('gender')
    dob             = request.form.get('dob') or None  # Allow empty DOB
    church_id       = request.form.get('church_id')
    disability_type = request.form.get('disability_type')
    phone           = request.form.get('phone')

    # 2. Basic validation
    if not all([first_name, last_name, gender, church_id, disability_type]):
        flash("Missing required fields. Please ensure Name, Gender, Church, and Disability are selected.", "warning")
        return redirect(url_for('home_blueprint.manage_pwd'))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 3. Insert the new PWD record
        # Note: We don't need to specify the CoordinatorID here because 
        # it is already linked to the ChurchID in the 'Church' table.
        cursor.execute('''
            INSERT INTO PWD 
                (FirstName, LastName, Gender, DateOfBirth, ChurchID, DisabilityType, PhoneNumber, RegistrationDate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURDATE())
        ''', (first_name, last_name, gender, dob, church_id, disability_type, phone))
        
        connection.commit()
        flash(f"Successfully registered {first_name} {last_name} in the system.", "success")
        
    except Exception as e:
        connection.rollback()
        flash(f"Database Error: {str(e)}", "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('home_blueprint.manage_pwd'))






@blueprint.route('/edit-pwd/<int:pwd_id>', methods=['POST'])
def edit_pwd(pwd_id):
    """Updates an existing PWD beneficiary's record based on pwd_id."""
    
    # 1. Capture updated data from the form
    first_name      = request.form.get('first_name')
    last_name       = request.form.get('last_name')
    gender          = request.form.get('gender')
    dob             = request.form.get('dob') or None
    church_id       = request.form.get('church_id')
    disability_type = request.form.get('disability_type')
    phone           = request.form.get('phone')

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 2. Update the PWD record
        # Note: We update ChurchID, which effectively updates the 
        # Area Coordinator linked to this person.
        cursor.execute('''
            UPDATE PWD 
            SET FirstName = %s, 
                LastName = %s, 
                Gender = %s, 
                DateOfBirth = %s, 
                ChurchID = %s, 
                DisabilityType = %s, 
                PhoneNumber = %s
            WHERE PWDID = %s
        ''', (first_name, last_name, gender, dob, church_id, disability_type, phone, pwd_id))
        
        connection.commit()
        flash(f"Record for {first_name} {last_name} updated successfully.", "success")
            
    except Exception as e:
        connection.rollback()
        # Useful if you add a unique constraint on phone numbers or IDs later
        flash(f"Error: Could not update beneficiary. {str(e)}", "danger")
    finally:
        cursor.close()
        connection.close()

    # 3. Redirect back to the dashboard we just finished
    return redirect(url_for('home_blueprint.manage_pwd'))

    



@blueprint.route('/delete-fee/<int:fee_id>', methods=['POST'])
def delete_fee(fee_id):
    """Removes a fee configuration."""
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Check if this fee is already being used in the ledger (optional safety check)
        # If you have a foreign key with 'ON DELETE RESTRICT', 
        # MySQL will prevent this automatically if students are already billed.
        
        cursor.execute('DELETE FROM fee_structure WHERE fee_id = %s', (fee_id,))
        connection.commit()
        
        if cursor.rowcount > 0:
            flash("Fee rule deleted successfully.", "success")
        else:
            flash("Fee rule not found or already deleted.", "warning")
            
    except Exception as e:
        connection.rollback()
        flash(f"Error: Cannot delete this fee. It may be linked to student records. {str(e)}", "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('pwd_blueprint.fees_summary'))



    
    



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