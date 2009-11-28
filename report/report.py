import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.ext.webapp import template

import csv
import StringIO
import datetime
import settings
import os
import urllib
import models.data


def fetch_reports(app_name, format_date=True):
	app_name = urllib.unquote(app_name)
	products = settings.PRODUCTS.keys()
	# Find the product ID for the provided application name
	found = False
	for pid in products:
		product_name = settings.PRODUCTS[pid]['name']
		if product_name.lower() == app_name.lower():
			found = True
			break

	if found:
		# Retrieve the first 1000 records
		sales = db.Query(models.data.Sale)
		sales.filter('pid =', pid)
		sales.order('-report_date')

		upgrades = db.Query(models.data.Upgrade)
		upgrades.filter('pid =', pid)
		upgrades.order('-report_date')

		return group_reports({'sales': sales, 'upgrades': upgrades}, format_date)
	else:
		return None

def group_reports(reports, format_date=True):
	if reports != None:
		# Create dictionary of upgrades for later lookup
		upgrade_dict = {}
		for upgrade in reports['upgrades']:
			upgrade_dict[upgrade.report_date] = upgrade.income_units

		grouped = []
		for sale in reports['sales']:
			upgrades = ''
			if sale.report_date in upgrade_dict:
				upgrades = upgrade_dict[sale.report_date]
			else:
				upgrades = '-'
			report_date = sale.report_date.strftime('%a, %b %d, %y') if format_date else sale.report_date
			grouped.append({'date': report_date, 'profit': sale.income_revenue, 'sales': sale.income_units, 'upgrades': upgrades})
		return grouped
	else:
		return None


class CSVReport(webapp.RequestHandler):

	def get(self):
		app_name = self.request.path.split('/')[-1]
		reports = fetch_reports(app_name, False)
		filename = app_name.replace('.', '_') + '_' + datetime.datetime.now().strftime('%Y%m%d') + '.csv'
		csv_file = StringIO.StringIO()
		csv_writer = csv.writer(csv_file, delimiter='\t', quotechar='|', quoting=csv.QUOTE_MINIMAL)
		csv_writer.writerow(['Date', 'Profit', 'Sales', 'Upgrades'])
		for day in reports:
			csv_writer.writerow([day['date'].strftime('%F'), day['profit'], day['sales'], day['upgrades']])
		self.response.headers['Content-Type'] = 'text/csv'
		self.response.out.write(csv_file.getvalue())


class HTMLReport(webapp.RequestHandler):

	def get(self):
		app_name = self.request.path.split('/')[-1]
		reports = fetch_reports(app_name)

		template_values = {
			'company_name': settings.SETTINGS['company_name'],
			'reports': reports,
			'page_name': 'Report',
			}

		template_path = os.path.join(settings.SETTINGS['template_path'], 'html_report.html')
		self.response.out.write(template.render(template_path, template_values))

def main():
	application = webapp.WSGIApplication([('/report/csv/.*', CSVReport),
									  		('/report/html/.*', HTMLReport)], debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()
