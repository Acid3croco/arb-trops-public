from setuptools import setup, find_packages

setup(
    name='standalone_tools',
    author='arb',
    author_email='arb.trops@gmail.com',
    description='standalone_tools de ouf',
    version='1.0.9',
    packages=find_packages(),
    install_requires=[
        'arb_logger', 'arb_defines', 'db_handler', 'redis_manager'
    ],
    entry_points={
        'console_scripts': [
            'smb = standalone_tools.show_book:main',
            'exch = standalone_tools.show_exchanges:main',
            'instr = standalone_tools.show_instruments:main',
            'bal = standalone_tools.show_balances:main',
            'pos = standalone_tools.show_positions:main',
            'fundings = standalone_tools.show_fundings:main',
            'fr_spreads = standalone_tools.funding_spreads:main',
            'liq = standalone_tools.show_liquidations:main',
            'trades = standalone_tools.show_trades:main',
            'orders = standalone_tools.show_orders:main',
            'arb_notification_server = standalone_tools.arb_notification_server:main',
            'reload_data_api = standalone_tools.reload_data_api:main',
            'script_reloader = standalone_tools.script_reloader:main',
            'mermaid_uml_generator = standalone_tools.mermaid_uml_generator:main',
        ]
    },
)
