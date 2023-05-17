odoo.define('forlife_product_combo.ProductScreen', function (require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    const ProductComboScreen = ProductScreen => class extends ProductScreen {
        async _onClickPay() {
            var order_lines = [];
            var currentOrder = this.currentOrder;
            var message = '';
            var combo = this.env.pos.product_combo;

            this.env.pos.selectedOrder.orderlines.forEach(function(item){
                order_lines.push({
                    product_id: item.product.id,
                    product_tmpl_id: item.product.product_tmpl_id,
                    combo_id: item.product.combo_id[0],
                    product_name:item.product.display_name,
                    count: item.quantity,
                })
            })

            //nghiệp vụ đổi hàng
            if(this.env.pos.get_order().is_change_product){
                try{
                    var order_old_lines = [];
                    var order_new_lines = [];
                    var order_new_ids = [];
                    var message = '';
                    _.each(currentOrder.get_orderlines(), function (orderLine) {
                       if(orderLine.product.combo_id[0] !=null && !orderLine.is_new_line && orderLine.quantity !== 0){
                            order_old_lines.push(orderLine);

                           // message = "Code " + orderLine.product.sku_code + " refund not enough quantity!";
                       }
                       if(orderLine.product.combo_id[0] !=null && orderLine.is_new_line){
                            order_new_lines.push(orderLine);
                            order_new_ids.push(orderLine.product.id);
                           // message = "Code " + orderLine.product.sku_code + " refund not enough quantity!";
                       }
                    })
                    if(order_old_lines){
                        _.each(order_old_lines, function (orderOldLine) {
                            if(order_new_lines){
                                //  check neu khong co trong mang
                                if(jQuery.inArray(orderOldLine.product.id, order_new_ids) == -1) {
                                    message = "Bạn cần chọn sản phẩm " + orderLine.product.sku_code + " để đổi trả!";
                                }else{
                                    // neu co trong mang check so luong san pham can doi tra
                                    _.each(order_new_lines, function (orderNewLine) {
                                        if(orderOldLine.product.id == orderNewLine.product.id && Math.abs(orderOldLine.quantity) != orderNewLine.quantity){
                                            // message = "Bạn cần đúng số lượng sản phẩm " + orderLine.product.sku_code + " để đổi trả!";
                                            message = "Bạn cần nhập đúng số lượng sản phẩm để đổi trả!";
                                        }
                                    })
                                }
                            }
                            else{
                                message = "Bạn cần chọn sản phẩm " + orderLine.product.sku_code + " để đổi trả!";
                            }
                        })
                    }

                    if(message.length > 0) {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Warning'),
                            body: this.env._t(
                                message
                            ),
                        });
                        return false;
                    }else{
                        return await super._onClickPay(...arguments);
                    }
                }catch(error){
                    console.log(error)
                }
            }

            // nghiệp vụ tra hang
            if(this.env.pos.get_order().is_refund_product) {
                try{
                    var order_old_lines = [];
                    var combo_old_ids = [];
                    var message = '';
                    _.each(currentOrder.get_orderlines(), function (orderLine) {
                       if(orderLine.product.combo_id[0] !=null && !orderLine.is_new_line){
                            order_old_lines.push(orderLine);
                       }
                    })
                    if(order_old_lines){
                        _.each(order_old_lines, function (orderOldLine) {
                            if(orderOldLine.quantity != 0 && Math.abs(orderOldLine.quantity) != orderOldLine.quantity_canbe_refund){
                                message = "Bạn cần trả đúng số lượng sản phẩm combo đã mua!";
                                combo_old_ids.push(orderOldLine.product.combo_id[0]);
                            }
                        })
                        if(combo_old_ids.length > 0) {
                            _.each(order_old_lines, function (orderOldLine) {
                                if(jQuery.inArray(orderOldLine.product.combo_id[0], combo_old_ids) != -1) {
                                    if(orderOldLine.quantity == 0){
                                        message = "Bạn cần trả đúng số lượng sản phẩm combo đã mua!";
                                    }
                                }
                            })
                        }
                    }

                    if(message.length > 0) {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Warning'),
                            body: this.env._t(
                                message
                            ),
                        });
                        return false;
                    }else{
                        return await super._onClickPay(...arguments);
                    }
                }catch(error){
                    console.log(error)
                }
            }

            // nghiep vu  mua combo
            if (!currentOrder.is_change_product && !currentOrder.is_refund_product) {
                // check product combo
                try{
                    var list_product_checked = [];
                    if(combo) {
                        var message = '';
                        order_lines.forEach(function(item){
                            if(jQuery.inArray(item.product_tmpl_id, list_product_checked) == -1) {
                                list_product_checked.push(item.product_tmpl_id);
                                var product_check_combo = [];
                                $.each(combo, $.proxy(function(i, e) {
                                    if(e.id == item.combo_id) {
                                        e.product_combolines.forEach(function (pc) {
                                            var line = [];
                                             order_lines.forEach(function(pp) {
                                                if(pp.product_tmpl_id == pc.product_id){
                                                    line.push(pp);
                                                }
                                            })

                                            line.forEach(function (li) {
                                                if (jQuery.inArray(li.product_tmpl_id, list_product_checked) == -1) {
                                                    list_product_checked.push(li.product_tmpl_id);
                                                }

                                                if (li.count < pc.quantity) {
                                                    message = "Mã " + pc.sku_code + " thuộc bộ nên cần phải hoàn thành bộ khi mua ";
                                                }

                                                if (li.count % pc.quantity != 0) {
                                                    message = "Mã " + pc.sku_code + " thuộc bộ nên cần phải hoàn thành bộ khi mua ";
                                                }

                                                var value = li.count / pc.quantity;
                                                if (jQuery.inArray(value, product_check_combo) == -1) {
                                                    product_check_combo.push(value);
                                                }
                                                if (product_check_combo.length > 1) {
                                                    message = "Không đủ số lượng mua combo bộ vui lòng mua bổ xung";
                                                }
                                            })
                                        });
                                    }
                                }, this));
                            }
                        })

                        if(message.length > 0) {
                            this.showPopup('ErrorPopup', {
                                title: this.env._t('Warning'),
                                body: this.env._t(
                                    message
                                ),
                            });
                            return false;
                        }
                        else{
                            return await super._onClickPay(...arguments);
                        }
                    }
                }catch(error){
                    console.log(error)
                }
            }
        }
    };

    Registries.Component.extend(ProductScreen, ProductComboScreen);

    return ProductScreen;

});