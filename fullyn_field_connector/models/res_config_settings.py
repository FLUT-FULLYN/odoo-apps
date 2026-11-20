# Copyright 2026 Fullyn SRL
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
import logging
from urllib.parse import urlparse

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.release import version_info

_logger = logging.getLogger(__name__)

PARAM_PREFIX = "fullyn_field_connector."
DEFAULT_PLATFORM_URL = "https://app.fullyn.com"
# Endpoint used by "Test connection". To be aligned with the Fullyn platform API.
PING_PATH = "/api/v1/ping"
TIMEOUT = 10
MODULE_VERSION = "1.0.0"
DEMO_URLS = {
    "fr": "https://fullyn.com/fr/demo",
    "en": "https://fullyn.com/en/demo",
}
# Odoo apps that Fullyn Field for Odoo writes into.
RELATED_APPS = [
    ("project", "Project"),
    ("hr_timesheet", "Timesheets"),
    ("planning", "Planning"),
    ("hr_holidays", "Time Off"),
    ("hr", "Employees"),
]


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    fullyn_platform_url = fields.Char(
        string="Fullyn platform address",
        default=DEFAULT_PLATFORM_URL,
        config_parameter=PARAM_PREFIX + "platform_url",
    )
    fullyn_api_key = fields.Char(
        string="Fullyn API key",
        config_parameter=PARAM_PREFIX + "api_key",
    )
    fullyn_data_consent = fields.Boolean(
        string="Allow data exchange with Fullyn",
        config_parameter=PARAM_PREFIX + "data_consent",
    )
    fullyn_last_check = fields.Char(
        string="Last connection test",
        compute="_compute_fullyn_last_check",
    )
    fullyn_odoo_version = fields.Char(
        string="Odoo version", compute="_compute_fullyn_readiness"
    )
    fullyn_employee_count = fields.Integer(
        string="Active employees", compute="_compute_fullyn_readiness"
    )
    fullyn_project_count = fields.Integer(
        string="Active projects", compute="_compute_fullyn_readiness"
    )
    fullyn_apps_status = fields.Text(
        string="Related Odoo apps", compute="_compute_fullyn_readiness"
    )
    fullyn_recommendation = fields.Text(
        string="Recommendation", compute="_compute_fullyn_readiness"
    )

    # ------------------------------------------------------------------
    # System parameters (Odoo 19: get_param/set_param, Odoo 20: get_str/set_str)
    # ------------------------------------------------------------------
    @api.model
    def _fullyn_param_get(self, key):
        icp = self.env["ir.config_parameter"].sudo()
        if hasattr(icp, "get_str"):
            return icp.get_str(PARAM_PREFIX + key) or ""
        return icp.get_param(PARAM_PREFIX + key) or ""

    @api.model
    def _fullyn_param_set(self, key, value):
        icp = self.env["ir.config_parameter"].sudo()
        if hasattr(icp, "set_str"):
            icp.set_str(PARAM_PREFIX + key, value)
        else:
            icp.set_param(PARAM_PREFIX + key, value)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    def _compute_fullyn_last_check(self):
        value = self._fullyn_param_get("last_check") or self.env._("Never")
        for record in self:
            record.fullyn_last_check = value

    @api.depends_context("lang")
    def _compute_fullyn_readiness(self):
        readiness = self._fullyn_get_readiness()
        for record in self:
            record.fullyn_odoo_version = readiness["version"]
            record.fullyn_employee_count = readiness["employees"]
            record.fullyn_project_count = readiness["projects"]
            record.fullyn_apps_status = readiness["apps_text"]
            record.fullyn_recommendation = readiness["recommendation"]

    @api.model
    def _fullyn_get_readiness(self):
        """Local diagnostic of the database. Nothing leaves Odoo."""
        installed = set(
            self.env["ir.module.module"]
            .sudo()
            .search(
                [
                    ("name", "in", [name for name, _label in RELATED_APPS]),
                    ("state", "=", "installed"),
                ]
            )
            .mapped("name")
        )
        labels = {
            "project": self.env._("Project"),
            "hr_timesheet": self.env._("Timesheets"),
            "planning": self.env._("Planning"),
            "hr_holidays": self.env._("Time Off"),
            "hr": self.env._("Employees"),
        }
        lines = []
        for name, _label in RELATED_APPS:
            mark = self.env._("installed") if name in installed else self.env._("not installed")
            lines.append(f"{labels[name]}: {mark}")

        employees = 0
        if "hr.employee" in self.env:
            employees = self.env["hr.employee"].sudo().search_count([("active", "=", True)])
        projects = 0
        if "project.project" in self.env:
            projects = self.env["project.project"].sudo().search_count([("active", "=", True)])

        major = version_info[0]
        if major not in (19, 20):
            recommendation = self.env._(
                "Fullyn Field for Odoo supports Odoo 19 and 20. On another version, "
                "connect Odoo to Fullyn Field through the Fullyn platform API."
            )
        elif {"project", "hr_timesheet"} <= installed:
            recommendation = self.env._(
                "Project and Timesheets are installed: field work can be written "
                "directly into task and project timesheets with Fullyn Field for Odoo "
                "(Odoo.sh or self-hosted), or synchronised through the Fullyn platform."
            )
        else:
            recommendation = self.env._(
                "Install Project and Timesheets so that field work can be allocated "
                "to projects, tasks and sales orders. Without them, Fullyn Field works "
                "through the Fullyn platform and sends validated data to Odoo by API."
            )
        return {
            "version": f"{major}.{version_info[1]}",
            "employees": employees,
            "projects": projects,
            "apps_text": "\n".join(lines),
            "recommendation": recommendation,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _fullyn_clean_url(self, url):
        url = (url or DEFAULT_PLATFORM_URL).strip().rstrip("/")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise UserError(
                self.env._("The Fullyn platform address must start with https://")
            )
        return url

    @api.model
    def _fullyn_store_last_check(self, message):
        stamp = fields.Datetime.to_string(fields.Datetime.now())
        self._fullyn_param_set("last_check", f"{stamp} UTC - {message}")

    @staticmethod
    def _fullyn_notification(title, message, kind):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": kind,
                "sticky": False,
            },
        }

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def action_fullyn_test_connection(self):
        """Opt-in connection test. Sends only the API key and module version."""
        self.ensure_one()
        if not self.env.user.has_group("base.group_system"):
            raise UserError(self.env._("Only administrators can test the connection."))
        if not self.fullyn_data_consent:
            raise UserError(
                self.env._(
                    "Tick \"Allow data exchange with Fullyn\" before testing the connection."
                )
            )
        if not self.fullyn_api_key:
            raise UserError(
                self.env._("Enter the API key of your Fullyn account first.")
            )
        base_url = self._fullyn_clean_url(self.fullyn_platform_url)
        try:
            response = requests.get(
                base_url + PING_PATH,
                headers={
                    "Authorization": f"Bearer {self.fullyn_api_key.strip()}",
                    "Accept": "application/json",
                    "User-Agent": f"Odoo/{version_info[0]} fullyn_field_connector/{MODULE_VERSION}",
                },
                timeout=TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            _logger.info("Fullyn connection test failed: %s", exc)
            message = self.env._("Fullyn platform unreachable from this server.")
            self._fullyn_store_last_check(message)
            return self._fullyn_notification(
                self.env._("Connection failed"), message, "danger"
            )

        payload = None
        if "json" in (response.headers.get("Content-Type") or ""):
            try:
                payload = response.json()
            except ValueError:
                payload = None
        if response.status_code == 200 and isinstance(payload, dict) and payload.get("status") == "ok":
            account = payload.get("account")
            if account:
                message = self.env._(
                    "Connected to the Fullyn account %(account)s.", account=account
                )
            else:
                message = self.env._("Connected to your Fullyn account.")
            kind, title = "success", self.env._("Connection OK")
        elif response.status_code == 200:
            message = self.env._(
                "The address answered, but not as the Fullyn API. Check the platform address."
            )
            kind, title = "warning", self.env._("Connection failed")
        elif response.status_code in (401, 403):
            message = self.env._("The API key was refused by the Fullyn platform.")
            kind, title = "warning", self.env._("Invalid API key")
        else:
            message = self.env._(
                "Unexpected answer from the Fullyn platform (HTTP %(code)s).",
                code=response.status_code,
            )
            kind, title = "danger", self.env._("Connection failed")
        self._fullyn_store_last_check(message)
        return self._fullyn_notification(title, message, kind)

    @api.model
    def fullyn_action_open_platform(self):
        url = self._fullyn_param_get("platform_url")
        try:
            url = self._fullyn_clean_url(url)
        except UserError:
            url = DEFAULT_PLATFORM_URL
        return {"type": "ir.actions.act_url", "url": url, "target": "new"}

    @api.model
    def fullyn_action_book_demo(self):
        lang = (self.env.lang or "en_US")[:2]
        url = DEMO_URLS.get(lang, DEMO_URLS["en"])
        return {"type": "ir.actions.act_url", "url": url, "target": "new"}

    def action_fullyn_open_platform(self):
        return self.fullyn_action_open_platform()

    def action_fullyn_book_demo(self):
        return self.fullyn_action_book_demo()
