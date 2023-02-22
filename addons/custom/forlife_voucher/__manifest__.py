# -*- coding: utf-8 -*-
{
    'name': "Voucher",

    'summary': """
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Voucher/Point of Sale',

    'depends': [
        'base',
        'hr',
        'purchase',
        'sale',
        'analytic',
        'forlife_point_of_sale',
        'forlife_promotion'
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/program_voucher.xml',
        'views/setup_voucher.xml',
        'views/voucher_view.xml',
        'views/menu_views.xml',
        'views/product_template.xml',
        'data/ir_sequence.xml',
        'data/ir_cron.xml'
    ]
}
