# OSINT Framework Requirements - No External API Keys Required
# This version removes all dependencies that require external API keys
# and focuses on local processing, web scraping, and open-source intelligence

# Core Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
jinja2==3.1.2
python-multipart==0.0.6

# Database and Storage
sqlalchemy==2.0.23
alembic==1.12.1
sqlite3  # Built-in Python module

# Web Scraping and HTTP Requests
aiohttp==3.9.1
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
selenium==4.15.2
playwright==1.40.0
scrapy==2.11.0

# HTML and XML Processing
html5lib==1.1
pyquery==2.0.0
lxml-html-clean==0.2.1

# Text Processing and NLP (Local Only)
nltk==3.8.1
spacy==3.7.2
textblob==0.17.1
gensim==4.3.2
wordcloud==1.9.2

# Data Processing and Analysis
pandas==2.1.3
numpy==1.25.2
scipy==1.11.4
scikit-learn==1.3.2

# Machine Learning (Local Models Only)
tensorflow==2.15.0
torch==2.1.1
transformers==4.35.2
sentence-transformers==2.2.2

# Computer Vision (Local Processing)
opencv-python==4.8.1.78
pillow==10.1.0
face-recognition==1.3.0
pytesseract==0.3.10

# Network and Security Analysis
networkx==3.2.1
cryptography==41.0.7
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
dnspython==2.4.2
whois==0.9.27

# Data Validation and Serialization
pydantic==2.5.0
email-validator==2.1.0
phonenumbers==8.13.25
python-dateutil==2.8.2
pytz==2023.3

# Caching and Performance
aiofiles==23.2.1
diskcache==5.6.3
cachetools==5.3.2

# Configuration and Environment
python-dotenv==1.0.0
pyyaml==6.0.1
toml==0.10.2

# Logging and Monitoring (Local Only)
structlog==23.2.0
rich==13.7.0
click==8.1.7

# Testing and Development
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.11.0
flake8==6.1.0
mypy==1.7.1

# Documentation
mkdocs==1.5.3
mkdocs-material==9.4.8

# Utilities
tqdm==4.66.1
click==8.1.7
python-slugify==8.0.1
user-agents==2.2.0

# File Processing
openpyxl==3.1.2
python-docx==1.1.0
pypdf2==3.0.1
python-pptx==0.6.23

# Image Processing (Local Only)
pillow==10.1.0
opencv-python==4.8.1.78
imagehash==4.3.1

# Audio/Video Processing (Local Only)
moviepy==1.0.3
pydub==0.25.1

# Geospatial Analysis (Local Data Only)
geopy==2.4.1
shapely==2.0.2

# Time Series Analysis
prophet==1.1.5

# Report Generation (Local Only)
matplotlib==3.8.2
seaborn==0.13.0
plotly==5.17.0
jinja2==3.1.2
weasyprint==60.2
reportlab==4.0.7

# Data Export
xlsxwriter==3.1.9
csv  # Built-in Python module
json  # Built-in Python module

# Async Utilities
asyncio  # Built-in Python module
concurrent.futures  # Built-in Python module

# System Monitoring
psutil==5.9.6
memory-profiler==0.61.0

# URL and Domain Analysis
urllib3==2.1.0
tldextract==5.0.1
publicsuffix2==2.20191221

# Email Processing
email-validator==2.1.0
email  # Built-in Python module

# Phone Number Processing
phonenumbers==8.13.25

# Name and Entity Processing
nameparser==1.1.3
dedupe==1.15.0

# Text Similarity and Matching
fuzzywuzzy==0.18.0
python-levenshtein==0.23.0
difflib  # Built-in Python module

# Pattern Recognition
regex==2023.10.3
pyparsing==3.1.1

# Data Cleaning
pyjanitor==0.24.1
dataprep==0.4.5

# Statistical Analysis
statsmodels==0.14.0

# Graph Visualization
pyvis==0.3.2

# Web Archive and History
waybackpy==3.0.4

# Social Media Analysis (Public Data Only)
tweepy  # For public Twitter data only
instaloader  # For public Instagram data only

# Code Analysis (Public Repositories Only)
gitpython==3.1.40
github3.py  # For public GitHub data only

# Dark Web Analysis (Local Tools Only)
torpy==0.4.0

# OSINT Specific Tools
maltego  # Local Maltego integration
theharvester  # Public email harvesting
recon-ng  # Web reconnaissance framework
sherlock  # Username search across platforms
social-analyzer  # Social media analysis

# Browser Automation
undetected-chromedriver==3.5.4
selenium-stealth==1.0.6

# Proxy and Anonymization
proxy-tools==0.2.0
socks==1.7.1

# Data Enrichment (Local Only)
countryinfo==0.1.3
pycountry==23.12.7

# Hashing and Encryption
hashlib  # Built-in Python module
cryptography==41.0.7

# Regular Expressions
regex==2023.10.3
re  # Built-in Python module

# Date and Time Processing
datetime  # Built-in Python module
python-dateutil==2.8.2

# File System Operations
pathlib  # Built-in Python module
os  # Built-in Python module
shutil  # Built-in Python module

# JSON and XML Processing
json  # Built-in Python module
xml.etree.ElementTree  # Built-in Python module
xmltodict==0.13.0

# HTTP Client Libraries
httpx==0.25.2
aiohttp==3.9.1

# Browser Engine
playwright==1.40.0
selenium==4.15.2

# Data Compression
gzip  # Built-in Python module
zlib  # Built-in Python module
bz2  # Built-in Python module

# Base64 and Encoding
base64  # Built-in Python module
binascii  # Built-in Python module

# UUID Generation
uuid  # Built-in Python module

# Random Number Generation
random  # Built-in Python module
secrets  # Built-in Python module

# Mathematical Operations
math  # Built-in Python module
statistics  # Built-in Python module

# Threading and Concurrency
threading  # Built-in Python module
multiprocessing  # Built-in Python module
concurrent.futures  # Built-in Python module

# Error Handling and Debugging
traceback  # Built-in Python module
inspect  # Built-in Python module

# Type Hints
typing  # Built-in Python module
typing_extensions==4.8.0

# Data Classes
dataclasses  # Built-in Python module (Python 3.7+)

# Context Managers
contextlib  # Built-in Python module

# Iteration Tools
itertools  # Built-in Python module
functools  # Built-in Python module

# Collection Utilities
collections  # Built-in Python module
heapq  # Built-in Python module

# String Operations
string  # Built-in Python module
textwrap  # Built-in Python module

# Number Operations
decimal  # Built-in Python module
fractions  # Built-in Python module

# File Format Support
csv  # Built-in Python module
configparser  # Built-in Python module
argparse  # Built-in Python module

# System Information
platform  # Built-in Python module
sys  # Built-in Python module
os  # Built-in Python module

# Time Operations
time  # Built-in Python module
calendar  # Built-in Python module

# Network Operations
socket  # Built-in Python module
urllib.parse  # Built-in Python module
urllib.request  # Built-in Python module
http.client  # Built-in Python module

# Process Management
subprocess  # Built-in Python module
shlex  # Built-in Python module

# Signal Handling
signal  # Built-in Python module

# Temporary Files
tempfile  # Built-in Python module

# Environment Variables
os.environ  # Built-in Python module

# Command Line Arguments
sys.argv  # Built-in Python module
argparse  # Built-in Python module

# Logging
logging  # Built-in Python module

# Testing Framework
unittest  # Built-in Python module

# Performance Profiling
cProfile  # Built-in Python module
profile  # Built-in Python module

# Memory Management
gc  # Built-in Python module
weakref  # Built-in Python module

# Serialization
pickle  # Built-in Python module
marshal  # Built-in Python module
