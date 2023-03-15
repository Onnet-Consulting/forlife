odoo.define('forlife_pos_layout.CustomProductItem', function(require) {
    'use strict';

    const ProductItem = require('point_of_sale.ProductItem');
    const Registries = require('point_of_sale.Registries');
    const { ConnectionLostError, ConnectionAbortedError } = require('@web/core/network/rpc_service')
    const { identifyError } = require('point_of_sale.utils');

    class CustomProductItem extends ProductItem {}

    CustomProductItem.template = 'CustomProductItem';

    Registries.Component.add(CustomProductItem);

    return CustomProductItem;
});
