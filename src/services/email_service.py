import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional

class EmailService:
    """Service for sending email notifications"""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL", "noreply@advancia.com")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.app_url = os.getenv("APP_URL", "http://localhost:8000")
        self.test_mode = os.getenv("EMAIL_TEST_MODE", "false").lower() == "true"
    
    def send_verification_email(self, recipient_email: str, username: str, token: str) -> bool:
        """Send email verification link"""
        try:
            verification_link = f"{self.app_url}/verify-email?token={token}"
            subject = "Verify Your Email Address"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Welcome, {username}!</h2>
                    <p>Please verify your email address to complete your registration.</p>
                    <p><a href="{verification_link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a></p>
                    <p>Or copy this link: {verification_link}</p>
                    <p>This link expires in 24 hours.</p>
                    <p>Best regards,<br>Advancia Team</p>
                </body>
            </html>
            """
            
            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending verification email: {e}")
            return False
    
    def send_kyc_pending_email(self, recipient_email: str, username: str) -> bool:
        """Send KYC submission confirmation email"""
        try:
            subject = "KYC Submission Received"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>KYC Verification Submitted</h2>
                    <p>Hi {username},</p>
                    <p>We have received your KYC documents. Our team will review them and notify you within 2-3 business days.</p>
                    <p>Status: Under Review</p>
                    <p>Best regards,<br>Advancia Compliance Team</p>
                </body>
            </html>
            """
            
            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending KYC email: {e}")
            return False
    
    def send_kyc_approved_email(self, recipient_email: str, username: str) -> bool:
        """Send KYC approval email"""
        try:
            subject = "KYC Verification Approved"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>KYC Verification Approved!</h2>
                    <p>Hi {username},</p>
                    <p>Congratulations! Your KYC verification has been approved.</p>
                    <p>You can now access all features of your account including withdrawals.</p>
                    <p>Best regards,<br>Advancia Compliance Team</p>
                </body>
            </html>
            """
            
            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending approval email: {e}")
            return False
    
    def send_kyc_rejected_email(self, recipient_email: str, username: str, reason: str) -> bool:
        """Send KYC rejection email"""
        try:
            subject = "KYC Verification Review"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>KYC Verification Review</h2>
                    <p>Hi {username},</p>
                    <p>Thank you for submitting your KYC documents. Unfortunately, we were unable to verify your information.</p>
                    <p><strong>Reason:</strong> {reason}</p>
                    <p>Please resubmit with correct information or contact support.</p>
                    <p>Best regards,<br>Advancia Compliance Team</p>
                </body>
            </html>
            """
            
            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending rejection email: {e}")
            return False
    
    def send_withdrawal_pending_email(self, recipient_email: str, username: str, amount: float) -> bool:
        """Send withdrawal request pending email"""
        try:
            subject = "Withdrawal Request Received"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Withdrawal Request</h2>
                    <p>Hi {username},</p>
                    <p>Your withdrawal request for ${amount:.2f} has been received.</p>
                    <p>Status: Pending Admin Approval</p>
                    <p>We will notify you once it has been processed.</p>
                    <p>Best regards,<br>Advancia Finance Team</p>
                </body>
            </html>
            """
            
            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending withdrawal email: {e}")
            return False
    
    def send_withdrawal_approved_email(self, recipient_email: str, username: str, amount: float) -> bool:
        """Send withdrawal approval email"""
        try:
            subject = "Withdrawal Approved"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Withdrawal Approved</h2>
                    <p>Hi {username},</p>
                    <p>Your withdrawal request for ${amount:.2f} has been approved.</p>
                    <p>The funds will be transferred to your registered bank account within 1-2 business days.</p>
                    <p>Best regards,<br>Advancia Finance Team</p>
                </body>
            </html>
            """
            
            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending approval email: {e}")
            return False

    def send_withdrawal_rejected_email(self, recipient_email: str, username: str, amount: float, reason: str) -> bool:
        """Send withdrawal rejection email"""
        try:
            subject = "Withdrawal Request Rejected"

            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Withdrawal Request Rejected</h2>
                    <p>Hi {username},</p>
                    <p>Your withdrawal request for ${amount:.2f} was rejected.</p>
                    <p><strong>Reason:</strong> {reason}</p>
                    <p>Please contact support if you believe this is an error.</p>
                    <p>Best regards,<br>Advancia Finance Team</p>
                </body>
            </html>
            """

            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending withdrawal rejection email: {e}")
            return False

    def send_card_request_approved_email(self, recipient_email: str, username: str, card_type: str, memo: str) -> bool:
        """Send card request approval email"""
        try:
            subject = "Card Request Approved"

            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Card Request Approved</h2>
                    <p>Hi {username},</p>
                    <p>Your request for a {card_type} card has been approved.</p>
                    <p>{memo or ''}</p>
                    <p>You can now manage your card in the dashboard.</p>
                    <p>Best regards,<br>Advancia Card Services</p>
                </body>
            </html>
            """

            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending card approval email: {e}")
            return False

    def send_card_request_rejected_email(self, recipient_email: str, username: str, card_type: str, reason: str) -> bool:
        """Send card request rejection email"""
        try:
            subject = "Card Request Rejected"

            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Card Request Rejected</h2>
                    <p>Hi {username},</p>
                    <p>Your request for a {card_type} card was rejected.</p>
                    <p><strong>Reason:</strong> {reason}</p>
                    <p>If you believe this is incorrect, please contact support.</p>
                    <p>Best regards,<br>Advancia Card Services</p>
                </body>
            </html>
            """

            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending card rejection email: {e}")
            return False

    def send_card_funded_email(self, recipient_email: str, username: str, amount: float, card_token: str) -> bool:
        """Send card funding confirmation email"""
        try:
            subject = "Card Funding Confirmed"

            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Card Funding Successful</h2>
                    <p>Hi {username},</p>
                    <p>Your card ending with {card_token[-4:]} has been funded with ${amount:.2f}.</p>
                    <p>You can now use it for transactions.</p>
                    <p>Best regards,<br>Advancia Card Services</p>
                </body>
            </html>
            """

            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending card funded email: {e}")
            return False

    def send_transaction_success_email(self, recipient_email: str, username: str, amount: float, currency: str, tx_hash: str) -> bool:
        """Send transaction success email"""
        try:
            subject = "Transaction Successful"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Transaction Completed</h2>
                    <p>Hi {username},</p>
                    <p>Your transaction has been successfully processed.</p>
                    <p><strong>Amount:</strong> {amount} {currency}</p>
                    <p><strong>Transaction Hash:</strong> {tx_hash}</p>
                    <p>You can view this transaction in your transaction history.</p>
                    <p>Best regards,<br>Advancia Wallet Team</p>
                </body>
            </html>
            """
            
            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending transaction success email: {e}")
            return False
    
    def send_transaction_failed_email(self, recipient_email: str, username: str, amount: float, currency: str, error_message: str) -> bool:
        """Send transaction failure email"""
        try:
            subject = "Transaction Failed"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Transaction Failed</h2>
                    <p>Hi {username},</p>
                    <p>Unfortunately, your transaction could not be completed.</p>
                    <p><strong>Amount:</strong> {amount} {currency}</p>
                    <p><strong>Reason:</strong> {error_message}</p>
                    <p>Please try again or contact support if the issue persists.</p>
                    <p>Best regards,<br>Advancia Wallet Team</p>
                </body>
            </html>
            """
            
            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending transaction failure email: {e}")
            return False

    def send_email(self, recipient_email: str, subject: str, template: str | None = None, data: dict | None = None) -> bool:
        """Send a generic templated email."""
        try:
            body = self._build_template_body(subject, template, data or {})
            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending templated email: {e}")
            return False

    def _build_template_body(self, subject: str, template: str | None, data: dict) -> str:
        if template == "account_rejection":
            return f"""
            <html>
                <body style=\"font-family: Arial, sans-serif;\">
                    <h2>Account Application Rejected</h2>
                    <p>Hi {data.get('user_name', 'User')},</p>
                    <p>Unfortunately, your account application was rejected.</p>
                    <p><strong>Reason:</strong> {data.get('rejection_reason', 'Not specified')}</p>
                    <p>{data.get('rejection_details', '')}</p>
                    <p>Appeal Allowed: {data.get('can_appeal', False)}</p>
                    <p>Appeal Deadline: {data.get('appeal_deadline', 'N/A')}</p>
                    <p>If you have questions, contact {data.get('support_email', self.sender_email)}.</p>
                    <p>Best regards,<br>Advancia Support Team</p>
                </body>
            </html>
            """
        if template == "appeal_notification":
            return f"""
            <html>
                <body style=\"font-family: Arial, sans-serif;\">
                    <h2>Account Appeal Submitted</h2>
                    <p>User: {data.get('user_name', 'User')} ({data.get('user_email', '')})</p>
                    <p>Original Reason: {data.get('original_reason', '')}</p>
                    <p>Appeal Message: {data.get('appeal_message', 'No message provided')}</p>
                    <p>Please review the appeal in the admin dashboard: <a href=\"{data.get('admin_dashboard_url', self.app_url)}\">Admin Dashboard</a></p>
                    <p>Best regards,<br>Advancia Support Team</p>
                </body>
            </html>
            """
        if template == "appeal_approved":
            return f"""
            <html>
                <body style=\"font-family: Arial, sans-serif;\">
                    <h2>Account Appeal Approved</h2>
                    <p>Hi {data.get('user_name', 'User')},</p>
                    <p>Your appeal has been approved.</p>
                    <p>{data.get('admin_notes', '')}</p>
                    <p>Best regards,<br>Advancia Support Team</p>
                </body>
            </html>
            """
        if template == "appeal_denied":
            return f"""
            <html>
                <body style=\"font-family: Arial, sans-serif;\">
                    <h2>Account Appeal Denied</h2>
                    <p>Hi {data.get('user_name', 'User')},</p>
                    <p>Your appeal was reviewed and denied.</p>
                    <p>{data.get('admin_notes', '')}</p>
                    <p>If you have questions, contact {data.get('support_email', self.sender_email)}.</p>
                    <p>Best regards,<br>Advancia Support Team</p>
                </body>
            </html>
            """
        if template in ["card_frozen", "card_unfrozen"]:
            action = "frozen" if template == "card_frozen" else "unfrozen"
            return f"""
            <html>
                <body style=\"font-family: Arial, sans-serif;\">
                    <h2>Card {action.title()}</h2>
                    <p>Hi {data.get('user_name', 'User')},</p>
                    <p>Your card ending in {data.get('card_last_4', '****')} has been {action}.</p>
                    <p>Reason: {data.get('reason', 'N/A')}</p>
                    <p>Best regards,<br>Advancia Card Services</p>
                </body>
            </html>
            """
        if template == "card_issued":
            return f"""
            <html>
                <body style=\"font-family: Arial, sans-serif;\">
                    <h2>Virtual Card Issued</h2>
                    <p>Hi {data.get('user_name', 'User')},</p>
                    <p>Your card request has been approved and a new card ending in {data.get('card_token', '****')[-4:]} is ready to use.</p>
                    <p>Best regards,<br>Advancia Card Services</p>
                </body>
            </html>
            """
        if template == "card_rejected":
            return f"""
            <html>
                <body style=\"font-family: Arial, sans-serif;\">
                    <h2>Card Request Rejected</h2>
                    <p>Hi {data.get('user_name', 'User')},</p>
                    <p>Your card request was rejected.</p>
                    <p>Reason: {data.get('reason', 'N/A')}</p>
                    <p>Best regards,<br>Advancia Card Services</p>
                </body>
            </html>
            """
        if template == "withdrawal_completed":
            return f"""
            <html>
                <body style=\"font-family: Arial, sans-serif;\">
                    <h2>Withdrawal Completed</h2>
                    <p>Hi {data.get('user_name', 'User')},</p>
                    <p>Your withdrawal of ${data.get('amount', 0):.2f} {data.get('currency', '')} has been completed.</p>
                    <p>Bank account ending in {data.get('bank_account', '****')}.</p>
                    <p>Best regards,<br>Advancia Finance Team</p>
                </body>
            </html>
            """
        if template is None:
            template = "generic"

        bullet_lines = "".join(
            f"<p><strong>{key.replace('_', ' ').title()}:</strong> {value}</p>"
            for key, value in data.items()
        )
        return f"""
        <html>
            <body style=\"font-family: Arial, sans-serif;\">
                <h2>{subject}</h2>
                {bullet_lines}
                <p>Best regards,<br>Advancia Team</p>
            </body>
        </html>
        """
    
    def _send_email(self, recipient_email: str, subject: str, body: str) -> bool:
        """Internal method to send email"""
        if self.test_mode:
            print(f"TEST MODE: Would send email to {recipient_email}")
            print(f"Subject: {subject}")
            print(f"Body: {body[:200]}...")
            return True
        
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient_email
            
            part = MIMEText(body, "html")
            message.attach(part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, message.as_string())
            
            return True
        except Exception as e:
            print(f"Error sending email to {recipient_email}: {e}")
            return False

# Email service instance
email_service = EmailService()

def send_email(recipient_email: str | None = None, to_email: str | None = None, subject: str = "", template: str | None = None, data: dict | None = None) -> bool:
    address = recipient_email or to_email
    if not address:
        raise ValueError("Email recipient must be provided via recipient_email or to_email")
    return email_service.send_email(address, subject, template, data)

