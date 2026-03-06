from flask import render_template, request, redirect, url_for, flash
from apps.lay_reader import blueprint
from apps import get_db_connection

@blueprint.route('/manage_lay_readers')
def manage_lay_readers():
    try:
        with get_db_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                # Join with church table to get church_name for the directory
                cursor.execute('''
                    SELECT lr.*, ch.church_name 
                    FROM lay_readers lr
                    LEFT JOIN church ch ON lr.church_id = ch.id
                    ORDER BY lr.last_name ASC, lr.first_name ASC
                ''')
                lay_readers = cursor.fetchall()

                cursor.execute('SELECT id, church_name FROM church ORDER BY church_name ASC')
                churches = cursor.fetchall()

        return render_template('lay_reader/lay_reader.html', 
                               lay_readers=lay_readers, 
                               churches=churches, 
                               segment='manage_lay_readers')
    except Exception as e:
        flash(f"Error loading data: {str(e)}", "danger")
        return redirect(url_for('home_blueprint.index'))

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
    return redirect(url_for('lay_reader_blueprint.manage_lay_readers'))