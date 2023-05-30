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
                    attribute_ids: item.product.attribute_ids,
                    product_tmpl_id: item.product.product_tmpl_id,
                    combo_id: item.product.combo_id[0],
                    product_name:item.product.display_name,
                    count: item.quantity,
                })
            })

            //nghiệp vụ đổi hàng
            if(this.env.pos.get_order().is_change_product){
                // select * from product_template_attribute_value where id = 3964747
                try{
                    // orders old
                    var order_old_lines = [];
                    var order_new_lines_combo = [];
                    var order_new_ids_combo = [];
                    var order_new_attribute_ids = [];

                    // orders new
                    var order_new_lines = [];
                    // ids order new
                    var order_new_ids = [];

                    var combo_ids = [];
                    _.each(currentOrder.get_orderlines(), function (orderLine) {
                        var attribute_ids = orderLine.product.attribute_ids.split(",");

                       if(orderLine.product.combo_id[0] !=null && !orderLine.is_new_line && orderLine.quantity !== 0){
                            order_old_lines.push(orderLine);
                            if(jQuery.inArray(orderLine.product.combo_id[0], combo_ids) == -1) {
                                combo_ids.push(orderLine.product.combo_id[0]);
                            }
                       }

                       if(orderLine.product.combo_id[0] !=null && orderLine.is_new_line){
                           // list combo
                            $.each(combo, $.proxy(function(i, e) {
                                //neu tich chon Allowed size hoac color
                                if(e.id == orderLine.product.combo_id[0] && jQuery.inArray(e.size_attribute_id, attribute_ids) != -1 || jQuery.inArray(e.color_attribute_id, attribute_ids) != -1){
                                    order_new_lines_combo.push(orderLine);
                                    order_new_ids_combo.push(orderLine.product.id);
                                    order_new_attribute_ids.push(orderLine.product.attribute_ids[0]);
                                }else if(e.id == orderLine.product.combo_id[0] && jQuery.inArray(e.size_attribute_id, attribute_ids) == -1 && jQuery.inArray(e.color_attribute_id, attribute_ids) == -1){
                                    order_new_lines.push(orderLine);
                                    order_new_ids.push(orderLine.product.id);
                                }
                            }, this));
                       }
                    })
                    var message = '';
                    // danh sach don hang cu
                    if(order_old_lines){
                        if(order_new_lines.length == 0){
                            message = "Bạn cần mua sản phẩm " + orderOldLine.product.display_name + " để đổi trả!";
                        }
                         if(combo_ids) {
                             _.each(combo_ids, function (combo) {
                                 var list_count = []
                                 var list_product_ids = []
                                 _.each(order_old_lines, function (orderOldLine) {
                                     if(combo == orderOldLine.product.combo_id[0] && Math.abs(orderOldLine.quantity) != 0) {
                                         if(jQuery.inArray(orderOldLine.product.id, list_product_ids) == -1) {
                                             var line_combo = [];
                                             _.each(order_old_lines, function (item) {
                                                 if(orderOldLine.product.product_tmpl_id == item.product.product_tmpl_id){
                                                    list_product_ids.push(item.product.id);
                                                    line_combo.push(item);
                                                 }
                                             })

                                             var total_quantity = 0;
                                             line_combo.forEach(function (line2) {
                                                total_quantity = total_quantity + Math.abs(line2.quantity)
                                             })

                                             if(jQuery.inArray(total_quantity, list_count) == -1) {
                                                list_count.push(total_quantity);
                                             }
                                         }
                                     }

                                     // check theo attribute
                                     var attribute_ids = orderOldLine.product.attribute_ids.split(",");
                                     if(jQuery.inArray(orderOldLine.product.id, order_new_ids) == -1) {
                                            // Neu san pham k co trong don hang hien thi thong bao
                                            if(order_new_lines_combo){
                                                _.each(attribute_ids, function (att) {
                                                    if(jQuery.inArray(att, order_new_attribute_ids) != -1 ){
                                                        var total_quantity = 0
                                                        // Nếu có danh sách đơn hàng combo mới
                                                        _.each(order_new_lines_combo, function (orderNewLineCombo) {
                                                            total_quantity = total_quantity + orderNewLineCombo.quantity
                                                        })

                                                        if (total_quantity != Math.abs(orderOldLine.quantity)) {
                                                            message = "Bạn cần mua đủ số lượng sản phẩm " + orderOldLine.product.display_name + " để đổi trả!";
                                                        }
                                                    }
                                                })
                                            }
                                            else
                                            {
                                                message = "Bạn cần mua sản phẩm " + orderOldLine.product.display_name + " để đổi trả!";
                                            }
                                        }
                                         // neu co danh sach don hang moi
                                     _.each(order_new_lines, function (orderNewLine) {
                                             if(orderNewLine.product.id == orderOldLine.product.id && orderNewLine.product.combo_id[0] == orderOldLine.product.combo_id[0] && Math.abs(orderOldLine.quantity) != orderNewLine.quantity ){
                                                message = "Bạn cần mua đủ số lượng sản phẩm " + orderNewLine.product.display_name + " để đổi trả!";
                                             }
                                     })

                                })

                                if(list_count.length > 1) {
                                    message = "Bạn cần trả đúng số lượng combo sản phẩm đã mua!";
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

            // nghiệp vụ tra hang
            if(this.env.pos.get_order().is_refund_product) {
                try{
                    var order_old_lines = [];
                    var combo_ids = [];
                    var message = '';
                    _.each(currentOrder.get_orderlines(), function (orderLine) {
                       if(orderLine.product.combo_id[0] !=null && !orderLine.is_new_line ){
                            order_old_lines.push(orderLine);
                            if(jQuery.inArray(orderLine.product.combo_id[0], combo_ids) == -1) {
                                combo_ids.push(orderLine.product.combo_id[0]);
                            }
                       }
                    })

                    if(order_old_lines){
                        if(combo_ids){
                            _.each(combo_ids, function (combo) {
                                var list_count = []
                                var list_product_ids = []
                                _.each(order_old_lines, function (orderOldLine) {
                                    if(combo == orderOldLine.product.combo_id[0] && Math.abs(orderOldLine.quantity) != 0) {
                                        if(jQuery.inArray(orderOldLine.product.id, list_product_ids) == -1) {
                                            var line_combo = [];
                                            _.each(order_old_lines, function (item) {
                                                if(orderOldLine.product.product_tmpl_id == item.product.product_tmpl_id){
                                                    list_product_ids.push(item.product.id);
                                                    line_combo.push(item);
                                                }
                                            })

                                            var total_quantity = 0;
                                            line_combo.forEach(function (line2) {
                                                total_quantity = total_quantity + Math.abs(line2.quantity)
                                            })

                                            if(jQuery.inArray(total_quantity, list_count) == -1) {
                                                list_count.push(total_quantity);
                                            }
                                        }
                                    }
                                })
                                if(list_count.length > 1) {
                                    message = "Bạn cần trả đúng số lượng combo sản phẩm đã mua!";
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
                            // kiem tra xem id có trong mang khong neu k co thi them vao
                            if(jQuery.inArray(item.product_id, list_product_checked) == -1) {
                                list_product_checked.push(item.product_id);
                                var product_check_combo = [];
                                $.each(combo, $.proxy(function(i, e) {
                                    if(e.id == item.combo_id) {
                                        e.product_combolines.forEach(function (pc) {
                                            var line2 = [];
                                            order_lines.forEach(function(pp) {
                                                if(pp.product_tmpl_id == pc.product_id){
                                                    line2.push(pp);
                                                }
                                            })
                                            var total_quantity = 0
                                            line2.forEach(function (li) {
                                                if (jQuery.inArray(li.product_id, list_product_checked) == -1) {
                                                    list_product_checked.push(li.product_id);
                                                }
                                                total_quantity = total_quantity + li.count
                                            })
                                            //  kiem tra tong so luong cua san pham trong 1 combo
                                            if (total_quantity < pc.quantity) {
                                                message = "Mã " + pc.sku_code + " thuộc bộ nên cần phải hoàn thành bộ khi mua";
                                            }

                                            if (total_quantity % pc.quantity != 0) {
                                                message = "Mã " + pc.sku_code + " thuộc bộ nên cần phải hoàn thành bộ khi mua";
                                            }

                                            var value = total_quantity / pc.quantity;
                                            if (jQuery.inArray(value, product_check_combo) == -1) {
                                                product_check_combo.push(value);
                                            }
                                            if (product_check_combo.length > 1) {
                                                message = "Không đủ số lượng mua combo bộ vui lòng mua bổ xung";
                                            }
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
