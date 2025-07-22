from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import db, User, Organizer, Event, EventSchedule, Ticket
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import google.generativeai as genai

from dotenv import load_dotenv
load_dotenv()


UPLOAD_FOLDER = 'static/uploads'  # Adjust as needed
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-1.5-flash")


a = Blueprint('main', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def ask_gemini(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error: {str(e)}"

@a.route('/')
def home():
    return render_template('home.html')


@a.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_role'] = 'user'
            session['user_id'] = user.id
            return redirect(url_for('main.home'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('main.login'))

    return render_template('auth/login.html')


@a.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        contact = request.form.get('contact')
        password = request.form.get('password')

        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email,
                        contact=contact, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        flash("User Registered Successfully. You can now login.", 'success')
        return redirect(url_for('main.login'))

    return render_template('auth/register.html')


@a.route('/business', methods=['GET', 'POST'])
def business():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        organizer = Organizer.query.filter_by(username=username).first()
        if organizer and check_password_hash(organizer.password, password):
            session['user_role'] = 'organizer'
            session['organizer_id'] = organizer.id
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid login credentials.', 'danger')
            return redirect(url_for('main.business'))

    return render_template('auth/business_login.html')


@a.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        email = request.form.get('email')
        contact = request.form.get('contact')
        password = request.form.get('password')

        hashed_password = generate_password_hash(password)
        new_organizer = Organizer(username=username, name=name,
                                  email=email, contact=contact,
                                  password=hashed_password)

        db.session.add(new_organizer)
        db.session.commit()

        flash("Registration successfully. You can now login to your business account.", "success")
        return redirect(url_for('main.business'))

    return render_template('auth/business_register.html')


@a.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('main.home'))

@a.route('/business/dashboard')
def dashboard():
    if session.get('organizer_id') and session.get('user_role') == 'organizer':
        organizer_id = session.get('organizer_id')
        events = Event.query.filter_by(organizer_id=organizer_id).all()
        return render_template('business/dashboard.html', events=events)
    else:
        flash("Unauthorized access", "danger")
        return redirect(url_for('main.business'))


@a.route('/create', methods=['GET', 'POST'])
def create_event():
    if session.get('user_role') != 'organizer':
        flash("Access denied", "danger")
        return redirect('/')

    if request.method == 'POST':
        session['temp_event'] = {
            'name': request.form.get('event_name'),
            'description': request.form.get('description'),
            'category': request.form.get('categories'),
            'flyer': None
        }

        flyer_file = request.files.get('flyer')
        if flyer_file and allowed_file(flyer_file.filename):
            filename = secure_filename(flyer_file.filename)
            flyer_path = os.path.join(UPLOAD_FOLDER, filename)
            flyer_file.save(flyer_path)
            session['temp_event']['flyer'] = flyer_path

        return redirect(url_for('main.schedule'))

    return render_template('business/create.html')


@a.route('/create/schedule', methods=['GET', 'POST'])
def schedule():
    if session.get('user_role') != 'organizer':
        flash("Access denied", "danger")
        return redirect('/')

    if request.method == 'POST':
        schedules = []

        venue_names = request.form.getlist('venue_name[]')
        venue_cities = request.form.getlist('venue_city[]')
        event_dates = request.form.getlist('event_date[]')
        start_times = request.form.getlist('start_time[]')
        durations = request.form.getlist('duration_hours[]')

        for i in range(len(venue_names)):
            schedules.append({
                'venue_name': venue_names[i],
                'venue_city': venue_cities[i],
                'date': event_dates[i],
                'start_time': start_times[i],
                'duration_hours': durations[i]
            })

        session['temp_schedules'] = schedules
        return redirect(url_for('main.tickets'))

    return render_template('business/schedule.html')


@a.route('/create/schedule/tickets', methods=['GET', 'POST'])
def tickets():
    if session.get('user_role') != 'organizer':
        flash("Access denied", "danger")
        return redirect('/')

    if request.method == 'POST':
        try:
            # Save Event
            event_data = session.get('temp_event')
            if not event_data:
                flash("Event session expired", "danger")
                return redirect('/create')

            new_event = Event(
                name=event_data['name'],
                description=event_data['description'],
                category=event_data['category'],
                flyer=event_data['flyer'],
                organizer_id=session.get('organizer_id'),
                created_at=datetime.utcnow()
            )
            db.session.add(new_event)
            db.session.flush()  # Get new_event.id without committing yet

            # Save Schedules
            schedule_objs = []
            for s in session.get('temp_schedules', []):
                schedule = EventSchedule(
                    event_id=new_event.id,
                    venue_name=s['venue_name'],
                    venue_city=s['venue_city'],
                    date=datetime.strptime(s['date'], '%Y-%m-%d').date(),
                    start_time=datetime.strptime(s['start_time'], '%H:%M').time(),
                    duration_hours=float(s['duration_hours'])
                )
                db.session.add(schedule)
                db.session.flush()  # Get schedule.id
                schedule_objs.append(schedule)

            # Save Tickets
            apply_same = request.form.get('applyToAll') == 'on'

            if apply_same:
                first_schedule = schedule_objs[0]
                sid = str(first_schedule.id)
                ticket_types = request.form.getlist(f'ticket_type_{sid}[]')
                prices = request.form.getlist(f'price_{sid}[]')
                quantities = request.form.getlist(f'total_quantity_{sid}[]')
                descriptions = request.form.getlist(f'description_{sid}[]')

                for sched in schedule_objs:
                    for i in range(len(ticket_types)):
                        db.session.add(Ticket(
                            event_id=new_event.id,
                            schedule_id=sched.id,
                            ticket_type=ticket_types[i],
                            price=float(prices[i]),
                            total_quantity=int(quantities[i]),
                            description=descriptions[i] or None
                        ))
            else:
                for sched in schedule_objs:
                    sid = str(sched.id)
                    ticket_types = request.form.getlist(f'ticket_type_{sid}[]')
                    prices = request.form.getlist(f'price_{sid}[]')
                    quantities = request.form.getlist(f'total_quantity_{sid}[]')
                    descriptions = request.form.getlist(f'description_{sid}[]')

                    for i in range(len(ticket_types)):
                        db.session.add(Ticket(
                            event_id=new_event.id,
                            schedule_id=sched.id,
                            ticket_type=ticket_types[i],
                            price=float(prices[i]),
                            total_quantity=int(quantities[i]),
                            description=descriptions[i] or None
                        ))

            db.session.commit()
            session.pop('temp_event', None)
            session.pop('temp_schedules', None)
            flash("Event created successfully!", "success")
            return redirect(url_for('main.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error saving event: {e}", "danger")
            return redirect('/create')

    # On GET: Build schedule list from session
    fake_schedules = session.get('temp_schedules', [])
    schedule_objs = [{
        'id': idx + 1,
        'venue_name': s['venue_name'],
        'venue_city': s['venue_city'],
        'date': datetime.strptime(s['date'], '%Y-%m-%d')
    } for idx, s in enumerate(fake_schedules)]

    return render_template('business/tickets.html', schedules=schedule_objs)
