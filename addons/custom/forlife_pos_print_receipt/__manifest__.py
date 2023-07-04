# -*- coding: utf-8 -*-
{
    'name': "PoS print receipts",
    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",

    'category': 'Point of Sales',
    'version': '16.0.1.0.0',

    'depends': [
        'web_map',
        'forlife_point_of_sale',
        'forlife_pos_point_order',
        'forlife_customer_card_rank',
        'forlife_pos_promotion',
        'forlife_pos_product_change_refund',

    ],
    'auto_install': True,

    'data': [
        'data/brand_data.xml',
        'views/res_brand_views.xml',
        'views/pos_orderx.xml',
        'report/print_pos_order.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_print_receipt/static/src/js/**/*.js',
            'forlife_pos_print_receipt/static/src/xml/Screens/ReceiptScreen/OrderReceipt.xml',
            'forlife_pos_print_receipt/static/src/xml/Screens/ReceiptScreen/FormatOrderReceipt.xml',
            'forlife_pos_print_receipt/static/src/xml/Screens/ReceiptScreen/TokyoLifeOrderReceipt.xml',
            'forlife_pos_print_receipt/static/src/xml/Screens/PaymentScreen/PaymentScreen.xml',
            'forlife_pos_print_receipt/static/src/css/**/*.css',
            'forlife_pos_print_receipt/static/src/scss/**/*.scss',
        ],
    }
}
