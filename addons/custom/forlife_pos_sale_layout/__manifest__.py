# -*- coding: utf-8 -*-
{
    'name': 'Forlife Pos Sale layout',
    'version': '1.0',
    'description': '',
    'summary': '',
    'author': 'ForLife',
    'website': '',
    'license': 'LGPL-3',
    'category': 'Sales/Point of Sale',
    'depends': [
        'forlife_pos_payment_change',
        'forlife_pos_promotion',
        'forlife_pos_point_order',
        'forlife_pos_accounting'
    ],
    'auto_install': True,
    'application': False,
    'data': [],
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_sale_layout/static/src/js/POSOrderManagementScreen/PosOrderRow.js',
            'forlife_pos_sale_layout/static/src/js/Popups/PosOrderSaleInfoPopup.js',
            'forlife_pos_sale_layout/static/src/xml/POSOrderManagementScreen/POSOrderList.xml',
            'forlife_pos_sale_layout/static/src/xml/POSOrderManagementScreen/PosOrderRow.xml',
            'forlife_pos_sale_layout/static/src/xml/Popups/PosOrderSaleInfoPopup.xml',
            'forlife_pos_sale_layout/static/src/scss/pos_sale.scss',
        ],
    }
}
