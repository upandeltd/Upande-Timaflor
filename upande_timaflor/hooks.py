app_name = "upande_timaflor"
app_title = "Upande Timaflor"
app_publisher = "newton@upande.com"
app_description = "ERPNext Implementation for Timaflor"
app_email = "newton@upande.com"
app_license = "mit"

# Apps
# ------------------
# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "upande_timaflor",
# 		"logo": "/assets/upande_timaflor/logo.png",
# 		"title": "Upande Timaflor", 
# 		"route": "/upande_timaflor",
# 		"has_permission": "upande_timaflor.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/upande_timaflor/css/upande_timaflor.css"
# app_include_js = "/assets/upande_timaflor/js/upande_timaflor.js"

# include js, css files in header of web template
# web_include_css = "/assets/upande_timaflor/css/upande_timaflor.css"
# web_include_js = "/assets/upande_timaflor/js/upande_timaflor.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "upande_timaflor/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "upande_timaflor/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
jinja = {
	"methods": "upande_timaflor.utils.jinja_methods",
	"filters": "upande_timaflor.utils.jinja_filters"
}

# JS file to override ERPNext's material_request.js
#app_include_js = {web": ["erpnext/public/js/material_request.js"]}

doctype_js = {
    "Material Request": "public/js/material_request.js"
}

# Fixtures
# --------
fixtures = [
    {
        "dt": "Server Script",
        "filters": [
            ["name", "in", [
                "get_latest_biometric_log"
            ]]
        ]
    },
    {
        "dt": "Client Script",
        "filters": [
            ["name", "in", [
                "Biometric Signature",
                "Material Assigned To Employee"
           ]]
        ]
    },
    {
        "dt": "Workspace",
        "filters": [
            ["name", "in", [
                "Production Manager Workspace",
                "PM Manufacturing",
                "PM Stock",
                "Storekeeper Workspace",
                "Stocks Workspace",
                "Accounting Workspace",
                "General Manager Home"
            ]]
        ]
    },
    {
        "dt": "DocType",
       "filters": [
            ["name", "in", [
                "Biometric Log",
                "Biometric Signature",
                "Assigned To Material",
                "Greenhouse",
                "Ordering Sheet",
                "Order Detail",
                "Order Quantity",
                "Daily Maximum Consumption",
                "Daily Minimum Consumption",
                "Fertilizer Order Sheet",
                "Fertilizer Stock Levels",
                "Chemical Stock Levels",
                "Chemical Order Sheet",
                "Chemical Order Quantity",
                "Area To Spray",
                "Chemical Sprays",
                "Fertilizer Average Consumption",
                "Stock Levels",
                "Quantity To Order",
                "Chemical Target"
            ]]
        ]
    }
]

# Installation
# ------------
# before_install = "upande_timaflor.install.before_install"
# after_install = "upande_timaflor.install.after_install"

# Uninstallation
# ------------
# before_uninstall = "upande_timaflor.uninstall.before_uninstall"
# after_uninstall = "upande_timaflor.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument
# before_app_install = "upande_timaflor.utils.before_app_install"
# after_app_install = "upande_timaflor.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument
# before_app_uninstall = "upande_timaflor.utils.before_app_uninstall"
# after_app_uninstall = "upande_timaflor.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config
# notification_config = "upande_timaflor.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways
# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes
# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Scheduled Tasks
# ---------------
# scheduler_events = {
# 	"all": [
# 		"upande_timaflor.tasks.all"
# 	],
# 	"daily": [
# 		"upande_timaflor.tasks.daily"
# 	],
# 	"hourly": [
# 		"upande_timaflor.tasks.hourly"
# 	],
# 	"weekly": [
# 		"upande_timaflor.tasks.weekly"
# 	],
# 	"monthly": [
# 		"upande_timaflor.tasks.monthly"
# 	],
# }

# Testing
# -------
# before_tests = "upande_timaflor.install.before_tests"

# Overriding Methods
# ------------------------------
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "upande_timaflor.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "upande_timaflor.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------
# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["upande_timaflor.utils.before_request"]
# after_request = ["upande_timaflor.utils.after_request"]

# Job Events
# ----------
# before_job = ["upande_timaflor.utils.before_job"]
# after_job = ["upande_timaflor.utils.after_job"]

# User Data Protection
# --------------------
# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------
# auth_hooks = [
# 	"upande_timaflor.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Document Events
# ---------------
doc_events = {
    "BOM": {
        "validate": ["upande_timaflor.utils.validate_bom"]
    }
}