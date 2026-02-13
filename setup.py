"""Setup script for Ramses Out."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ramses-out",
    version="0.1.0",
    author="Overmind Studios",
    description="Preview collection, review preparation, and delivery tool for Ramses pipeline",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "PySide6>=6.4.0",
    ],
    entry_points={
        "console_scripts": [
            "ramses-out=ramses_out.gui:main",
        ],
        "gui_scripts": [
            "ramses-out-gui=ramses_out.gui:main",
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
