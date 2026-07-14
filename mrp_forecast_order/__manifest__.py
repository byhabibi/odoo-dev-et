
{
    "name": "MRP Forecast Order",
    "version": "1.0",
    "license": "LGPL-3",
    "author": "Delta Solusi Nusantara",
    "summary": "Forecast for Manufactur Order",
    "website": "https://www.dsnusantara.com",
    "category": "Sales",
    "depends": ["base", "mrp", "sale", "stock", "product", "report_xlsx", "purchase_request", "purchase", "purchase_stock", "mrp_mps"],
    "data": [
        #Security
        "security/ir.model.access.csv",

        #Data
        "data/dsn_ir_sequence.xml",
        "data/dsn_report_data.xml",

        #Wizard
        "wizard/dsn_mps_wizard_views.xml",
        "wizard/dsn_mrp_wizard_views.xml",

        #Views
        "views/dsn_forecast_order_views.xml",
        "views/dsn_demand_planning_views.xml",
        "views/dsn_stock_warehouse_order_point_views.xml",
        "views/dsn_mps_views.xml",
        "views/dsn_mrp_views.xml",
        "views/dsn_menu_views.xml"
    ],
    "installable": True,
    "application": True,
}
