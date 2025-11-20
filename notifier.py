"""
Notification System

Sends alerts via Telegram and Email for critical events.
"""

import logging
import asyncio
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger("Notifier")


class TelegramNotifier:
    """Send notifications via Telegram Bot API."""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token
            chat_id: Target chat ID
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Rate limiting
        self.last_sent = {}
        self.min_interval = 60  # Min 60s between same message
    
    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send message to Telegram.
        
        Args:
            message: Message text
            parse_mode: Parse mode (HTML, Markdown)
            
        Returns:
            True if sent successfully
        """
        # Rate limiting check
        msg_hash = hash(message)
        if msg_hash in self.last_sent:
            elapsed = (datetime.now() - self.last_sent[msg_hash]).total_seconds()
            if elapsed < self.min_interval:
                logger.debug(f"Rate limited: same message sent {elapsed:.0f}s ago")
                return False
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/sendMessage"
                payload = {
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': parse_mode
                }
                
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        self.last_sent[msg_hash] = datetime.now()
                        logger.info("Telegram notification sent")
                        return True
                    else:
                        logger.error(f"Telegram API error: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False


class EmailNotifier:
    """Send notifications via SMTP email."""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        recipient_emails: List[str]
    ):
        """Initialize email notifier."""
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_emails = recipient_emails
    
    def send_email(self, subject: str, body: str, html: bool = False) -> bool:
        """
        Send email notification.
        
        Args:
            subject: Email subject
            body: Email body
            html: If True, send as HTML
            
        Returns:
            True if sent successfully
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipient_emails)
            
            if html:
                part = MIMEText(body, 'html')
            else:
                part = MIMEText(body, 'plain')
            
            msg.attach(part)
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {len(self.recipient_emails)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


class NotificationManager:
    """Unified notification manager."""
    
    def __init__(
        self,
        telegram: Optional[TelegramNotifier] = None,
        email: Optional[EmailNotifier] = None
    ):
        """Initialize notification manager."""
        self.telegram = telegram
        self.email = email
    
    async def notify(
        self,
        message: str,
        level: str = "info",
        channels: List[str] = None
    ):
        """
        Send notification via configured channels.
        
        Args:
            message: Notification message
            level: Severity level (info, warning, error, critical)
            channels: List of channels ('telegram', 'email'). None = all
        """
        if channels is None:
            channels = []
            if self.telegram:
                channels.append('telegram')
            if self.email:
                channels.append('email')
        
        # Format message with emoji
        emoji = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🔥'
        }.get(level, 'ℹ️')
        
        formatted_msg = f"{emoji} <b>{level.upper()}</b>\n\n{message}"
        
        # Send to channels
        if 'telegram' in channels and self.telegram:
            await self.telegram.send_message(formatted_msg)
        
        if 'email' in channels and self.email:
            subject = f"[{level.upper()}] Scraper Alert"
            self.email.send_email(subject, message)
    
    async def notify_completion(self, task_count: int, success_count: int):
        """Notify task completion."""
        message = f"✅ <b>Tasks Completed</b>\n\nTotal: {task_count}\nSuccessful: {success_count}\nFailed: {task_count - success_count}"
        await self.notify(message, level='info')
    
    async def notify_error(self, error_message: str, url: str):
        """Notify critical error."""
        message = f"❌ <b>Critical Error</b>\n\nURL: {url}\nError: {error_message}"
        await self.notify(message, level='error')
    
    async def notify_captcha(self, url: str, captcha_type: str):
        """Notify CAPTCHA encounter."""
        message = f"🤖 <b>CAPTCHA Detected</b>\n\nType: {captcha_type}\nURL: {url}"
        await self.notify(message, level='warning')
