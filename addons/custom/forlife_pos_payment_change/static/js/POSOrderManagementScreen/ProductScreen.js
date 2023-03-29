odoo.define('forlife_pos_payment_change.ProductScreen', function (require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const rpc = require('web.rpc');
    const WarehouseProductScreen = ProductScreen => class extends ProductScreen {

        async _onClickPay() {
            var picking_type_id = this.env.pos.picking_type.id;
            var order_lines = [];
            this.env.pos.selectedOrder.orderlines.forEach(function(item){
                order_lines.push({
                    product_id: item.product.id,
                    quantity: item.quantity
                })
            })
            var new_arr = {};
            order_lines.forEach(function(item){
                if (new_arr[item.product_id]){
                    new_arr[item.product_id] = new_arr[item.product_id] + item.quantity;
                }else{
                    new_arr[item.product_id] = item.quantity;
                }
            })
            try{
                var data = await rpc.query({
                    model: 'pos.order',
                    method: 'check_stock_quant_inventory',
                    args: [picking_type_id, [new_arr]],
                });
                if(data){
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Warning'),
                        body: this.env._t(
                            data
                        ),
                    });
                    return false;
                }else{
                    return await super._onClickPay(...arguments);
                }
            }catch(error){
                console.log(error)
            }
            return await super._onClickPay(...arguments);
        }
    };

    Registries.Component.extend(ProductScreen, WarehouseProductScreen);

    return ProductScreen;

});