# -*- coding: utf-8 -*-
{
    'name': "Vourcher",

    'summary': """
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Vourcher/Point of Sale',

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
        'views/program_vourcher.xml',
        'views/setup_vourcher.xml',
        'views/vourcher_view.xml',
        'views/menu_views.xml',
        'views/product_template.xml'
    ]
}
