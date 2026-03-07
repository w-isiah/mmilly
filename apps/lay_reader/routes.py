from flask import render_template, request, redirect, url_for, flash,session
from apps.lay_reader import blueprint
from apps import get_db_connection
from apps.utils.decorators import login_required  # Adjust path as needed

@blueprint.route('/manage_lay_readers')
@login_required
def manage_lay_readers():
    """Displays lay readers with their respective church or parish assignments."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                # 1. Fetch Lay Readers with BOTH Church and Parish names
                cursor.execute('''
                    SELECT lr.*, ch.church_name, p.name as parish_name 
                    FROM lay_readers lr
                    LEFT JOIN church ch ON lr.church_id = ch.id
                    LEFT JOIN parishes p ON lr.parish_id = p.id
                    ORDER BY lr.last_name ASC, lr.first_name ASC
                ''')
                lay_readers = cursor.fetchall()

                # 2. Fetch support data for the assignment modals
                cursor.execute('SELECT id, church_name FROM church WHERE is_active = 1 ORDER BY church_name ASC')
                churches = cursor.fetchall()
                
                cursor.execute('SELECT id, name FROM parishes WHERE is_active = 1 ORDER BY name ASC')
                parishes = cursor.fetchall()

        return render_template('lay_reader/lay_reader.html', 
                               lay_readers=lay_readers, 
                               churches=churches, 
                               parishes=parishes,
                               segment='manage_lay_readers')
    except Exception as e:
        flash(f"Error loading lay reader data: {str(e)}", "danger")
        return redirect(url_for('home_blueprint.index'))

@blueprint.route('/assign_lay_reader/<int:reader_id>', methods=['POST'])
@login_required
def assign_lay_reader(reader_id):
    """Exclusively assigns a lay reader to one location or clears assignment."""
    assignment_type = request.form.get('assignment_type') 
    assigned_id = request.form.get('assigned_id')
    
    # Default to NULL for both to handle 'unassign' or 'swap'
    parish_id = None
    church_id = None

    if assignment_type == 'parish' and assigned_id:
        parish_id = assigned_id
    elif assignment_type == 'church' and assigned_id:
        church_id = assigned_id
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE lay_readers 
                    SET parish_id = %s, church_id = %s 
                    WHERE id = %s
                ''', (parish_id, church_id, reader_id))
            conn.commit()
            flash("Lay Reader assignment updated successfully.", "success")
    except Exception as e:
        flash(f"Error updating assignment: {str(e)}", "danger")
    
    return redirect(url_for('lay_readers_blueprint.manage_lay_readers'))



@blueprint.route('/add_lay_reader', methods=['POST'])
def add_lay_reader():
    f = request.form
    church_id = f.get('church_id') if f.get('church_id') else None
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                sql = '''INSERT INTO lay_readers (church_id, title, first_name, last_name, 
                         other_names, gender, phone_number, email, is_active) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)'''
                cursor.execute(sql, (church_id, f.get('title'), f.get('first_name'), 
                                   f.get('last_name'), f.get('other_names'), 
                                   f.get('gender'), f.get('phone_number'), f.get('email')))
            conn.commit()
            flash("Lay Reader added successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
    return redirect(url_for('lay_readers_blueprint.manage_lay_readers'))

@blueprint.route('/edit_lay_reader/<int:reader_id>', methods=['POST'])
def edit_lay_reader(reader_id):
    f = request.form
    is_active = 1 if f.get('is_active') else 0
    church_id = f.get('church_id') if f.get('church_id') else None
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                sql = '''UPDATE lay_readers SET church_id=%s, title=%s, first_name=%s, 
                         last_name=%s, other_names=%s, gender=%s, phone_number=%s, 
                         email=%s, is_active=%s WHERE id=%s'''
                cursor.execute(sql, (church_id, f.get('title'), f.get('first_name'), 
                                   f.get('last_name'), f.get('other_names'), f.get('gender'), 
                                   f.get('phone_number'), f.get('email'), is_active, reader_id))
            conn.commit()
            flash("Profile updated successfully.", "info")
    except Exception as e:
        flash(f"Update failed: {str(e)}", "danger")
    return redirect(url_for('lay_readers_blueprint.manage_lay_readers'))

@blueprint.route('/delete_lay_reader/<int:reader_id>', methods=['POST'])
def delete_lay_reader(reader_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM lay_readers WHERE id = %s', (reader_id,))
            conn.commit()
            flash("Record deleted.", "success")
    except Exception as e:
        flash("Record is linked to other data and cannot be deleted.", "danger")
    return redirect(url_for('lay_readers_blueprint.manage_lay_readers'))