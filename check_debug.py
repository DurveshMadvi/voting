from app import app
from models import db, AuditLog, OTP

with app.app_context():
    print("--- Latest 5 Audit Logs ---")
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(5).all()
    for l in logs:
        print(f"{l.timestamp}: {l.action} ({l.user_email})")
    
    print("\n--- Latest 5 OTPs ---")
    otps = OTP.query.order_by(OTP.created_at.desc()).limit(5).all()
    for o in otps:
        print(f"{o.created_at}: {o.email} code={o.otp_code} used={o.is_used}")
