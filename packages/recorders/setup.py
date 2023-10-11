from setuptools import setup, find_packages

setup(
    name='recorders',
    author='arb',
    author_email='arb.trops@gmail.com',
    description='recorders de ouf',
    version='3.1.0',
    packages=find_packages(),
    install_requires=[
        'arb_logger', 'arb_defines', 'db_handler', 'redis_manager'
    ],
    entry_points={
        'console_scripts': [
            'trades_reader = recorders.trades_reader:main',
            'trades_recorder = recorders.trades_recorder:main',
            'funding_reader = recorders.funding_reader:main',
            'funding_recorder = recorders.funding_recorder:main',
            'l2_book_reader = recorders.l2_book_reader:main',
            'l2_book_recorder = recorders.l2_book_recorder:main',
            'clean_records = recorders.clean_records:main',
            'fold_records = recorders.fold_records:main',
        ]
    },
)
