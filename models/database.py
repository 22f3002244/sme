from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.sql import func

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    contact = db.Column(db.String(20), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('Booking', backref='user', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='user', cascade='all, delete-orphan')


class Organizer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(20), nullable=True)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    events = db.relationship('Event', backref='organizer', cascade='all, delete-orphan')


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey('organizer.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    flyer = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    schedules = db.relationship('EventSchedule', backref='event', cascade='all, delete-orphan')
    tickets = db.relationship('Ticket', backref='event', cascade='all, delete-orphan')
    bookings = db.relationship('Booking', backref='event', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='event', cascade='all, delete-orphan')


class EventSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    duration_hours = db.Column(db.Float, nullable=True)
    venue_name = db.Column(db.String(150), nullable=False)
    venue_city = db.Column(db.String(100), nullable=False)

    tickets = db.relationship('Ticket', backref='schedule', cascade='all, delete-orphan')
    bookings = db.relationship('Booking', backref='schedule', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='schedule', cascade='all, delete-orphan')


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('event_schedule.id'), nullable=False)
    ticket_type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_quantity = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(255))

    bookings = db.relationship('Booking', backref='ticket', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='ticket', cascade='all, delete-orphan')


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('event_schedule.id'), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, default=func.current_date())
    payment_time = db.Column(db.Time, default=func.current_time())
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('Booking', backref='payment', cascade='all, delete-orphan')


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('event_schedule.id'), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=False)
    booking_date = db.Column(db.Date, default=func.current_date())
    booking_time = db.Column(db.Time, default=func.current_time())
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
