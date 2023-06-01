{
    'name': "Forlife POS Accounting",
    'summary': """
        Forlife POS Accounting
    """,

    'description': """
        Forlife POS Accounting
    """,
    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',
    'category': 'Forlife POS Accounting',
    'depends': [
        'account',
        'point_of_sale',
        'forlife_promotion',
        'forlife_pos_promotion',
        'forlife_customer_card_rank'
    ],

    'data': [
        'views/journal_views.xml',
        'views/product_views.xml',
        'views/member_card_views.xml',
        'views/points_promotion_views.xml',
        'views/promotion_program_views.xml',
        'views/pos_order_views.xml'
    ],
    'installable': True,
    'application': True,
    'assets': {
    },
}
