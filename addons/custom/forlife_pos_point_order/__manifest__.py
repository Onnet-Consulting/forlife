# -*- coding: utf-8 -*-
{
    'name': "Point of Sale Forlife Point Order",

    'summary': """Point of Sale Forlife Point Order
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Point of Sale Point Order',

    'depends': [
        'point_of_sale',
        'forlife_point_of_sale',
        'forlife_pos_app_member',
        'forlife_promotion',
        'forlife_pos_layout',
        'base'
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/account_move.xml',
        'wizards/pos_compensate_point_order_views.xml',
        'wizards/compensate_point_wizard_view.xml',
        'data/cron_job_data.xml',
        'views/pos_order.xml',
        'views/res_partner_view.xml',
        'security/ir.model.access.csv',
        'views/promotion_inherit_view.xml',
        'views/point_compensate_request_views.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_point_order/static/src/xml/OrderDetails.xml',
            'forlife_pos_point_order/static/src/xml/OrderLineDetails.xml',
            'forlife_pos_point_order/static/src/xml/OrderLineChangeRefund.xml',
            'forlife_pos_point_order/static/src/xml/PointsConsumption.xml',
            'forlife_pos_point_order/static/src/xml/PointsConsumptionPopup.xml',
            'forlife_pos_point_order/static/src/xml/EditlistPopup.xml',
            'forlife_pos_point_order/static/src/js/Button/PointsConsumptionButton.js',
            'forlife_pos_point_order/static/src/js/Popup/PointsConsumptionPopup.js',
            'forlife_pos_point_order/static/src/js/OrderDetails/OrderLinesDetails.js',
            'forlife_pos_point_order/static/src/js/models.js',
            'forlife_pos_point_order/static/src/js/ProductScreen.js',
            'forlife_pos_point_order/static/src/js/CustomOrderline.js',
        ]
    },
    'installable': True,
    'application': True,
}
