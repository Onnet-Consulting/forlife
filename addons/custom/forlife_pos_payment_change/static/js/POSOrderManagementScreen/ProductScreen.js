odoo.define('forlife_pos_payment_change.ProductScreen', function (require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const rpc = require('web.rpc');
    const WarehouseProductScreen = ProductScreen => class extends ProductScreen {

         combinedItems = (order_lines = []) => {
               const res = order_lines.reduce((acc, obj) => {
                  let found = false;
                  for (let i = 0; i < acc.length; i++) {
                     if (acc[i].product_id === obj.product_id && acc[i].seri == obj.seri) {
                        found = true;
                        acc[i].count=acc[i].count+obj.quantity;
                     };
                  }
                  if (!found) {
                     obj.count = obj.quantity;
                     acc.push(obj);
                  }
                  return acc;
               }, []);
               return res;
            }

        async _onClickPay() {
            var picking_type_id = this.env.pos.picking_type.id;
            var order_lines = [];
            this.env.pos.selectedOrder.orderlines.forEach(function(item){
                if(item.pack_lot_lines){
                    order_lines.push({
                        product_id: item.product.id,
                        quantity: item.quantity,
                        seri:$.trim(item.pack_lot_lines[0].lot_name)
                    })
                }else{
                    order_lines.push({
                        product_id: item.product.id,
                        quantity: item.quantity,
                        seri:false
                    })
                }

            })
            var data_rpc = this.combinedItems(order_lines);
            data_rpc.forEach(function(item){
                delete item.quantity
            })
            try{
                var data = await rpc.query({
                    model: 'pos.order',
                    method: 'check_stock_quant_inventory',
                    args: [picking_type_id, [data_rpc]],
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