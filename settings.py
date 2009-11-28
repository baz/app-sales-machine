import os
import datetime

APP_ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

SETTINGS = {
	# Company name appears on the admin page
	"company_name": "<<My iPhone Company>>",

	# Currency you would like your daily income revenue figures to be converted to
	"base_currency": "AUD",

	# This must be the email address of a registered administrator for the application due to mail API restrictions
	"admin_email_address": "My Name <sender@example.com>",
	
	# Don't change these
	"template_path": APP_ROOT_DIR + '/templates/',
	"upload_form_name": "file_upload",
}

ACCOUNTS = {
	# Your iTunes Connect credentials for the cron job to log in and download your reports daily
	# You can specify more than 1 account
	"<< Arbitrary account name >>": {
		"itunesconnect_username": "<<username>>",
		"itunesconnect_password": "<<password>>",
	}
}

PRODUCTS = {
	# SKU of the app when you uploaded it to the App Store
	"<<SKU>>": {
		# Human-readable app name which corresponds to the above SKU
		"name": "<<app name>>",

		# App ID (can be found from the GET param of your iTunes URL i.e. ?id=xxxxxxxxx)
		"app_id": "<<app id>>",

		# Make sure your category name and corresponding ID exists in jobs/app_store_codes.py
		"category_name": "<<category name>>",

		# Is your app free?
		"paid": False,

		# List of dictionaries which represent the human-readable version number and the date the version was released on the App Store
		"versions": [{'name': 'v1.0', 'date': datetime.date(2009, 6, 22)},
					{'name': 'v1.1', 'date': datetime.date(2009, 7, 18)}],

		# List of email addresses you would like the daily reports sent to
		"to_addresses": [
			'Recipient Name <recipient@example.com>',
		]
	}
}
