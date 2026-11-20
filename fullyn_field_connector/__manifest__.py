# Copyright 2026 Fullyn SRL
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
{
    "name": "Fullyn Field Connector",
    "summary": (
        "Field Service, Planning, Timesheets and Pre-payroll for field teams: "
        "site time tracking, Checkinatwork, Check In and Out at Work (CIAO), "
        "CP 124 / PC 124 and CP 149.01 / PC 149.01 mobility"
    ),
    "description": """
Fullyn Field Connector
======================

Connects your Odoo database to Fullyn Field, the Belgian field-team solution:
Field Service, Planning, Timesheets, Pre-payroll, site time tracking
(start/stop, team and kiosk), Checkinatwork, Check In and Out at Work (CIAO),
mobility CP 124 / PC 124 and CP 149.01 / PC 149.01, time off, month-end
validation and closing before payroll. For construction, installers,
maintenance, cleaning and landscaping companies.

What the module does
--------------------
* Adds a "Fullyn Field" menu and a settings screen.
* Stores the address of your Fullyn platform and your Fullyn API key.
* Tests the connection to your Fullyn account (opt-in, see below).
* Runs a local readiness check of your database (Odoo version, employees,
  active projects, Project / Timesheets / Planning / Time Off apps).

External service
----------------
This module requires a Fullyn account (separate subscription, fullyn.com).
Without an account, the menu, settings and readiness check still work.

Data sent to Fullyn
-------------------
Nothing is sent unless an administrator ticks "Allow data exchange with
Fullyn" and clicks "Test connection". The test only sends the API key and
the module version to the platform address configured in the settings.
No employee, project or timesheet data is sent by this module.
""",
    "version": "20.0.1.0.2",
    "category": "Human Resources",
    "author": "Fullyn",
    "website": "https://fullyn.com",
    "support": "info@fullyn.com",
    "license": "LGPL-3",
    "depends": ["base_setup"],
    "data": [
        "data/ir_actions_server.xml",
        "views/res_config_settings_views.xml",
        "views/menus.xml",
    ],
    "images": ["static/description/banner.png"],
    "application": True,
    "installable": True,
}
