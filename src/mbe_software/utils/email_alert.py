import logging
import keyring
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class EmailAlert():
    def __init__(self, recipients: list[str]):
        # Create smtp attribute
        self.smtp = None
        
        # This is set in the store_email_password.py script
        password = keyring.get_password('mbe_software', 'mbe.lab.alerts@gmail.com')
        
        # Abort if password was not found
        if password is None:
            logger.error("""
                Could not find email password in keyring! Alert emails will not send.\n\n
                Try running store_email_password.py if this is a new system, or\n
                if you don't want alerts, this can be safely ignored.         
                """)
            return
        
        # Store addresses
        self.from_address = 'mbe.lab.alerts@gmail.com'
        self.recipients = recipients
        
        # Start smtp
        self.smtp = smtplib.SMTP('smtp.gmail.com', 587)
        self.smtp.ehlo()
        self.smtp.starttls()
        
        # Log in to smtp server
        self.smtp.login(self.from_address, password)
        
    def send_email(self, subject: str, body: str):
        # Abort if smtp was never initialized
        if self.smtp is None:
            return
        
        # Construct message
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg.attach(MIMEText(body))
        
        # Send message
        self.smtp.sendmail(
            from_addr=self.from_address, 
            to_addrs=self.recipients, 
            msg=msg.as_string()
        )