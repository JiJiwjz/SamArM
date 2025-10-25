"""
邮件发送模块
负责发送邮件到收件人
"""

import smtplib
import logging
from typing import List, Dict, Optional, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import time

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件发送器"""
    
    def __init__(self, smtp_config: Dict[str, any]):
        """
        初始化邮件发送器
        
        Args:
            smtp_config: SMTP配置字典，包含：
                - sender_email: 发送者邮箱
                - sender_password: 发送者密码/授权码
                - smtp_server: SMTP服务器地址
                - smtp_port: SMTP端口（465=SSL，587=STARTTLS）
                - use_tls: 是否使用STARTTLS（默认True）
                - use_ssl: 是否使用SSL（默认当端口为465时开启）
                - timeout: 连接超时（秒）
                - max_retries: 默认重试次数（整型，可选，默认=1）
        """
        self.sender_email = smtp_config.get('sender_email')
        self.sender_password = smtp_config.get('sender_password')
        self.smtp_server = smtp_config.get('smtp_server')
        self.smtp_port = int(smtp_config.get('smtp_port', 587))
        self.use_tls = smtp_config.get('use_tls', True)
        # 端口为465默认使用SSL
        self.use_ssl = smtp_config.get('use_ssl', self.smtp_port == 465)
        self.timeout = int(smtp_config.get('timeout', 20))
        # 将默认重试次数改为1（可由配置覆盖）
        self.max_retries = int(smtp_config.get('max_retries', 1))
        
        if not all([self.sender_email, self.sender_password, self.smtp_server]):
            raise ValueError("SMTP配置不完整！请检查sender_email、sender_password和smtp_server")
        
        logger.info(
            f"邮件发送器已初始化: {self.smtp_server}:{self.smtp_port} "
            f"(SSL={self.use_ssl}, STARTTLS={self.use_tls and not self.use_ssl}, "
            f"timeout={self.timeout}s, max_retries={self.max_retries})"
        )
    
    def _create_message(self, to_email: str, subject: str, html_content: str, 
                       plain_content: Optional[str] = None) -> MIMEMultipart:
        """
        创建邮件消息
        """
        msg = MIMEMultipart('alternative')
        msg['From'] = Header(f'Arxiv Mailbot <{self.sender_email}>')
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8')
        
        # 添加纯文本部分（备选）
        if plain_content:
            msg.attach(MIMEText(plain_content, 'plain', 'utf-8'))
        
        # 添加HTML部分
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        return msg
    
    def send_email(self, to_email: str, subject: str, html_content: str, 
                   plain_content: Optional[str] = None, max_retries: Optional[int] = None) -> Tuple[bool, str]:
        """
        发送单封邮件
        
        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            html_content: HTML内容
            plain_content: 纯文本内容
            max_retries: 最大重试次数（不传则使用初始化时的默认值，当前默认=1）
        
        Returns:
            (是否成功, 消息)
        """
        attempts = int(max_retries) if max_retries is not None else self.max_retries
        
        for attempt in range(1, attempts + 1):
            try:
                # 创建消息
                msg = self._create_message(to_email, subject, html_content, plain_content)
                
                # 选择 SMTP 客户端类型
                server_cls = smtplib.SMTP_SSL if self.use_ssl else smtplib.SMTP
                
                logger.debug(
                    f"第{attempt}次尝试连接SMTP服务器: {self.smtp_server}:{self.smtp_port} "
                    f"(SSL={self.use_ssl})"
                )
                
                with server_cls(self.smtp_server, self.smtp_port, timeout=self.timeout) as server:
                    if not self.use_ssl and self.use_tls:
                        server.ehlo()
                        server.starttls()
                        server.ehlo()
                    
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg)
                
                logger.info(f"✅ 邮件发送成功: {to_email}")
                return True, f"邮件已发送到 {to_email}"
            
            except smtplib.SMTPAuthenticationError:
                error_msg = "SMTP认证失败：请检查邮箱与授权码（QQ邮箱需启用SMTP并使用授权码）"
                logger.error(error_msg)
                return False, error_msg
            
            except smtplib.SMTPServerDisconnected as e:
                # 某些服务商在DATA后断开，实际已投递。无法准确判断已投递与否，这里按失败处理。
                error_msg = f"SMTP连接断开: {str(e)}"
                if attempt < attempts:
                    logger.warning(f"⚠️ {error_msg}，{attempt}秒后重试...")
                    time.sleep(attempt)
                else:
                    logger.error(f"❌ 第{attempts}次尝试后仍失败: {error_msg}")
                    return False, error_msg
            
            except smtplib.SMTPException as e:
                error_msg = f"SMTP错误: {str(e)}"
                if attempt < attempts:
                    logger.warning(f"⚠️ {error_msg}，{attempt}秒后重试...")
                    time.sleep(attempt)
                else:
                    logger.error(f"❌ 第{attempts}次尝试后仍失败: {error_msg}")
                    return False, error_msg
            
            except Exception as e:
                error_msg = f"发送邮件失败: {str(e)}"
                if attempt < attempts:
                    logger.warning(f"⚠️ {error_msg}，{attempt}秒后重试...")
                    time.sleep(attempt)
                else:
                    logger.error(f"❌ 第{attempts}次尝试后仍失败: {error_msg}")
                    return False, error_msg
        
        return False, "邮件发送失败"
    
    def send_batch_emails(self, recipients: List[str], subject: str, 
                         html_content: str, plain_content: Optional[str] = None,
                         delay: float = 1.0, max_retries: Optional[int] = None) -> Dict[str, any]:
        """
        批量发送邮件
        
        Args:
            recipients: 收件人列表
            subject: 邮件主题
            html_content: HTML内容
            plain_content: 纯文本内容
            delay: 每封邮件间隔（秒）
            max_retries: 覆盖批量发送中每封邮件的重试次数（默认None=使用EmailSender默认）
        
        Returns:
            统计信息字典
        """
        logger.info(f"开始批量发送邮件给 {len(recipients)} 位收件人...")
        
        stats = {
            'total': len(recipients),
            'success': 0,
            'failed': 0,
            'failed_recipients': [],
            'failed_reasons': {}
        }
        
        for i, recipient in enumerate(recipients, 1):
            logger.info(f"发送第 {i}/{len(recipients)} 封邮件: {recipient}")
            
            success, message = self.send_email(
                recipient, subject, html_content, plain_content, max_retries=max_retries
            )
            
            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1
                stats['failed_recipients'].append(recipient)
                stats['failed_reasons'][recipient] = message
            
            # 避免被识别为垃圾邮件，邮件间隔
            if i < len(recipients):
                time.sleep(delay)
        
        logger.info(f"批量发送完成: 成功{stats['success']}, 失败{stats['failed']}")
        
        return stats
