# -*- coding: utf-8 -*-
{
    'name': "Generate Product Forlife Customize",

    'summary': """
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Product/Forlife',

    'depends': [
        'base',
        'product',
        'stock',
        'forlife_point_of_sale'
    ],

    'data': [
        'data/ir_sequence.xml',
        'security/ir.model.access.csv',
        'views/generate_product.xml',
        'views/menu_view.xml'
    ]
}
