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
        'forlife_point_of_sale',
        'web_map',
    ],
    'auto_install': True,

    'data': [
        'data/brand_data.xml',
        'views/res_brand_views.xml',
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
