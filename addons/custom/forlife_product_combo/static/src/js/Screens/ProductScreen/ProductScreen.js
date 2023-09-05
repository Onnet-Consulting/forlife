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
                            if(intersection.includes(line.product.sku_code)){
                                list_name.push(line.product.display_name)
                            }
                        })
                    }else {
                        for(let i=0; i< list_key.length; i++){
                            let value_check = this._function_validate_quantity(list_product_tmpl, list_key, merge_combo, i)
                            let list_check = value_check[0]
                            let body = value_check[1]
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
                    let value_check = this._function_validate_quantity(list_product_tmpl, list_key, merge_combo, i)
                    let list_check = value_check[0]
                    let body = value_check[1]
                    let item_line = value_check[2]
                    let new_add_line = []
                    if(new Set(list_check).size !== 1){
                        order_lines.forEach(function(line){
                            for(let it of item_line){
                               if(!line.refunded_orderline_id && line.product.sku_code == it.sku_code && Math.abs(line.quantity) == Math.abs(it.quantity) && it.quantity !==0){
                                  if (!new_add_line[it.product_tmpl_id]){
                                      new_add_line[it.product_tmpl_id] = line.product.display_name
                                  }
                               }else{
                                  if (!new_add_line[it.product_tmpl_id] && it.quantity !== 0){
                                      new_add_line[it.product_tmpl_id] = false
                                  }
                               }
                            }
                        })
                        for(let it of item_line){
                            if(new_add_line[it.product_tmpl_id] == false){
                                this.showPopup('ErrorPopup', {
                                    title: this.env._t('Error!'),
                                    body: this.env._t(`Sản phẩm ${it.display_name} thuộc bộ nên cần hoàn thành bộ khi mua mới (Sản phẩm hoặc số lượng của sản phẩm mua mới không hợp lệ!)`)
                                });
                                return;
                            }
                        }
                    }else{
                        let product_valid_combo_in_pos = []
                        for(let j =0;j <list_product_tmpl.length; j++){
                            if(rsltObject[list_key[i]].includes(list_product_tmpl[j].sku_code) && list_product_tmpl[j].quantity > 0){
                                product_valid_combo_in_pos.push(list_product_tmpl[j].sku_code)
                            }
                        }
                        if(product_valid_combo_in_pos.length != rsltObject[list_key[i]].length){
                            let intersection = self.getSameValueofArr(product_valid_combo_in_pos, rsltObject[list_key[i]])
                            order_lines.forEach(function(line){
                                if(intersection.includes(line.product.sku_code) && line.quantity >0){
                                    list_name.push(line.product.display_name)
                                }
                            })
                        }
                    }
                }
            }
            if (list_name.length >0){
                let info_order;
                if(!order.is_refund_product){
                    info_order = 'Mua'
                }else{
                    info_order = 'Trả'
                }
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Error: Product Invalid!'),
                    body: this.env._t(`Sản phẩm ${list_name.toString()} thuộc bộ nên cần hoàn thành bộ khi ${info_order}!`),
                });
                return;
            }
            return await super._onClickPay(...arguments);
        }
        _function_validate_quantity (list_product_tmpl, list_key, merge_combo, i) {
            var order = this.env.pos.selectedOrder;
            let list_check = []
            let arr_name = []
            let arr_qty = []
            let item_line = []
            list_product_tmpl.forEach(function(item){
                for(let j=0; j<merge_combo[list_key[i]].length; j++){
                    if(item.sku_code == merge_combo[list_key[i]][j].sku_code){
                       if(order.is_change_product && item.quantity <= 0){
                           list_check.push(item.quantity/merge_combo[list_key[i]][j].quantity)
                           arr_name.push(merge_combo[list_key[i]][j].product_name.vi_VN)
                           arr_qty.push([merge_combo[list_key[i]][j].quantity, merge_combo[list_key[i]][j].product_name.vi_VN])
                           item_line.push(item)
                       }else if(!order.is_change_product){
                           list_check.push(item.quantity/merge_combo[list_key[i]][j].quantity)
                           arr_name.push(merge_combo[list_key[i]][j].product_name.vi_VN)
                           arr_qty.push([merge_combo[list_key[i]][j].quantity, merge_combo[list_key[i]][j].product_name.vi_VN])
                           item_line.push(item)
                       }
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
            if(!order.is_refund_product && !order.is_change_product){
                body = this.env._t(`Sản phẩm ${arr_name.toString()} có số lượng chưa đúng so với cấu hình bộ.\n Gợi ý: ${msg} là một bộ!`);
            }else{
                body = this.env._t(`Sản phẩm ${arr_name.toString()} phải trả đúng với cấu hình bộ.\n Gợi ý: ${msg} là một bộ!`);
            }
            return [list_check, body, item_line]
        }

//        _function_validate_product () {
//
//        }
    };

    Registries.Component.extend(ProductScreen, ProductComboScreen);

    return ProductScreen;

});
