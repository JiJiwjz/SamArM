"""
配置管理模块
负责加载、验证和管理所有配置信息
"""

import os
import yaml
from dotenv import load_dotenv
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器 - 统一管理所有配置项"""
    
    _instance = None
    _config = {}
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化配置管理器"""
        if not self._config:
            self._load_config()
    
    def _load_config(self):
        """加载所有配置"""
        # 1. 加载环境变量
        load_dotenv('.env')
        
        # 2. 加载YAML配置文件
        config_file = 'config.yaml'
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f) or {}
                self._config = self._merge_configs(yaml_config)
        else:
            logger.warning(f"配置文件 {config_file} 不存在，使用环境变量配置")
            self._config = self._load_from_env()
        
        self._validate_config()
        logger.info("配置加载完成")
    
    def _load_from_env(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        return {
            'arxiv': {
                'keywords': os.getenv('ARXIV_KEYWORDS', '').split('|'),
                'categories': os.getenv('ARXIV_CATEGORIES', 'cs.CV,cs.AI,cs.LG').split(','),
                'max_results': int(os.getenv('ARXIV_MAX_RESULTS', 50)),
                'sort_by': os.getenv('ARXIV_SORT_BY', 'submittedDate'),
            },
            'deepseek': {
                'api_key': os.getenv('DEEPSEEK_API_KEY'),
                'api_url': os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1'),
                'model': os.getenv('DEEPSEEK_MODEL', 'deepseek-chat'),
                'timeout': int(os.getenv('DEEPSEEK_TIMEOUT', 30)),
            },
            'email': {
                'sender_email': os.getenv('SENDER_EMAIL'),
                'sender_password': os.getenv('SENDER_PASSWORD'),
                'smtp_server': os.getenv('SMTP_SERVER'),
                'smtp_port': int(os.getenv('SMTP_PORT', 587)),
                'recipients': os.getenv('RECIPIENT_EMAILS', '').split('|'),
            },
            'scheduler': {
                'execute_time': os.getenv('SCHEDULER_TIME', '09:00'),
                'frequency': os.getenv('SCHEDULER_FREQUENCY', 'daily'),
            },
            'logging': {
                'level': os.getenv('LOG_LEVEL', 'INFO'),
                'file': os.getenv('LOG_FILE', 'logs/arxiv_mailbot.log'),
            },
            'storage': {
                'data_dir': os.getenv('DATA_DIR', 'data'),
                'format': os.getenv('DATA_FORMAT', 'json'),
            }
        }
    
    def _merge_configs(self, yaml_config: Dict) -> Dict:
        """合并YAML配置和环境变量，环境变量优先级更高"""
        env_config = self._load_from_env()
        
        # 环境变量中的值覆盖YAML配置
        for key, value in env_config.items():
            if key in yaml_config:
                if isinstance(value, dict):
                    yaml_config[key].update(value)
                else:
                    yaml_config[key] = value
            else:
                yaml_config[key] = value
        
        return yaml_config
    
    def _validate_config(self):
        """验证关键配置项"""
        # 检查必要的配置
        if not self.get('deepseek.api_key'):
            logger.warning("警告：未设置DEEPSEEK_API_KEY")
        
        if not self.get('email.sender_email'):
            logger.warning("警告：未设置SENDER_EMAIL")
        
        # 检查arxiv关键词
        keywords = self.get('arxiv.keywords', [])
        if not keywords or all(not k.strip() for k in keywords):
            logger.warning("警告：未设置arxiv搜索关键词")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号路径
        例如：get('arxiv.keywords') 获取 config['arxiv']['keywords']
        
        Args:
            key_path: 点号分隔的配置路径
            default: 默认值
        
        Returns:
            配置值或默认值
        """
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """
        设置配置值
        
        Args:
            key_path: 点号分隔的配置路径
            value: 要设置的值
        """
        keys = key_path.split('.')
        config = self._config
        
        # 创建嵌套字典
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        logger.debug(f"配置已更新: {key_path} = {value}")
    
    def get_arxiv_config(self) -> Dict[str, Any]:
        """获取arxiv爬取配置"""
        return self.get('arxiv', {})
    
    def get_deepseek_config(self) -> Dict[str, Any]:
        """获取DeepSeek API配置"""
        return self.get('deepseek', {})
    
    def get_email_config(self) -> Dict[str, Any]:
        """获取邮件配置"""
        return self.get('email', {})
    
    def get_scheduler_config(self) -> Dict[str, Any]:
        """获取调度配置"""
        return self.get('scheduler', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.get('logging', {})
    
    def get_storage_config(self) -> Dict[str, Any]:
        """获取存储配置"""
        return self.get('storage', {})
    
    def display_config(self):
        """打印配置信息（隐藏敏感信息）"""
        config_copy = dict(self._config)
        
        # 隐藏敏感信息
        if 'deepseek' in config_copy:
            config_copy['deepseek']['api_key'] = '***HIDDEN***'
        if 'email' in config_copy:
            config_copy['email']['sender_password'] = '***HIDDEN***'
        
        logger.info(f"当前配置：\n{yaml.dump(config_copy, allow_unicode=True)}")


# 全局配置管理器实例
config_manager = ConfigManager()


if __name__ == '__main__':
    # 测试配置管理器
    config = ConfigManager()
    print("arxiv关键词:", config.get('arxiv.keywords'))
    print("DeepSeek模型:", config.get('deepseek.model'))
    print("邮件SMTP服务器:", config.get('email.smtp_server'))
