odoo.define('forlife_pos_payment_change.ProductScreen', function (require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const rpc = require('web.rpc');
    const WarehouseProductScreen = ProductScreen => class extends ProductScreen {

        inventory_warehouse(){
            return rpc.query({
                model: 'pos.order',
                method: 'check_stock_quant_inventory',
                args: [this.env.pos.picking_type.id],
            });
        }

        async _onClickPay() {
            var result = await this.inventory_warehouse()
            console.log(result)
            return await super._onClickPay(...arguments);
        }
    };

    Registries.Component.extend(ProductScreen, WarehouseProductScreen);

    return ProductScreen;

});