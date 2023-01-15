# -*- coding: utf-8 -*-
{
    'name': "POS Payment Method Change",
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
    ],

    'data': [
        "security/ir.model.access.csv",
        "wizards/view_pos_payment_change_wizard.xml",
        "views/view_pos_order.xml",
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_payment_change/static/js/SetPOSOrderButton.js',
            'forlife_pos_payment_change/static/js/POSOrderManagementScreen/POSOrderManagementScreen.js',
            'forlife_pos_payment_change/static/js/POSOrderManagementScreen/POSOrderManagementControlPanel.js',
            'forlife_pos_payment_change/static/js/POSOrderManagementScreen/POSOrderFetcher.js',
            'forlife_pos_payment_change/static/js/POSOrderManagementScreen/POSOrderList.js',
            'forlife_pos_payment_change/static/js/POSOrderManagementScreen/POSOrderRow.js',
            'forlife_pos_payment_change/static/js/Popup/PaymentChangePopup.js',

            'forlife_pos_payment_change/static/xml/POSOrderButton.xml',
            'forlife_pos_payment_change/static/xml/POSOrderManagementScreen/POSOrderManagementScreen.xml',
            'forlife_pos_payment_change/static/xml/POSOrderManagementScreen/POSOrderManagementControlPanel.xml',
            'forlife_pos_payment_change/static/xml/POSOrderManagementScreen/POSOrderList.xml',
            'forlife_pos_payment_change/static/xml/POSOrderManagementScreen/POSOrderRow.xml',
            'forlife_pos_payment_change/static/xml/Popup/PaymentChangePopup.xml',

        ],
    }
}
