# -*- coding: utf-8 -*-
{
    'name': "Point of Sale Forlife",

    'summary': """Point of Sale Forlife
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Point of Sale Point Order',

    'depends': [
        'point_of_sale',
        'forlife_point_of_sale',
        'forlife_pos_app_member',
        'forlife_promotion',
        'base'
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/cron_job_data.xml',
        'wizards/compensate_point_wizard_view.xml',
        'views/pos_order.xml',
        'views/res_partner_view.xml',
        'views/account_move.xml'
    ],
    'installable': True,
    'application': True,
    # 'assets': {
    # }
}
