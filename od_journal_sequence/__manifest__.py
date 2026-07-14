# -*- coding: utf-8 -*-

{
    'name': 'DSN Journal Sequence For Odoo 16',
    'version': '16.0',
    'category': 'Accounting',
    'summary': 'Journal Sequence For Odoo 16',
    'description': 'Journal Sequence For Odoo 16',
    'sequence': '1',
    'author': 'DSN DEV',
    'support': 'dev@dsnusantara.com',
    # 'live_test_url': 'https://www.youtube.com/watch?v=z-xZwCah7wM',
    'depends': ['account'],
    'demo': [],
    'data': [
        'data/account_data.xml',
        'views/account_journal.xml',
        'views/account_move.xml',
    ],
    'qweb': [],
    'license': 'OPL-1',
    # 'price': 13,
    # 'currency': 'USD',
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
