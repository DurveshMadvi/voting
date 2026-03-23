from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    has_voted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    votes = db.relationship("Vote", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.email}>"


class OTP(db.Model):
    __tablename__ = "otps"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_used = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<OTP {self.email} - {self.otp_code}>"


class Candidate(db.Model):
    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    party = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)  # Emoji symbol
    color = db.Column(db.String(7), nullable=False)     # Hex color for UI

    def __repr__(self):
        return f"<Candidate {self.name} ({self.party})>"


class RegisteredVoter(db.Model):
    __tablename__ = "registered_voters"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True) # Only for Admin
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<RegisteredVoter {self.email}>"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    action = db.Column(db.String(255), nullable=False)
    user_email = db.Column(db.String(120), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_email} at {self.timestamp}>"


class Vote(db.Model):
    __tablename__ = "votes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    
    # Cryptographic fields replacing plain candidate_id
    encrypted_vote = db.Column(db.Text, nullable=False)
    vote_hash = db.Column(db.String(64), nullable=False)
    digital_signature = db.Column(db.Text, nullable=False)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Vote by User:{self.user_id}>"
