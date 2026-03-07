import pytz
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash,session

from apps import get_db_connection
from apps.utils.decorators import login_required  # Adjust path as needed
from apps.pwd import blueprint

# --- Routes ---



@blueprint.route('/manage_pwds')
@login_required
def manage_pwds():
    """Displays PWD registry with Church and Parish info."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                # 1. Fetch PWD List with Church and Parish Join
                cursor.execute('''
                    SELECT 
                        p.*, 
                        dt.name as disability_name,
                        c.church_name,
                        pr.name as parish_name
                    FROM pwd p
                    LEFT JOIN disability_types dt ON p.disability_type_id = dt.id
                    LEFT JOIN church c ON p.church_id = c.id
                    LEFT JOIN parishes pr ON p.parish_id = pr.id
                    ORDER BY p.id DESC
                ''')
                pwds = cursor.fetchall()

                # 2. Fetch Disability Categories
                cursor.execute('SELECT id, name FROM disability_types WHERE is_active = 1 ORDER BY name ASC')
                disability_types = cursor.fetchall()

                # 3. Fetch Parishes for the Assignment Modal
                cursor.execute('SELECT id, name FROM parishes WHERE is_active = 1 ORDER BY name ASC')
                parishes = cursor.fetchall()

                # 4. Fetch Churches for the Assignment Modal
                cursor.execute('SELECT id, church_name FROM church WHERE is_active = 1 ORDER BY church_name ASC')
                churches = cursor.fetchall()

        return render_template(
            'pwd/pwd_dashboard.html', 
            pwds=pwds,
            disability_types=disability_types,
            parishes=parishes,
            churches=churches,
            segment='manage_pwds'
        )
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('home_blueprint.index'))





@blueprint.route('/assign_pwd/<int:pwd_id>', methods=['POST'])
@login_required
def assign_pwd(pwd_id):
    """Assigns PWD to Parish, Church, or removes assignment entirely."""
    role = session.get('role')
    if role != 'super_admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('pwd_blueprint.manage_pwds'))

    assignment_type = request.form.get('assignment_type') 
    assigned_id = request.form.get('assigned_id')
    
    # Defaults for 'unassign'
    parish_id = None
    church_id = None

    # Only set if a specific type was chosen and an ID exists
    if assignment_type == 'parish' and assigned_id:
        parish_id = assigned_id
    elif assignment_type == 'church' and assigned_id:
        church_id = assigned_id
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE pwd 
                    SET parish_id = %s, church_id = %s 
                    WHERE id = %s
                ''', (parish_id, church_id, pwd_id))
            conn.commit()
            
            if not parish_id and not church_id:
                flash("PWD has been unassigned from all locations.", "info")
            else:
                flash("Location assignment updated.", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
    
    return redirect(url_for('pwd_blueprint.manage_pwds'))



    





@blueprint.route('/add_pwd', methods=['POST'])

def add_pwd():
    """Registers a new PWD (Open to logged-in users)."""
    f = request.form
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                sql = '''INSERT INTO pwd 
                         (first_name, last_name, gender, date_of_birth, 
                          disability_type_id, village, phone_number, caregiver_name, 
                          caregiver_phone, notes, registration_date)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE())'''
                
                cursor.execute(sql, (
                    f.get('first_name'), f.get('last_name'), f.get('gender'), 
                    f.get('dob') or None, f.get('disability_type_id') or None,
                    f.get('village'), f.get('phone_number'), f.get('caregiver_name'),
                    f.get('caregiver_phone'), f.get('notes')
                ))
            conn.commit()
            flash(f"Successfully registered {f.get('first_name')}.", "success")
    except Exception as e:
        flash(f"Database Error: {str(e)}", "danger")

    return redirect(url_for('pwd_blueprint.manage_pwds'))


@blueprint.route('/edit_pwd/<int:pwd_id>', methods=['POST'])

def edit_pwd(pwd_id):
    """Updates PWD record - Super Admin Only."""
    role = session.get('role')
    if role != 'super_admin':
        flash("Access Denied: You do not have permission to edit records.", "warning")
        return redirect(url_for('pwd_blueprint.manage_pwds'))

    f = request.form
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                sql = '''UPDATE pwd 
                         SET first_name=%s, last_name=%s, gender=%s, date_of_birth=%s, 
                             disability_type_id=%s, village=%s, 
                             phone_number=%s, caregiver_name=%s, caregiver_phone=%s, notes=%s
                         WHERE id=%s'''
                
                cursor.execute(sql, (
                    f.get('first_name'), f.get('last_name'), f.get('gender'), 
                    f.get('dob') or None, f.get('disability_type_id') or None, 
                    f.get('village'), f.get('phone_number'), f.get('caregiver_name'), 
                    f.get('caregiver_phone'), f.get('notes'), pwd_id
                ))
            conn.commit()
            flash("Record updated successfully.", "info")
    except Exception as e:
        flash(f"Update failed: {str(e)}", "danger")

    return redirect(url_for('pwd_blueprint.manage_pwds'))


@blueprint.route('/delete_pwd/<int:pwd_id>', methods=['POST'])

def delete_pwd(pwd_id):
    """Deletes PWD record - Super Admin Only."""
    role = session.get('role')
    if role != 'super_admin':
        flash("Access Denied: You do not have permission to delete records.", "warning")
        return redirect(url_for('pwd_blueprint.manage_pwds'))

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM pwd WHERE id = %s', (pwd_id,))
            conn.commit()
            flash("Record permanently removed.", "success")
    except Exception as e:
        flash("Error: This record is linked to other data and cannot be deleted.", "danger")

    return redirect(url_for('pwd_blueprint.manage_pwds'))