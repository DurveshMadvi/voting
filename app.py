import random
import string
from datetime import datetime, date, timedelta
from functools import wraps

import pymysql
from flask import Flask, render_template, request, redirect, url_for, session, flash, has_request_context
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash

from crypto_utils import crypto_engine
from config import Config
from models import db, User, OTP, Candidate, Vote, RegisteredVoter, AuditLog

# ─── Auto-create database if it doesn't exist ────────────────────────────────
def ensure_database_exists():
    """Create the MySQL database if it doesn't already exist."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    try:
        conn = pymysql.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
        )
        cursor = conn.cursor()
        db_name = os.getenv("MYSQL_DB", "voting_system")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        conn.close()
    except Exception as e:
        print(f"Warning: Could not auto-create database: {e}")

ensure_database_exists()


# ─── App Setup ───────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
mail = Mail(app)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def generate_otp(length=6):
    """Generate a random numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


def login_required(f):
    """Decorator: redirect to login if user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def log_audit(action, user_email=None):
    """Helper to log an immutable audit trail entry."""
    ip = "system"
    if has_request_context():
        ip = request.remote_addr
    
    log = AuditLog(action=action, user_email=user_email, ip_address=ip)
    db.session.add(log)
    db.session.commit()


def seed_candidates():
    """Insert default candidates if the table is empty."""
    if Candidate.query.count() == 0:
        defaults = [
            Candidate(name="Aarav Sharma", party="Progressive Alliance", symbol="🌟", color="#6C63FF"),
            Candidate(name="Priya Patel", party="People's Front", symbol="🌿", color="#00C897"),
            Candidate(name="Rohan Mehta", party="Democratic Union", symbol="🔥", color="#FF6B6B"),
            Candidate(name="Sneha Reddy", party="National Coalition", symbol="⚡", color="#FFA726"),
        ]
        db.session.add_all(defaults)
        db.session.commit()

    if RegisteredVoter.query.count() == 0:
        admin_pw = generate_password_hash("Admin@123")
        dummy_voters = [
            # Special Admin Account (Password only, no OTP)
            RegisteredVoter(email="admin@gmail.com", date_of_birth=date(1980, 1, 1), password_hash=admin_pw, is_admin=True),
            # Pre-registering the main user
            RegisteredVoter(email="durvesh5.madvi@gmail.com", date_of_birth=date(2000, 1, 1), is_admin=False),
            # Regular voters
            RegisteredVoter(email="krishna.18152@sakec.ac.in", date_of_birth=date(2000, 1, 1), is_admin=False),
            RegisteredVoter(email="krishna@gmail.com", date_of_birth=date(2000, 1, 1), is_admin=False),
            RegisteredVoter(email="krishna.sharma@gmail.com", date_of_birth=date(2000, 1, 1), is_admin=False)
        ]
        db.session.add_all(dummy_voters)
        db.session.commit()
        log_audit("SYSTEM_INITIALIZED_SEEDED_VOTERS")


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password")
        
        # Check if it's the Admin Account
        if email == "admin@gmail.com":
            admin = RegisteredVoter.query.filter_by(email=email).first()
            if admin and check_password_hash(admin.password_hash, password):
                # Admin bypasses OTP
                user = User.query.filter_by(email=email).first()
                if not user:
                    user = User(email=email, is_verified=True)
                    db.session.add(user)
                    db.session.commit()
                
                session["user_id"] = user.id
                session["user_email"] = user.email
                session["is_admin"] = True
                
                log_audit("ADMIN_LOGIN_SUCCESS", email)
                flash("Admin logged in successfully!", "success")
                return redirect(url_for("results"))
            else:
                flash("Invalid Admin credentials.", "error")
                return redirect(url_for("login"))

        # Normal User Flow
        if not email:
            flash("Please enter your email address.", "error")
            return redirect(url_for("login"))

        # Check if email exists in the RegisteredVoter dummy database
        registered_voter = RegisteredVoter.query.filter_by(email=email).first()
        if not registered_voter:
            log_audit("LOGIN_FAILED_OR_INVALID_USER", email)
            flash("Email not found in the voter database. You are not eligible to vote.", "error")
            return redirect(url_for("login"))

        # Generate OTP
        otp_code = generate_otp()

        # Store OTP in database
        otp_record = OTP(email=email, otp_code=otp_code)
        db.session.add(otp_record)
        db.session.commit()

        # Send OTP via email
        try:
            msg = Message(
                subject="Your Voting System OTP",
                recipients=[email],
                html=render_template("email_otp.html", otp=otp_code),
            )
            mail.send(msg)
            log_audit("LOGIN_SUCCESS_OTP_SENT", email)
            flash("OTP has been sent to your email!", "success")
        except Exception as e:
            log_audit(f"OTP_EMAIL_FAILED: {e}", email)
            flash(f"Failed to send email. Please check your config. Error: {e}", "error")
            return redirect(url_for("login"))

        session["otp_email"] = email
        return redirect(url_for("verify_otp"))

    return render_template("login.html")


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    email = session.get("otp_email")
    if not email:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        entered_otp = request.form.get("otp", "").strip()

        # Find the latest unused OTP for this email
        otp_record = (
            OTP.query
            .filter_by(email=email, is_used=False)
            .order_by(OTP.created_at.desc())
            .first()
        )

        if otp_record and otp_record.otp_code == entered_otp:
            otp_record.is_used = True
            db.session.commit()

            # Create or fetch user
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(email=email)
                db.session.add(user)
                db.session.commit()
                log_audit("NEW_USER_ACCOUNT_CREATED", email)
                
            # Auto-verify age from registered voter database
            registered_voter = RegisteredVoter.query.filter_by(email=email).first()
            if registered_voter:
                dob = registered_voter.date_of_birth
                today = date.today()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                
                if age < 18:
                    log_audit("AGE_VERIFICATION_FAILED_UNDER_18", email)
                    flash("Access denied: You are under 18 years old.", "error")
                    return redirect(url_for("login"))
                
                # Update user profile with verify status
                user.date_of_birth = dob
                user.is_verified = True
                db.session.commit()
                log_audit("AGE_VERIFIED_FROM_DATABASE", email)

            session["user_id"] = user.id
            session["user_email"] = user.email
            session["is_admin"] = registered_voter.is_admin if registered_voter else False
            session.pop("otp_email", None)

            flash("Logged in successfully!", "success")
            log_audit("OTP_VERIFICATION_SUCCESS", email)
            return redirect(url_for("vote"))
        else:
            log_audit("OTP_VERIFICATION_FAILED_INVALID_CODE", email)
            flash("Invalid OTP. Please try again.", "error")

    return render_template("verify_otp.html", email=email)





@app.route("/vote", methods=["GET", "POST"])
@login_required
def vote():
    user = User.query.get(session["user_id"])

    if not user.is_verified:
        flash("Your age could not be verified. Access denied.", "error")
        return redirect(url_for("logout"))

    if user.has_voted:
        flash("You have already voted!", "info")
        return redirect(url_for("results"))

    candidates = Candidate.query.all()

    if request.method == "POST":
        candidate_id = request.form.get("candidate_id")
        if not candidate_id:
            flash("Please select a candidate.", "error")
            return redirect(url_for("vote"))

        candidate = Candidate.query.get(int(candidate_id))
        if not candidate:
            flash("Invalid candidate.", "error")
            return redirect(url_for("vote"))

        # Record vote with Advanced Security Cryptography
        candidate_data = str(candidate.id)
        encrypted_vote = crypto_engine.encrypt_vote(candidate_data)
        vote_hash = crypto_engine.generate_sha256_hash(candidate_data)
        signature = crypto_engine.sign_vote(encrypted_vote)

        new_vote = Vote(
            user_id=user.id,
            encrypted_vote=encrypted_vote,
            vote_hash=vote_hash,
            digital_signature=signature
        )
        db.session.add(new_vote)
        user.has_voted = True
        db.session.commit()
        
        log_audit(f"VOTE_CAST_SECURELY", user.email)

        flash("Your secure encrypted vote has been recorded successfully!", "success")
        return redirect(url_for("results"))

    return render_template("vote.html", candidates=candidates)


@app.route("/results")
@login_required
def results():
    user = User.query.get(session["user_id"])
    if not user.has_voted and not session.get("is_admin"):
        flash("You must vote first to see your confirmation.", "warning")
        return redirect(url_for("vote"))

    candidates = Candidate.query.all()
    all_votes = Vote.query.all()
    
    # If Admin: Show full tally
    if session.get("is_admin"):
        log_audit("ADMIN_VIEWED_RESULTS", session["user_email"])
        total_votes = len(all_votes)
        
        # Tally logic
        tallies = {c.id: 0 for c in candidates}
        for v in all_votes:
            try:
                decrypted_cid = int(crypto_engine.decrypt_vote(v.encrypted_vote))
                expected_hash = crypto_engine.generate_sha256_hash(str(decrypted_cid))
                if expected_hash == v.vote_hash and decrypted_cid in tallies:
                    tallies[decrypted_cid] += 1
            except: pass

        # Determine winner(s)
        max_votes = max(tallies.values()) if tallies else 0
        
        results_data = []
        for c in candidates:
            vote_count = tallies[c.id]
            percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
            results_data.append({
                "name": c.name, "party": c.party, "symbol": c.symbol, "color": c.color,
                "votes": vote_count, "percentage": float(round(percentage, 1)),
                "is_winner": (vote_count == max_votes and max_votes > 0)
            })
        
        results_data.sort(key=lambda x: x["votes"], reverse=True)
        # Fetch audit logs for the dashboard
        audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(50).all()
        
        return render_template("admin_dashboard.html", results=results_data, total_votes=total_votes, logs=audit_logs)

    # If Normal User: Show ONLY their own vote confirmation
    user_vote = Vote.query.filter_by(user_id=user.id).first()
    voted_candidate = None
    if user_vote:
        try:
            cid = int(crypto_engine.decrypt_vote(user_vote.encrypted_vote))
            voted_candidate = Candidate.query.get(cid)
        except: pass

    return render_template("results.html", voted_candidate=voted_candidate)


@app.route("/logout")
def logout():
    old_email = session.get("user_email")
    session.clear()
    if old_email:
        log_audit("USER_LOGOUT", old_email)
    flash("Logged out successfully.", "success")
    return redirect(url_for("index"))


# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_candidates()
    app.run(debug=True)
