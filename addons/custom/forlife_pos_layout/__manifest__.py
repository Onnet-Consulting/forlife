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
            'forlife_pos_layout/static/src/xml/Screens/ProductScreen/ProductsWidget.xml',
            'forlife_pos_layout/static/src/xml/Screens/ProductScreen/ProductScreen.xml',
        ],
    }
}
