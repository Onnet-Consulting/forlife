odoo.define('forlife_product_combo.ProductScreen', function (require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const rpc = require('web.rpc');

    const ProductComboScreen = ProductScreen => class extends ProductScreen {

        get_combo(vals) {
            return rpc.query({
                model: 'product.combo',
                method: 'get_combo',
                args: [vals]
            });
        }

        getDifference(a, b) {
          return a.filter(element => !b.includes(element)).concat(b.filter(element => !a.includes(element)));
        }

        async _onClickPay() {
            var self = this;
            var order_lines = this.env.pos.selectedOrder.orderlines
            var list_product_tmpl =[]
            order_lines.forEach(function(line){
                list_product_tmpl.push({
                    'product_tmpl_id': line.product.product_tmpl_id,
                    'quantity': line.quantity
                })
            })
            var rslt = await this.get_combo(list_product_tmpl)
            var rsltObject = {}
            var list_key = []
            var product_in_combo = []
            if (rslt.length >0){
                rslt.forEach(function(item){
                    let key = `combo_id_${item.combo_id}`
                    if(rsltObject[key]){
                        rsltObject[key].push(item.product_tmpl_id)
                    }else{
                        rsltObject[key]=[]
                        list_key.push(key)
                        rsltObject[key].push(item.product_tmpl_id)
                    }
                })
            }
            var list_name = []
            for(let i=0; i< list_key.length; i++){
                let product_valid_combo_in_pos = []
                for(let j =0;j <list_product_tmpl.length; j++){
                    if(rsltObject[list_key[i]].includes(list_product_tmpl[j].product_tmpl_id)){
                        product_valid_combo_in_pos.push(list_product_tmpl[j].product_tmpl_id)
                    }
                }
                if(product_valid_combo_in_pos.length != rsltObject[list_key[i]].length){
                    let product_diff = self.getDifference(product_valid_combo_in_pos,rsltObject[list_key[i]])
                    order_lines.forEach(function(line){
                        if(!rsltObject[list_key[i]].includes(line.product.product_tmpl_id)){
                            list_name.push(line.product.display_name)
                        }
                    })
                }
            }
//                                this.showPopup('ErrorPopup', {
//                        title: this.env._t('Error: no internet connection.'),
//                        body: this.env._t('Some, if not all, post-processing after syncing order failed.'),
//                    });

//            for(let i =0; i< list_product_tmpl.length;i++){
//                for(let j=0; j< rslt.length;j ++){
//                    if(!product_valid_combo_in_pos[rslt]){
//                        product_valid_combo_in_pos[rslt] = [];
//                        if(list_product_tmpl[i].product_tmpl_id == rslt[j].product_tmpl_id){
//                            product_valid_combo_in_pos[rslt].push(list_product_tmpl[i].product_tmpl_id)
//                        }else{
//
//                        }
//                    }
//                }
//            }
            console.log('2')
            return await super._onClickPay(...arguments);
        }
    };

    Registries.Component.extend(ProductScreen, ProductComboScreen);

    return ProductScreen;

});
