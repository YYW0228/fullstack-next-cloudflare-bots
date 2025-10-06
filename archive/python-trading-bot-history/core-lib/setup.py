"""
反向跟单机器人核心库安装配置

这是整个反向跟单生态系统的基础库，包含所有共享组件。
"""

from setuptools import setup, find_packages
import os

# 读取README文件
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "反向跟单机器人核心库"

# 读取requirements
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="reverse-trading-core",
    version="1.0.0",
    description="反向跟单机器人核心库 - 智慧交易的基础架构",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="RovoDev Team",
    author_email="dev@rovodev.com",
    url="https://github.com/rovodev/reverse-trading-core",
    
    # 包配置
    packages=find_packages(),
    include_package_data=True,
    
    # Python版本要求
    python_requires=">=3.8",
    
    # 依赖管理
    install_requires=[
        "ccxt>=4.1.87",           # 交易所接口
        "telethon>=1.32.1",       # Telegram客户端
        "nest-asyncio>=1.5.8",    # 异步支持
        "pytz>=2023.3",           # 时区处理
        "typing-extensions>=4.0.0", # 类型注解扩展
    ],
    
    # 可选依赖
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'pytest-cov>=4.0.0',
            'black>=22.0.0',
            'flake8>=5.0.0',
            'mypy>=1.0.0',
        ],
        'monitoring': [
            'prometheus-client>=0.15.0',
            'grafana-api>=1.0.0',
        ]
    },
    
    # 包分类
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Framework :: AsyncIO",
    ],
    
    # 关键词
    keywords="trading, cryptocurrency, reverse-trading, quantitative, bot, finance",
    
    # 项目链接
    project_urls={
        'Documentation': 'https://docs.rovodev.com/reverse-trading',
        'Source': 'https://github.com/rovodev/reverse-trading-core',
        'Tracker': 'https://github.com/rovodev/reverse-trading-core/issues',
    },
)