# -*- coding: utf-8 -*-
{   
    'name': "DSN Approval",
    'summary': "Base Approval Module by Delta Solusi Nusantara",
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
        'base', 'hr', 'mail'
    ],

    # always loaded
    'data': [
        'security/approval_security.xml',
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/dsn_hr_employee_views.xml',
    ],
    
}
