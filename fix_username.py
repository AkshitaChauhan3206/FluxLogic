from app import app, db
from models import User

with app.app_context():
    user = User.query.filter_by(username='Akshita ').first()
    if user:
        user.username = 'Akshita'
        db.session.commit()
        print('Username updated to Akshita')
    else:
        print('User not found or already fixed')
