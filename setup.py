"""Setup script for Ramses Review."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ramses-review",
    version="0.1.0",
    author="Overmind Studios",
    description="Preview collection and review preparation tool for Ramses pipeline",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "PySide6>=6.4.0",
    ],
    entry_points={
        "console_scripts": [
            "ramses-review=ramses_review.gui:main",
        ],
        "gui_scripts": [
            "ramses-review-gui=ramses_review.gui:main",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
