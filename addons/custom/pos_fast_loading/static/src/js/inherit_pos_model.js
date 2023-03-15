odoo.define("pos_fast_loading.inherit_models", function (require) {
    "use strict";

    var models = require("point_of_sale.models");

    var _super_posmodel = models.PosModel.prototype;

    var _modify_pos_data = function (payload) {
        _super_posmodel._modify_pos_data.apply(this, arguments);
        console.log("############# fast loading function *_modify_pos_data* ##########");
    }

    models.PosModel = models.PosModel.extend({
        
        after_load_server_data: async function () {
            var res  = await _super_posmodel.after_load_server_data.apply(this, arguments);
            if (this.config.enable_pos_longpolling) {
                // monkey-patching ( calling function without putting it depends)
                _super_posmodel._modify_pos_data = this._modify_pos_data;
                this._modify_pos_data = _modify_pos_data;
            }
            return res;
        }

    });
});
