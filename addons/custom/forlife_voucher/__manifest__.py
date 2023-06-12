# -*- coding: utf-8 -*-
{
    'name': "Voucher",

    'summary': """
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Voucher/Point of Sale',

    'depends': [
        'base',
        'hr',
        'purchase',
        'sale',
        'analytic',
        'forlife_point_of_sale',
        'forlife_promotion',
        'sh_message'
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/program_voucher.xml',
        'views/setup_voucher.xml',
        'views/voucher_view.xml',
        'views/product_category.xml',
        'views/product_product.xml',
        'views/product_template.xml',
        'views/sale_order.xml',
        'data/ir_sequence.xml',
        'data/ir_cron.xml',
        'views/hr_department.xml',
        'views/pos_order.xml',
        'views/pos_payment_method.xml',
        'views/product_program_import_view.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_voucher/static/src/js/Screen/PaymentScreen.js',
            'forlife_voucher/static/src/js/Screen/ProductScreen.js',
            'forlife_voucher/static/src/js/Popup/VoucherPopups.js',
            'forlife_voucher/static/src/xml/VoucherPopup.xml',
            'forlife_voucher/static/src/js/models.js'
        ]
    }
}
