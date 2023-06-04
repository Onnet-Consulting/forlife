# -*- coding: utf-8 -*-
{
    'name': "forlife_pos_app_member",

    'summary': """""",
    "license": "LGPL-3",
    'description': """
    """,

    'author': "ForLife",
    'website': "",

    'category': 'Sales/Point Of Sale',
    'version': '1.0',

    'depends': [
        'point_of_sale',
        'contacts',
        'forlife_point_of_sale',
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/res_partner_group.xml',
        'data/res_partner.xml',
        'data/ir_fields.xml',
        'data/res_partner_retail.xml',
        'data/hr_data.xml',
        'data/barcode_rule.xml',
        'wizard/create_warehouse_partner_views.xml',
        'views/res_partner_group_views.xml',
        'views/res_partner_job_views.xml',
        'views/res_partner_views.xml',
        'views/res_partner_retail_views.xml',
        'views/stock_warehouse_views.xml',
        'views/hr_employee_views.xml',
        'views/res_users_views.xml',
    ],
    'external_dependencies': {
        'python': ['phonenumbers'],
    },
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_app_member/static/src/js/**/*.js',
            'forlife_pos_app_member/static/src/xml/**/*.xml',
        ]
    }
}
