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

        getSameValueofArr(a, b) {
          return a.filter(element => b.includes(element));
        }

        pushArr(arr, line) {
            if(!line.refunded_orderline_id){
                 arr.push({
                    'product_tmpl_id': line.product.product_tmpl_id,
                    'product_id':line.product.id,
                    'quantity': line.quantity,
                    'display_name':line.product.display_name,
                    'refunded_orderline_id': false,
                    'sku_code': line.product.sku_code
                })
            }else{
                arr.push({
                    'product_tmpl_id': line.product.product_tmpl_id,
                    'product_id':line.product.id,
                    'quantity': line.quantity,
                    'display_name':line.product.display_name,
                    'refunded_orderline_id': line.refunded_orderline_id,
                    'sku_code': line.product.sku_code
                })
            }
            return arr;
        }

        async _onClickPay() {
            var self = this;
            var order_lines = this.env.pos.selectedOrder.orderlines;
            var order = this.env.pos.selectedOrder;
            var list_product_tmpl =[];

            order_lines.forEach(function(line){
                self.pushArr(list_product_tmpl, line)
            })

            var rslt = await this.get_combo(list_product_tmpl)

            if(!rslt){return await super._onClickPay(...arguments);}

            var rsltObject = {};
            var list_key = [];
            var product_in_combo = [];
            var merge_combo = {}

            rslt.forEach(function(item){
                let key = `combo_id_${item.combo_id}`
                if(rsltObject[key]){
                    rsltObject[key].push(item.sku_code)
                }else{
                    rsltObject[key]=[]
                    list_key.push(key)
                    rsltObject[key].push(item.sku_code)
                }
                if(merge_combo[key]){
                    merge_combo[key].push(item)
                }else{
                    merge_combo[key]=[]
                    merge_combo[key].push(item)
                }
            })

            var list_name = [];
            var list_quantity=[];
            var list_product_new_change = [];
            var list_product_change_invalid = [];

            if(!order.is_change_product){
                for(let i=0; i< list_key.length; i++){
                    let product_valid_combo_in_pos = []
                    for(let j =0;j <list_product_tmpl.length; j++){
                        if(rsltObject[list_key[i]].includes(list_product_tmpl[j].sku_code)){
                            product_valid_combo_in_pos.push(list_product_tmpl[j].sku_code)
                        }
                    }
                    if(product_valid_combo_in_pos.length != rsltObject[list_key[i]].length){
                        let intersection = self.getSameValueofArr(product_valid_combo_in_pos, rsltObject[list_key[i]])
                        order_lines.forEach(function(line){
                            if(intersection.includes(line.product.product_tmpl_id)){
                                list_name.push(line.product.display_name)
                            }
                        })
                    }else {
                        for(let i=0; i< list_key.length; i++){
                            let list_check = []
                            let arr_name = []
                            let arr_qty = []
                            list_product_tmpl.forEach(function(item){
                                for(let j=0; j<merge_combo[list_key[i]].length; j++){
                                    if(item.sku_code == merge_combo[list_key[i]][j].sku_code){
                                       list_check.push(item.quantity/merge_combo[list_key[i]][j].quantity)
                                       arr_name.push(merge_combo[list_key[i]][j].product_name.vi_VN)
                                       arr_qty.push([merge_combo[list_key[i]][j].quantity, merge_combo[list_key[i]][j].product_name.vi_VN])
                                    }
                                }
                            })
                            let msg = '';
                            arr_qty.forEach(function(item, index){
                                if(index != arr_qty.length-1){
                                   msg += `${item.toString().replace(',',' sản phẩm ').replace(',\t',' sản phẩm ')} và `
                                }else{
                                   msg += `${item.toString().replace(',',' sản phẩm ').replace(',\t',' sản phẩm ')}`
                                }
                            })
                            let body;
                            if(!order.is_refund_product){
                                body = this.env._t(`Sản phẩm ${arr_name.toString()} có số lượng chưa đúng so với cấu hình bộ.\n Gợi ý: ${msg} là một bộ!`);
                            }else{
                                body = this.env._t(`Sản phẩm ${arr_name.toString()} phải trả đúng với cấu hình bộ.\n Gợi ý: ${msg} là một bộ!`);
                            }
                            if(new Set(list_check).size !== 1){
                                this.showPopup('ErrorPopup', {
                                    title: this.env._t('Error: Quantity Invalid!'),
                                    body: body,
                                });
                                return;
                            }
                        }
                    }
                }
            }else if(order.is_change_product){
                for(let i=0; i< list_key.length; i++){
                    let product_valid_combo_in_pos = []
                    for(let j =0;j <list_product_tmpl.length; j++){
                        if(rsltObject[list_key[i]].includes(list_product_tmpl[j].product_tmpl_id) && list_product_tmpl[j].refunded_orderline_id){
                            product_valid_combo_in_pos.push(list_product_tmpl[j].product_tmpl_id)
                        }
                    }
//                    for(let i =0; i<list_product_tmpl)
//                    var check_product_add_new = []
//                    order_lines.forEach(function(item){
//                        if(item.is_new_line){
//                            check_product_add_new.push()
//                        }
//                    })
//                    order_lines.forEach(function(line){
//                        for(let k =0; k< list_product_tmpl.length; k++){
//                            if(!line.refunded_orderline_id && !list_product_tmpl[k].refunded_orderline_id){
//                                if(line.product.sku_code != list_product_tmpl[k].sku_code || (line.product.product_tmpl_id == list_product_tmpl[k].product_tmpl_id && line.product.id ==list_product_tmpl[k].product_id)){
//                                    list_product_change_invalid.push(line.product.display_name)
//                                }
//                            }
//                        }
//                    })



                }
            }
//            if (list_name.length >0){
//                let info_order;
//                if(!order.is_refund_product){
//                    info_order = 'Mua'
//                }else{
//                    info_order = 'Trả'
//                }
//                this.showPopup('ErrorPopup', {
//                    title: this.env._t('Error: Product Invalid!'),
//                    body: this.env._t(`Sản phẩm ${list_name.toString()} thuộc bộ nên cần hoàn thành bộ khi ${info_order}!`),
//                });
//                return;
//            }
//            if(list_product_change_invalid.length >0){
//                this.showPopup('ErrorPopup', {
//                    title: this.env._t('Error: Product Invalid!'),
//                    body: this.env._t(`Sản phẩm đổi ${list_product_change_invalid.toString()} trùng với sản phẩm muốn đổi hoặc không thuộc cùng 1 biến thể với sản phẩm muốn đổi!`),
//                });
//                return;
//            }
//            if (list_quantity.length>0){
//                this.showPopup('ErrorPopup', {
//                    title: this.env._t('Error: Quantity Invalid!'),
//                    body: this.env._t(`Sản phẩm ${list_quantity.toString()} có số lượng chưa đúng so với cấu hình bộ !`),
//                });
//                return;
//            }
            return await super._onClickPay(...arguments);
        }
    };

    Registries.Component.extend(ProductScreen, ProductComboScreen);

    return ProductScreen;

});
