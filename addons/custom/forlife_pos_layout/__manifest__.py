{
    'name': 'Forlife Pos layout',
    'version': '1.0',
    'description': '',
    'summary': '',
    'author': 'ForLife',
    'website': '',
    'license': 'LGPL-3',
    'category': 'Sales/Point of Sale',
    'depends': [
        'point_of_sale'
    ],
    'auto_install': True,
    'application': False,
    'data': [],
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_layout/static/src/css/override_pos.css',
            'forlife_pos_layout/static/src/xml/Screens/ProductScreen/ProductsWidgetControlPanel.xml',
            'forlife_pos_layout/static/src/xml/Screens/ProductScreen/ProductItem.xml',
            'forlife_pos_layout/static/src/js/Screens/ProductScreen/ProductItem.js',
            'forlife_pos_layout/static/src/xml/Screens/ProductScreen/Orderline.xml',
            'forlife_pos_layout/static/src/xml/Screens/ProductScreen/OrderLineChangeRefund.xml',
            'forlife_pos_layout/static/src/js/Screens/ProductScreen/Orderline.js',
            'forlife_pos_layout/static/src/js/Screens/ProductScreen/OrderLineChangeRefund.js',
            'forlife_pos_layout/static/src/xml/Screens/ProductScreen/OrderWidget.xml',
            'forlife_pos_layout/static/src/xml/Screens/ProductScreen/ProductsWidget.xml',
            'forlife_pos_layout/static/src/xml/Screens/ProductScreen/ProductScreen.xml',
            'forlife_pos_layout/static/src/js/Screens/ProductScreen/CustomOrderSummary.js',
            'forlife_pos_layout/static/src/xml/Screens/ProductScreen/CustomOrderSummary.xml',
            'forlife_pos_layout/static/src/xml/Screens/ProductScreen/ControlButtons/ProductInfoButton.xml',
            'forlife_pos_layout/static/src/xml/Screens/ReceiptScreen/ReceiptScreen.xml',
            'forlife_pos_layout/static/src/xml/Chrome.xml',
            'forlife_pos_layout/static/src/js/Chrome.js',
            'forlife_pos_layout/static/src/js/models.js',
        ],
    }
}
