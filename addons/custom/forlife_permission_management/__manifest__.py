{
    'name': 'Forlife Permission Management',
    'version': '1.0',
    'description': '',
    'summary': '',
    'author': 'ForLife',
    'website': '',
    'license': 'LGPL-3',
    'category': 'Hidden',
    'depends': [
        'base',
        'product',
        'stock',
        'forlife_point_of_sale',

    ],
    'installable': True,
    'auto_install': True,
    'data': [
        'views/product_product_views.xml',
        'views/res_users_views.xml',
    ],
}
