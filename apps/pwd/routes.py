import pytz
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from apps import get_db_connection
from apps.pwd import blueprint

# --- Helpers ---
def get_kampala_time():
    """Returns current time in Africa/Kampala."""
    return datetime.now(pytz.timezone("Africa/Kampala"))

# --- Routes ---

@blueprint.route('/manage_pwds')
def manage_pwds():
    """Displays PWD metrics and the registry with disability and church joins."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                # 1. Aggregate PWD Metrics
                cursor.execute('''
                    SELECT 
                        COUNT(id) as total_registered,
                        SUM(CASE WHEN gender = 'Male' THEN 1 ELSE 0 END) as male_count,
                        SUM(CASE WHEN gender = 'Female' THEN 1 ELSE 0 END) as female_count
                    FROM pwd
                ''')
                stats = cursor.fetchone()

                # 2. Fetch PWD List - Note: dt.name matches your schema
                cursor.execute('''
                    SELECT 
                        p.*, 
                        ch.church_name,
                        dt.name as disability_name
                    FROM pwd p
                    LEFT JOIN church ch ON p.church_id = ch.id
                    LEFT JOIN disability_types dt ON p.disability_type_id = dt.id
                    ORDER BY p.id DESC
                ''')
                pwds = cursor.fetchall()

                # 3. Fetch Metadata for Modals
                cursor.execute('SELECT id, church_name FROM church WHERE is_active = 1 ORDER BY church_name ASC')
                churches = cursor.fetchall()

                # Note: Selecting 'name' to match your disability_types table
                cursor.execute('SELECT id, name FROM disability_types WHERE is_active = 1 ORDER BY name ASC')
                disability_types = cursor.fetchall()

        return render_template(
            'pwd/pwd_dashboard.html', 
            stats=stats, 
            pwds=pwds,
            churches=churches,
            disability_types=disability_types,
            segment='manage_pwds'
        )
        
    except Exception as e:
        flash(f"Error loading PWD data: {str(e)}", "danger")
        return redirect(url_for('home_blueprint.index'))


@blueprint.route('/add_pwd', methods=['POST'])
def add_pwd():
    """Registers a new PWD using the expanded schema."""
    f = request.form
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Registration date uses DB CURDATE() to ensure consistency
                sql = '''INSERT INTO pwd 
                         (first_name, last_name, gender, date_of_birth, church_id, 
                          disability_type_id, village, phone_number, caregiver_name, 
                          caregiver_phone, notes, registration_date)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE())'''
                
                cursor.execute(sql, (
                    f.get('first_name'), 
                    f.get('last_name'), 
                    f.get('gender'), 
                    f.get('dob') or None, 
                    f.get('church_id') or None, 
                    f.get('disability_type_id') or None,
                    f.get('village'),
                    f.get('phone_number'),
                    f.get('caregiver_name'),
                    f.get('caregiver_phone'),
                    f.get('notes')
                ))
            conn.commit()
            flash(f"Successfully registered {f.get('first_name')} {f.get('last_name')}.", "success")
    except Exception as e:
        flash(f"Database Error: {str(e)}", "danger")

    return redirect(url_for('pwd_blueprint.manage_pwds'))


@blueprint.route('/edit_pwd/<int:pwd_id>', methods=['POST'])
def edit_pwd(pwd_id):
    """Updates an existing PWD record."""
    f = request.form
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                sql = '''UPDATE pwd 
                         SET first_name=%s, last_name=%s, gender=%s, date_of_birth=%s, 
                             church_id=%s, disability_type_id=%s, village=%s, 
                             phone_number=%s, caregiver_name=%s, caregiver_phone=%s, notes=%s
                         WHERE id=%s'''
                
                cursor.execute(sql, (
                    f.get('first_name'), f.get('last_name'), f.get('gender'), 
                    f.get('dob') or None, f.get('church_id') or None, 
                    f.get('disability_type_id') or None, f.get('village'), 
                    f.get('phone_number'), f.get('caregiver_name'), 
                    f.get('caregiver_phone'), f.get('notes'), pwd_id
                ))
            conn.commit()
            flash("Record updated successfully.", "info")
    except Exception as e:
        flash(f"Update failed: {str(e)}", "danger")

    return redirect(url_for('pwd_blueprint.manage_pwds'))


@blueprint.route('/delete_pwd/<int:pwd_id>', methods=['POST'])
def delete_pwd(pwd_id):
    """Deletes a PWD record."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM pwd WHERE id = %s', (pwd_id,))
            conn.commit()
            flash("Beneficiary removed from registry.", "success")
    except Exception as e:
        # Standard error handling if foreign key constraints are violated
        flash("Error: This record is linked to other ministry data and cannot be deleted.", "danger")

    return redirect(url_for('pwd_blueprint.manage_pwds'))