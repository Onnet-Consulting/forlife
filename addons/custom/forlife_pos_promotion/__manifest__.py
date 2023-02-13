# -*- coding: utf-8 -*-
{
    'name': "POS Promotion Program",

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
        'point_of_sale',
        'forlife_point_of_sale',
        'forlife_promotion'
    ],
    'assets': {
        'web.assets_backend': [
            'forlife_pos_promotion/static/src/js/**/*',
        ],
    },

    'data': [
        # Security
        'security/ir.model.access.csv',
        # Wizards
        'wizards/promotion_generate_code_views.xml',
        # View
        'views/promotion_program_views.xml',
        'views/promotion_combo_line_views.xml',
        'views/promotion_code_views.xml',
        # Menu
        'menu/menu_views.xml',
    ]
}
