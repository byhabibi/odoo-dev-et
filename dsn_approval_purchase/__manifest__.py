# -*- coding: utf-8 -*-
{   
    'name': "DSN Approval Purchase",
    'summary': "Approval Modul for Purchase by Delta Solusi Nusantara",
    'description': """
        1. Implementasi approval pada dokumen Vendor Pricelist.
        2. Implementasi approval pada dokumen Purchase Order.
        3. Implementasi approval pada dokumen Purchase Request.
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
        'dsn_approval', 'purchase', 'purchase_request'
    ],

    # always loaded
    'data': [
        'security/approval_security.xml',
        'security/ir.model.access.csv',
        'views/dsn_approval_purchase_views.xml',
        'views/dsn_purchase_request_views.xml',
        'views/dsn_purchase_order_views.xml',
        'views/dsn_product_supplierinfo_views.xml',
        'views/menu.xml',
    ],
    
}
