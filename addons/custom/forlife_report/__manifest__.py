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
        'forlife_stock',
        'purchase_request',
        'forlife_promotion',
        'forlife_point_of_sale',
        'forlife_customer_card_rank',
        'forlife_pos_product_change_refund',
        'forlife_business_objective_plan',
    ],

    'data': [
        'security/res_group_security.xml',
        'security/ir.model.access.csv',

        'wizard/report_base_actions.xml',
        'wizard/report_base_views.xml',
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
        'wizard/report_num23_views.xml',
        'wizard/report_num24_views.xml',
        'wizard/report_num25_views.xml',
        'wizard/report_num26.xml',
        'wizard/report_num27.xml',
        'wizard/report_num28.xml',
        'wizard/report_num29.xml',
        'wizard/report_num30_views.xml',
        'wizard/report_num31.xml',
        'wizard/report_num32.xml',
        'wizard/report_num33.xml',
        'wizard/report_num34_views.xml',
        'wizard/report_num35_views.xml',
        'wizard/report_num36.xml',
        'wizard/report_num37.xml',
        'wizard/report_num38.xml',
        'wizard/report_num39_views.xml',

        'report/report_paperformat.xml',
        'report/print_purchase_request.xml',
        'report/print_purchase_order.xml',
        'report/print_stock_transfer_ingoing.xml',
        'report/print_stock_transfer_outgoing.xml',
        'report/print_stock_picking_ingoing.xml',
        'report/print_stock_picking_outgoing.xml',

        'views/attribute_code_config_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_request_views.xml',
        'views/stock_transfer_views.xml',
        'views/stock_picking_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'forlife_report/static/src/xml/**/*',
            'forlife_report/static/src/css/**/*',
            'forlife_report/static/src/js/**/*',
        ]
    }
}
