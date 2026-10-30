"""
Setup script for the WildGuard Framework.

Install the framework as a package:
    pip install -e .

Then run from anywhere:
    python -m wildguard_framework.main
"""

from setuptools import setup, find_packages

setup(
    name="wildguard-framework",
    version="2.0.0",
    description="Decision-Support Framework for Deploying Microservice-based IoT Systems",
    author="Fahed Alkhabbas, Romina Spalazzese, Paul Davidsson",
    packages=find_packages(),
    package_data={"": ["scenarios/*.json"]},
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "ortools>=9.8",
        "matplotlib>=3.5",
    ],
    entry_points={
        "console_scripts": [
            "wildguard-deploy=wildguard_framework.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Distributed Computing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
