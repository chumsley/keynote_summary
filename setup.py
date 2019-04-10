from setuptools import setup, find_packages
from os import path
from io import open

# Get the long description from the README file
here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="keynote_summary",
    version='0.5',
    author="James Wright",
    author_email="james@chumsley.org",
    description="Output a markdown-formatted summary of the slides in a Keynote file",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/chumsley/keynote_summary",
    # packages=find_packages(),
    packages=['keynote_summary'],
    scripts=['scripts/keynote_summary'],
    classifiers=[
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=['keynote_parser']
)
