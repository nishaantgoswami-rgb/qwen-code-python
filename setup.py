"""
Setup configuration for Qwen Code.
"""

from setuptools import setup, find_packages


setup(
    name="qwen-code",
    version="2.0.0",
    description="AI-powered coding assistant CLI tool",
    long_description=open("README.md").read() if open("README.md").read() else "Qwen Code - AI-powered coding assistant",
    long_description_content_type="text/markdown",
    author="Qwen Team",
    author_email="qwen@alibabacloud.com",
    url="https://github.com/QwenLM/qwen-code-python",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
        "pyyaml>=5.4.0",
        "rich>=10.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-asyncio>=0.15.0",
            "black>=21.0.0",
            "flake8>=3.9.0",
            "mypy>=0.910",
        ],
        "test": [
            "pytest>=6.0.0",
            "pytest-asyncio>=0.15.0",
            "pytest-cov>=2.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "qwen=qwen_code.cli.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    include_package_data=True,
)