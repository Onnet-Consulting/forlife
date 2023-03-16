# -*- coding: utf-8 -*-
{
    'name': "POS Promotion Program",

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
        'forlife_point_of_sale',
        'forlife_promotion',
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_promotion/static/src/js/Promotion.js',
            'forlife_pos_promotion/static/src/js/ControlButtons/PromotionButton.js',
            'forlife_pos_promotion/static/src/js/ControlButtons/EnterCodeButton.js',
            'forlife_pos_promotion/static/src/js/Popup/ProgramSelectionPopup.js',
            'forlife_pos_promotion/static/src/js/ControlButtons/ResetPromotionProgramsButton.js',
            'forlife_pos_promotion/static/src/js/Popup/ComboDetailsPopup.js',

            'forlife_pos_promotion/static/src/xml/ControlButtons/PromotionButton.xml',
            'forlife_pos_promotion/static/src/xml/ControlButtons/EnterCodeButton.xml',
            'forlife_pos_promotion/static/src/xml/Popup/ProgramSelectionPopup.xml',
            'forlife_pos_promotion/static/src/xml/ControlButtons/ResetPromotionProgramsButton.xml',

            'forlife_pos_promotion/static/src/xml/Screens/ProductScreen/Orderline.xml',
            'forlife_pos_promotion/static/src/xml/Popup/ProgramSelectionPopup.xml',
            'forlife_pos_promotion/static/src/xml/Popup/ComboDetailsPopup.xml',

            'forlife_pos_promotion/static/src/css/detail-product-popup.css',

        ],
    },

    'data': [
        # Security
        'security/ir.model.access.csv',
        # Wizards
        'wizards/promotion_generate_code_views.xml',
        # View
        'views/promotion_program_views.xml',
        'views/promotion_combo_line_views.xml',
        'views/promotion_code_views.xml',
        'views/pos_order_views.xml',
        'views/promotion_campaign_views.xml',
        'views/promotion_pricelist_item_views.xml',
        'views/pos_order_line_usage_views.xml',
        # Menu
        'menu/menu_views.xml',
    ]
}
