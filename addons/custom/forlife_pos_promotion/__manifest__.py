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
        'forlife_voucher',
        'forlife_pos_point_order',
        'forlife_pos_layout'
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_promotion/static/src/js/Promotion.js',
            'forlife_pos_promotion/static/src/js/CustomOrderline.js',
            # 'forlife_pos_promotion/static/src/js/OrderSummary.js',
            'forlife_pos_promotion/static/src/js/CustomOrderSummary.js',
            'forlife_pos_promotion/static/src/js/ProductScreen.js',
            'forlife_pos_promotion/static/src/js/PartnerListScreen.js',
            'forlife_pos_promotion/static/src/js/ControlButtons/PromotionButton.js',
            'forlife_pos_promotion/static/src/js/ControlButtons/EnterCodeButton.js',
            'forlife_pos_promotion/static/src/js/Popup/ProgramSelectionPopup.js',
            'forlife_pos_promotion/static/src/js/ControlButtons/ResetPromotionProgramsButton.js',
            'forlife_pos_promotion/static/src/js/Popup/ComboDetailsPopup.js',
            'forlife_pos_promotion/static/src/js/ControlButtons/CartPromotionButton.js',
            'forlife_pos_promotion/static/src/js/Popup/CartPromotionPopup.js',
            'forlife_pos_promotion/static/src/js/Popup/RewardSelectionCartPromotionPopup.js',
            'forlife_pos_promotion/static/src/js/Popup/SurpriseRewardPopup.js',
            'forlife_pos_promotion/static/src/js/db.js',
            'forlife_pos_promotion/static/src/js/models.js',
            'forlife_pos_promotion/static/src/js/Popup/CodeInputPopup.js',
            'forlife_pos_promotion/static/src/xml/ControlButtons/PromotionButton.xml',
            'forlife_pos_promotion/static/src/xml/ControlButtons/EnterCodeButton.xml',
            'forlife_pos_promotion/static/src/xml/Popup/ProgramSelectionPopup.xml',
            'forlife_pos_promotion/static/src/xml/ControlButtons/ResetPromotionProgramsButton.xml',

            'forlife_pos_promotion/static/src/xml/Screens/ProductScreen/OrderDetail.xml',
            'forlife_pos_promotion/static/src/xml/Screens/ProductScreen/CustomOrderline.xml',
            'forlife_pos_promotion/static/src/xml/Screens/ProductScreen/OrderLineChangeRefund.xml',
            'forlife_pos_promotion/static/src/xml/Popup/ProgramSelectionPopup.xml',
            'forlife_pos_promotion/static/src/xml/Popup/ComboDetailsPopup.xml',
            'forlife_pos_promotion/static/src/xml/ControlButtons/CartPromotionButton.xml',
            'forlife_pos_promotion/static/src/xml/Popup/CartPromotionPopup.xml',
            'forlife_pos_promotion/static/src/xml/Popup/RewardSelectionCartPromotionPopup.xml',
            'forlife_pos_promotion/static/src/xml/Popup/SurpriseRewardPopup.xml',
            'forlife_pos_promotion/static/src/xml/Popup/CodeInputPopup.xml',

            'forlife_pos_promotion/static/src/css/detail-product-popup.css',
            'forlife_pos_promotion/static/src/css/program-selection-popup.css',

        ],
    },

    'data': [
        # Data
        'data/ir_cron_data.xml',
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
        'views/condition_product_promotion_views.xml',
        # Menu
        'menu/menu_views.xml',
    ]
}
