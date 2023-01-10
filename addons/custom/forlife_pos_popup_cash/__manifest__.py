# -*- coding: utf-8 -*-
{
    'name': "Point of Sale Forlife",

    'summary': """Point of Sale Forlife
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Point of Sale POPUP CASH IN/OUT',

    'depends': [
        'point_of_sale',
        'forlife_point_of_sale',
        'forlife_promotion'
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/store.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_popup_cash/static/src/js/popup.js',
            'forlife_pos_popup_cash/static/src/js/onchange_selection.js',
            'forlife_pos_popup_cash/static/src/js/CashMoveButton.js',
            'forlife_pos_popup_cash/static/src/xml/Popups/CashMovePopup.xml',
        ]
    }
}
