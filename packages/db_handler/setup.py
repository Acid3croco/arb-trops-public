from setuptools import setup, find_packages

setup(
    name='db_handler',
    author='arb',
    author_email='arb.trops@gmail.com',
    description='db_handler de ouf',
    version='2.0.0',
    packages=find_packages(),
    install_requires=['arb_logger', 'arb_defines'],
    entry_points={
        'console_scripts': [
            'db_handler = db_handler.db_handler:main',
            'start_db = db_handler.start_db:main',
            'stop_db = db_handler.stop_db:main',
        ]
    },
)
