import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import Optional, List
from pathlib import Path

try:
    from linebot.v3.messaging import (
        Configuration,
        ApiClient,
        MessagingApi,
        PushMessageRequest,
        TextMessage
    )
    LINE_SDK_AVAILABLE = True
except ImportError:
    LINE_SDK_AVAILABLE = False

logger = logging.getLogger(__name__)

class LineNotifier:
    """
    A class to send notifications via LINE Messaging API (v3).
    """
    def __init__(self, access_token: Optional[str] = None, user_id: Optional[str] = None):
        self.access_token = access_token or os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
        self.user_id = user_id or os.environ.get('LINE_USER_ID')

    def send_summary(self, message: str) -> bool:
        if not LINE_SDK_AVAILABLE:
            logger.warning("line-bot-sdk not installed. Cannot send LINE notification.")
            return False

        if not self.access_token or not self.user_id:
            logger.warning("LINE_CHANNEL_ACCESS_TOKEN or LINE_USER_ID not set. Skipping notification.")
            return False
            
        if not message:
            logger.warning("Empty message provided to LineNotifier.send_summary.")
            return False

        configuration = Configuration(access_token=self.access_token)
        
        try:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                text_message = TextMessage(text=message)
                push_message_request = PushMessageRequest(
                    to=self.user_id,
                    messages=[text_message]
                )
                line_bot_api.push_message(push_message_request)
                logger.info("LINE notification sent successfully.")
                return True
        except Exception as e:
            logger.error(f"Failed to send LINE notification: {e}")
            return False

class EmailNotifier:
    """
    A class to send notifications via Email (SMTP).
    Supports multiple recipients via comma-separated string and image attachments.
    """
    def __init__(
        self, 
        smtp_server: Optional[str] = None, 
        smtp_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        recipient: Optional[str] = None
    ):
        self.smtp_server = smtp_server or os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.environ.get('SMTP_PORT', '587'))
        self.username = username or os.environ.get('SMTP_USERNAME')
        self.password = password or os.environ.get('SMTP_PASSWORD')
        # recipient can be "mail1@example.com, mail2@example.com"
        self.recipient_str = recipient or os.environ.get('SMTP_RECIPIENT', 'mylin102@gmail.com')

    def _get_recipient_list(self) -> List[str]:
        if not self.recipient_str:
            return []
        return [r.strip() for r in self.recipient_str.split(',') if r.strip()]

    def send_email(self, subject: str, body: str, is_html: bool = False, attachments: Optional[List[Path]] = None) -> bool:
        """
        Send an email notification to one or more recipients with optional attachments.
        """
        recipients = self._get_recipient_list()
        if not all([self.username, self.password]) or not recipients:
            logger.warning("Email credentials or recipients not set. Skipping email.")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = subject

            # Attach body
            msg.attach(MIMEText(body, 'html' if is_html else 'plain'))

            # Attach files
            if attachments:
                for path in attachments:
                    if path.exists():
                        with open(path, 'rb') as f:
                            img_data = f.read()
                            image = MIMEImage(img_data, name=path.name)
                            msg.attach(image)

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.username, recipients, msg.as_string())
            server.quit()
            
            logger.info(f"Email sent successfully to {len(recipients)} recipient(s) with {len(attachments) if attachments else 0} attachments.")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
