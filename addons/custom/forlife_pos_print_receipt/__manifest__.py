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
    ],
    'auto_install': True,

    'data': [
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_print_receipt/static/src/js/**/*.js',
            'forlife_pos_print_receipt/static/src/xml/Screens/ReceiptScreen/OrderReceipt.xml',
            'forlife_pos_print_receipt/static/src/xml/Screens/ReceiptScreen/FormatOrderReceipt.xml',
            'forlife_pos_print_receipt/static/src/xml/Screens/ReceiptScreen/TokyoLifeOrderReceipt.xml',
            'forlife_pos_print_receipt/static/src/css/**/*.css',
            'forlife_pos_print_receipt/static/src/scss/**/*.scss',
        ],
    }
}
