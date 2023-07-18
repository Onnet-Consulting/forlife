# -*- coding: utf-8 -*-
{
    'name': "POS Product Change",

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
        'forlife_pos_promotion',
        'forlife_point_of_sale',
        'forlife_pos_point_order',
        'forlife_voucher',
        'forlife_pos_assign_employee',
        'forlife_pos_layout',
        'forlife_pos_accounting'
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_product_change_refund/static/src/scss/pos.scss',
            'forlife_pos_product_change_refund/static/src/xml/**/*.xml',
            'forlife_pos_product_change_refund/static/src/js/**/*.js',
        ],
    },

    'data': [
        # Security
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        # Wizards
        'wirards/reason_refuse.xml',
        # View
        'views/pos_order_line_views.xml',
        'views/handle_change_refund_views.xml',
        'views/store_views.xml',
        'views/pos_order_views.xml',
        'views/product_template_views.xml',
        'views/pos_reason_refund.xml',
        'views/product_category_view.xml',
        'views/product_defective.xml',
        'views/defective_type.xml',
        # Menu
    ]
}
