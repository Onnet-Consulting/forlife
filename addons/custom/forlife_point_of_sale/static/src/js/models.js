odoo.define('forlife_point_of_sale.models', function (require) {
    "use strict";

    var {PosGlobalState, Order, Orderline} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');


    const CustomPosGlobalState = (PosGlobalState) => class extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.pos_brand_info = loadedData['pos_brand_info'];
        }

        async getClosePosInfo() {
            let result = await super.getClosePosInfo();
            result['movesNegative'] = result.defaultCashDetails.moves.filter(l => l.amount <= 0);
            result['movesPositive'] = result.defaultCashDetails.moves.filter(l => l.amount > 0);
            return result;
        }

        // Fully overrided
        async _loadMissingProducts(orders) {
            const missingProductIds = new Set([]);
            for (const order of orders) {
                for (const line of order.lines) {
                    const productId = line[2].product_id;
                    if (missingProductIds.has(productId)) continue;
                    if (!this.db.get_product_by_id(productId)) {
                        missingProductIds.add(productId);
                    }
                }
            }
            const products = await this.env.services.rpc({
                model: 'pos.session',
                method: 'get_pos_ui_product_product_by_params',
                args: [odoo.pos_session_id, {domain: [['id', 'in', [...missingProductIds]]]}],
                // Add context here to avoid filter base on qty on-hand
                kwargs: {
                    context: {
                        'load_missing_product': 1
                    }
                }
            });
            this._loadProductProduct(products);
        }
    }
    Registries.Model.extend(PosGlobalState, CustomPosGlobalState);

    const CustomPosOrder = (Order) => class extends Order {

        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.invoice_info_company_name = this.invoice_info_company_name;
            json.invoice_info_address = this.invoice_info_address;
            json.invoice_info_tax_number = this.invoice_info_tax_number;
            return json;
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.invoice_info_company_name = json.invoice_info_company_name;
            this.invoice_info_address = json.invoice_info_address;
            this.invoice_info_tax_number = json.invoice_info_tax_number;

        }
    }
    Registries.Model.extend(Order, CustomPosOrder);

    const CustomPosOrderline = (Orderline) => class extends Orderline {
        get_full_product_name () {
            let res = super.get_full_product_name();
            if (this.product.full_attrs_desc && !this.full_product_name) {
                res += ` (${this.product.full_attrs_desc})`;
            };
            return res;
        }
    }
    Registries.Model.extend(Orderline, CustomPosOrderline);

});
