# -*- coding: utf-8 -*-
{
    'name': "POS Model Cache",
    'summary': """
    """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Sales/Point of Sale',

    'depends': [
        'pos_cache',
        # TODO: make another module to inherit this ..... i'm in a rush here :shame:
        'forlife_pos_promotion',

    ],
    'data': [
        'security/ir.model.access.csv',
        'data/pos_model_cache_data.xml',
    ]
}
