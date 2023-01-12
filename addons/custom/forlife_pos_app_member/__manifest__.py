# -*- coding: utf-8 -*-
{
    'name': "forlife_pos_app_member",

    'summary': """""",

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
        'views/res_partner_group_views.xml',
        'views/res_partner_job_views.xml',
        'views/res_partner_views.xml',
        'views/res_partner_retail_views.xml',
        'views/stock_warehouse_views.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],
    'external_dependencies': {
        'python': ['phonenumbers'],
    },
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_app_member/static/src/js/**/*.js',
            'forlife_pos_app_member/static/src/xml/**/*.xml',
        ]
    },
    'post_init_hook': '_update_required_attribute_for_fields',
}
