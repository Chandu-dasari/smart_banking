from datetime import datetime, timedelta
from models import db, TimeSlot

DEFAULT_SLOT_TIMES = [
    "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
    "11:00 AM", "11:30 AM", "12:00 PM",
    "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM",
    "04:00 PM", "04:30 PM"
]

def generate_default_slots(days_ahead=30):
    """Generate default slots for next N days if not exist"""
    today = datetime.today()
    created = 0
    for i in range(1, days_ahead + 1):
        day = today + timedelta(days=i)
        if day.weekday() >= 5:  # Skip weekends
            continue
        date_str = day.strftime('%Y-%m-%d')
        for t in DEFAULT_SLOT_TIMES:
            existing = TimeSlot.query.filter_by(date=date_str, time=t).first()
            if not existing:
                slot = TimeSlot(date=date_str, time=t, max_capacity=2, booked_count=0)
                db.session.add(slot)
                created += 1
    db.session.commit()
    return created

def get_available_slots_by_date(date_str):
    slots = TimeSlot.query.filter_by(date=date_str, is_active=True).all()
    return [s for s in slots]

def get_calendar_data(month, year):
    """Get slots availability for calendar view"""
    from calendar import monthrange
    _, days = monthrange(year, month)
    calendar_data = {}
    for day in range(1, days + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        slots = TimeSlot.query.filter_by(date=date_str, is_active=True).all()
        available = sum(1 for s in slots if s.is_available)
        total = len(slots)
        calendar_data[day] = {'available': available, 'total': total}
    return calendar_data
