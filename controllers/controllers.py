from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import math

from app import app
from database import db
from models.models import User, ParkingLot, ParkingSpot, Reservation

def role_required(role):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash("You do not have permission to access this page.")
                return redirect(url_for('login'))
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password, full_name=full_name, role='user')
        
        db.session.add(new_user)
        db.session.commit()

        flash(f"Your account has been created! Please login to move forward.", 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('login'))
        
        login_user(user)

        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Admin dashboard
@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    lots = ParkingLot.query.order_by(ParkingLot.id).all()
    users = User.query.filter_by(role='user').all()
    return render_template('admin_dashboard.html', lots=lots, users=users)

@app.route('/admin/add_lot', methods=['POST'])
@login_required
@role_required('admin')
def add_lot():
    name = request.form.get('name')
    capacity = int(request.form.get('capacity'))
    price = float(request.form.get('price'))

    new_lot = ParkingLot(name=name, capacity=capacity, price_per_hour=price)
    db.session.add(new_lot)

    spots_for_lot = []
    for i in range(1, capacity + 1):
        spot = ParkingSpot(spot_number=i)
        spots_for_lot.append(spot)
    
    new_lot.spots = spots_for_lot
    
    db.session.commit()
    
    flash(f"Parking lot '{name}' and its {capacity} spots have been created successfully!")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_lot/<int:lot_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_lot(lot_id):
    lot_to_delete = ParkingLot.query.get_or_404(lot_id)

    # Checking if any spot in the lot is occupied
    can_delete = True
    for spot in lot_to_delete.spots:
        if spot.status != 'Available':
            can_delete = False
            break

    if can_delete:
        # If all spots are available in lot, we can delete it!
        db.session.delete(lot_to_delete)
        db.session.commit()
        flash(f"Parking lot '{lot_to_delete.name}' and all its spots have been successfully deleted.", 'success')
    else:
        flash(f"Cannot delete lot '{lot_to_delete.name}' because it has occupied spots.", 'error')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_lot/<int:lot_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    if request.method == 'POST':
        lot.name = request.form.get('name')
        lot.price_per_hour = float(request.form.get('price'))
        new_capacity = int(request.form.get('capacity'))
        
        current_capacity = lot.capacity
        if new_capacity > current_capacity:
            for i in range(current_capacity + 1, new_capacity + 1):
                new_spot = ParkingSpot(spot_number=i, lot_id=lot.id)
                db.session.add(new_spot)
            flash(f"{new_capacity - current_capacity} new spots added.", 'success')
        
        elif new_capacity < current_capacity:
            num_to_remove = current_capacity - new_capacity
            spots_to_check = ParkingSpot.query.filter_by(lot_id=lot.id).order_by(ParkingSpot.spot_number.desc()).limit(num_to_remove).all()
            
            can_decrease = all(spot.status == 'Available' for spot in spots_to_check)
            print('can decrease',can_decrease)

            if can_decrease:
                for spot in spots_to_check:
                    db.session.delete(spot)
                flash(f"{num_to_remove} spots removed.", 'success')
            else:
                flash("Cannot decrease capacity: one or more spots to be removed are currently occupied.", 'error')
                return redirect(url_for('edit_lot', lot_id=lot.id))

        lot.capacity = new_capacity
        db.session.commit()
        flash(f"Lot '{lot.name}' has been updated successfully!", 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_lot.html', lot=lot)

@app.route('/admin/lot/<int:lot_id>/spots')
@login_required
@role_required('admin')
def view_lot_spots(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = sorted(lot.spots, key=lambda x: x.spot_number)
    return render_template('view_spots.html', lot=lot, spots=spots)

@app.route('/admin/all_reservations')
@login_required
@role_required('admin')
def all_reservations():
    all_completed = Reservation.query.filter(
        Reservation.end_time.isnot(None)
    ).order_by(Reservation.start_time.desc()).all()
    
    return render_template('all_reservations.html', reservations=all_completed)

# User dashboard
@app.route('/user/dashboard')
@login_required
@role_required('user')
def user_dashboard():
    active_reservation = Reservation.query.filter_by(user_id=current_user.id, end_time=None).first()

    if active_reservation:
        return render_template('user_dashboard.html', active_reservation=active_reservation)
    else:
        lots = ParkingLot.query.order_by(ParkingLot.id).all()
        return render_template('user_dashboard.html', lots=lots)

@app.route('/user/book_spot', methods=['POST'])
@login_required
@role_required('user')
def book_spot():
    lot_id = request.form.get('lot_id')
    available_spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='Available').first()
    
    if available_spot:
        available_spot.status = 'Occupied'
        
        new_reservation = Reservation(
            user_id=current_user.id,
            spot_id=available_spot.id,
            start_time=datetime.now()
        )
        db.session.add(new_reservation)
        
        db.session.commit()
        
        lot = ParkingLot.query.get(lot_id)
        flash(f"Success! You have been assigned Spot #{available_spot.spot_number} in {lot.name}.", 'success')
    else:
        flash("Sorry, this parking lot is currently full. Please try another one.", 'error')
        
    return redirect(url_for('user_dashboard'))

@app.route('/user/release_spot', methods=['POST'])
@login_required
@role_required('user')
def release_spot():
    reservation_id = request.form.get('reservation_id')
    reservation = Reservation.query.get_or_404(reservation_id)
    
    if reservation.user_id != current_user.id:
        flash("You do not have permission to perform this action.", 'error')
        return redirect(url_for('user_dashboard'))

    reservation.end_time = datetime.now()
    
    duration_seconds = (reservation.end_time - reservation.start_time).total_seconds()
    duration_hours = duration_seconds / 3600

    price_per_hour = reservation.spot.lot.price_per_hour

    # Charging for a min. of one hour if parked for <1hr
    cost = math.ceil(duration_hours) * price_per_hour
    reservation.cost = round(cost, 2)
    
    spot = ParkingSpot.query.get(reservation.spot_id)
    spot.status = 'Available'
    
    db.session.commit()
    
    flash(f"You have successfully released your spot. Total cost: ${reservation.cost:.2f}", 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/history')
@login_required
@role_required('user')
def parking_history():
    completed_reservations = Reservation.query.filter(
        Reservation.user_id == current_user.id,
        Reservation.end_time.isnot(None)
    ).order_by(Reservation.start_time.desc()).all()
    
    return render_template('parking_history.html', reservations=completed_reservations)

if __name__ == '__main__':
    app.run(debug=True)