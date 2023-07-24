{
    'name': 'Forlife Pos Partner View',
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
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_search_customer/static/src/xml/Screens/PartnerListScreen/PartnerListScreen.xml',
            'forlife_pos_search_customer/static/src/js/Screens/PartnerListScreen/PartnerListScreen.js',
            'forlife_pos_search_customer/static/src/js/Screens/PartnerListScreen/PartnerDetailsEdit.js',
            'forlife_pos_search_customer/static/src/js/Screens/ProductScreen/ProductScreen.js',
            'forlife_pos_search_customer/static/src/css/searchbar_customer.css',
        ],
    }
}
