# -*- coding: utf-8 -*-
{
    'name': "ForLife Print Stamps Barcode",
    'summary': """
        """,
    'description': """
    """,
    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',
    'category': 'Hidden/Tools',
    'installable': True,
    'auto_install': True,
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',

        'report/print_stamps_barcode_report.xml',
        'views/print_stamps_barcode_views.xml',
    ],
}
