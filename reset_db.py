from app import app, db
import os

with app.app_context():
    db.drop_all()
    db.create_all()
    print("Database Reset Successful: All tables recreated with new schema.")
