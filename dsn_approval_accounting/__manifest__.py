# -*- coding: utf-8 -*-
{   
    'name': "DSN Approval Accounting",

    'summary': "Approval Module for Accounting by Delta Solusi Nusantara",
    'description': """
        1. Approval terjadi pada dokumen journal entry.
        2. Approval hanya untuk dokumen journal entry yang dibuat secara manual.
        3. Untuk dokumen journal entry yang terbentuk melalui serangkaian proses maka tidak akan diberlakukan approval.
        v1.0.0
        By: DSN Team
    """,
    'author': "Delta Solusi Nusantara",
    'website': "www.dsnusantara.com",
    'version': '16.0.1.0.0', 
    'sequence': 1,
    "auto_install": False,
    "installable": True,
    "application": True,
    "license": "OPL-1",

    # any module necessary for this one to work correctly
    'depends': [
        'dsn_approval', 'account'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/dsn_approval_accounting_views.xml',
        'views/dsn_account_move_views.xml',
        'views/menu.xml',
    ],
    
}
