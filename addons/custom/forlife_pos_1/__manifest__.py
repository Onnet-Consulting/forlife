# -*- coding: utf-8 -*-
{
    'name': "forlife_pos_1",

    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",

    'category': 'Point of Sale',
    'version': '1.0',

    'depends': [
        'point_of_sale',
        'contacts',
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/res_partner_group.xml',
        'views/res_partner_group_views.xml',
        'views/res_partner_job_views.xml',
        'views/res_partner_views.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],
}
