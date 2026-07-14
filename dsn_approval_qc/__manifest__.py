# -*- coding: utf-8 -*-
{   
    'name': "DSN Approval Quality Check",
    'summary': "Approval Modul for Quality Check by Delta Solusi Nusantara",
    'description': """
        v1.0.0
        By: DSN Team
    """,
    'author': "Delta Solusi Nusantara",
    'website': "www.dsnusantara.com",
    'version': '16.0.1.0.0', 
    'sequence': 0,
    "auto_install": False,
    "installable": True,
    "application": True,
    "license": "OPL-1",

    # any module necessary for this one to work correctly
    'depends': [
        'dsn_approval', 'quality', 'quality_control',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/dsn_approval_qc_views.xml',
    ],
    
}
