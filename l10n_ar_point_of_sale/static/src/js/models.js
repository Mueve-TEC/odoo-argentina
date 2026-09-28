odoo.define('l10n_ar_point_of_sale.models', function (require) {
    "use strict";

    const { Order } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const L10nARPointOfSaleOrder = (Order) => class L10nARPointOfSaleOrder extends Order {
        constructor(obj, options) {
            super(...arguments);
            // Sales must generate their invoice by default in Argentina. The
            // cashier can still turn the toggle off on the payment screen.
            if (!(options && options.json)) {
                this.to_invoice = true;
            }
        }
        //@override
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            // Keep the value saved with the order, defaulting to invoicing
            // for orders that don't carry it yet.
            this.to_invoice = json.to_invoice === undefined ? true : json.to_invoice;
        }
    };
    Registries.Model.extend(Order, L10nARPointOfSaleOrder);
});
