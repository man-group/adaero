# Always prefer setuptools over distutils
from setuptools import setup, find_packages

from os import path

here = path.abspath(path.dirname(__file__))

description = 'A platform for managing peer-to-peer feedback within an organisation.'

def readme():
    try:
        with open('README.md') as f:
            return f.read()
    except FileNotFoundError:
        return ""

setup(
    name='feedback_tool',

    version='1.0.0',

    description=description,
    long_description=readme(),
    long_description_content_type='text/markdown',
    # The project's main homepage.
    url='https://github.com/manahl/feedback_tool',
    download_url='https://github.com/manahl/feedback_tool/archive/v1.0.0.tar.gz',

    # Author details
    author='MAN Alpha Tech',
    author_email='ManAlphaTech@man.com',

    # Choose your license
    license='GPL 2.0',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 2.7',
    ],

    # What does your project relate to?
    keywords='feedback',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    #   py_modules=["my_module"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'pyramid',
        'pyramid-beaker',
        'waitress',
        'python-ldap',
        'pyramid_tm',
        'SQLAlchemy',
        'transaction',
        'zope.sqlalchemy',
        'pycrypto',
        'rest_toolkit',
        'python-dateutil',
        'apscheduler',
        'Paste',
        'beautifulsoup4',
        'lxml',
        'pytz',
        'alembic',
        'unicodecsv',
        'jinja2',
        'click',
        'pandas',
        'gunicorn',
        'psycopg2-binary'
    ],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'test': [
            'pytest',
            'pytest-cov',
            'mock',
            'python-dateutil',
            'WebTest',
            'faker',
            'click',
            'freezegun',
            'pytest-xdist',
            'tox'
        ],
        'oracle': [
            'cx_Oracle'
        ],
        'postgres': [
            'psycopg2'
        ]
    },

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'feedback_tool=feedback_tool.scripts.feedback_app:main',
            'configure_db=feedback_tool.scripts.configure_db:cli',
        ],
        'paste.app_factory': [
            'main = feedback_tool:main'
        ]
    },
)
