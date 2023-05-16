# -*- coding: utf-8 -*-
{
    'name': "ForLife Product Combo",
    'summary': """
        """,
    'description': """
    """,
    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',
    'category': 'Sales/Point of Sale',
    'installable': True,
    'auto_install': True,
    'depends': [
        'point_of_sale',
    ],
    'data': [
        # Views
        'views/product_combo_views.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
    ],
}
