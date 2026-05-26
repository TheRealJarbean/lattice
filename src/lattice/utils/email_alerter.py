import logging
import keyring
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Local imports
from lattice.utils.config import AppConfig

logger = logging.getLogger(__name__)

class EmailAlerter():
    def __init__(self):
        # Create smtp attribute
        self.smtp = None
        
        # This is set in the store_email_password.py script
        password = keyring.get_password('lattice', AppConfig.ALERT['sender'])
        
        # Abort if password was not found
        if password is None:
            logger.error("""
                Could not find email password in keyring! Alert emails will not send.\n\n
                Try updating the sender email and app password in Preferences, or\n
                if you don't want alerts, this can be safely ignored.         
                """)
            return
        
        # Start smtp
        self.smtp = smtplib.SMTP('smtp.gmail.com', 587)
        self.smtp.ehlo()
        self.smtp.starttls()
        
        # Log in to smtp server
        try:
            self.smtp.login(AppConfig.ALERT['sender'], password)
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Alerter email authentication failed: {e}")
            self.smtp = None
            return
        
        # Set last alert time
        self.last_alert_time = None
        self.alert_interval_min = 30

        self.send_email("Test", "This is a test email.")
        
    def send_email(self, subject: str, body: str):
        # Abort if smtp was never initialized
        if self.smtp is None:
            return
        
        # Check if an alert was sent recently
        if self.last_alert_time:
            if time.monotonic() - self.last_alert_time < self.alert_interval_min * 60:
                return
        
        # Construct message
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg.attach(MIMEText(body))
        
        # Send message
        self.smtp.sendmail(
            from_addr=AppConfig.ALERT['sender'], 
            to_addrs=AppConfig.ALERT['recipients'], 
            msg=msg.as_string()
        )