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
        'forlife_pos_accounting',
        'web'
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_product_change_refund/static/src/scss/pos.scss',
            'forlife_pos_product_change_refund/static/src/xml/**/*.xml',
            'forlife_pos_product_change_refund/static/src/js/**/*.js',
            'web/static/src/search/search_panel/search_view.scss',
            'web/static/src/search/control_panel/control_panel.scss',
            'web/static/src/scss/bootstrap_overridden_frontend.scss',
            'web/static/src/legacy/scss/modal.scss',
            ('remove', 'forlife_pos_product_change_refund/static/src/js/debug_context.js')
        ],
        'point_of_sale.pos_assets_backend': [
            'forlife_pos_product_change_refund/static/src/js/debug_context.js'
        ]
    },

    'data': [
        # Security
        'security/security.xml',
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
        'views/templates.xml',
        'wirards/return_pos_order_line.xml',
        # Menu
    ]
}
