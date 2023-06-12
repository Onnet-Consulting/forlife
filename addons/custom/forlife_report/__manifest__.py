# -*- coding: utf-8 -*-
{
    'name': "ForLife Reports",

    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",

    'category': 'Generic Modules',
    'version': '16.0.1.0.0',

    'depends': [
        'base',
        'web',
        'stock',
        'report_xlsx',
        'forlife_base',
        'forlife_point_of_sale',
        'forlife_customer_card_rank',
        'forlife_pos_product_change_refund'
    ],

    'data': [
        'security/ir.model.access.csv',

        'data/attribute_code_config_data.xml',

        'views/attribute_code_config_views.xml',

        'wizard/report_base_actions.xml',
        'wizard/report_base_views.xml',
        'wizard/report_num1_views.xml',
        'wizard/report_num2_views.xml',
        'wizard/report_num3_views.xml',
        'wizard/report_num4_views.xml',
        'wizard/report_num5_views.xml',
        'wizard/report_num6_views.xml',
        'wizard/report_num7_views.xml',
        'wizard/report_num8_views.xml',
        'wizard/report_num9_views.xml',
        'wizard/report_num10_views.xml',
        'wizard/report_num11_views.xml',
        'wizard/report_num12_views.xml',
        'wizard/report_num13_views.xml',
        'wizard/report_num14_views.xml',
        'wizard/report_num15_views.xml',
        'wizard/report_num16_views.xml',
        'wizard/report_num17_views.xml',
        'wizard/report_num18_views.xml',
        'wizard/report_num19_views.xml',
        'wizard/report_num20_views.xml',
        'wizard/report_num21_views.xml',
        'wizard/report_num22_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'forlife_report/static/src/xml/**/*',
            'forlife_report/static/src/css/**/*',
            'forlife_report/static/src/js/**/*',
        ]
    }
}
