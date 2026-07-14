{
    'name': 'DSN Sequence Setting',
    'summary': "Product DSN Sequences Setting",
    'description': """
        v1.0.0
        By: DSN Team
    """,
    'author': "Delta Solusi Nusantara",
    'website': "www.dsnusantara.com",
    'version': '16.0.1.0.0', 
    'data': [
        #security
        'security/ir.model.access.csv',
        
        #views
        'views/sales_sequences_views.xml',
        'views/purchase_sequences_views.xml',
        'views/manufacture_sequences_views.xml',
        'views/account_move_sequences_views.xml',
        'views/inventory_operation_sequences_views.xml',
        'views/account_journal.xml',

        'views/dsn_sequence_setting_menu.xml',
    ],
    'depends': ['base', 'sale', 'purchase', 'mrp', 'account', 'purchase_request', 'stock'],
    'auto_install': False,
    'installable': True,
    'application': False,
    'license': 'OEEL-1',

}