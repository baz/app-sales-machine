from google.appengine.ext import db
import models.raw_report
import models.data
import re
import settings
import hashlib
from processors import report_munger


def persist(filename, content):
	# Skip hidden files
	p = re.compile('\\..+')
	# Don't import weekly files because the parser does not recognise them
	if p.match(filename) is None and filename.find('Weekly') == -1:
		# Parse report
		parsed_data = report_munger.AppStoreSalesDataMunger().munge(content, settings.SETTINGS['base_currency'])
		date = parsed_data.keys()[-1]
		if persist_original_file(filename, date, content) != False:
			# Persist parsed data
			persist_parsed_data(parsed_data)

def persist_original_file(filename, date, content):
	# Check if the report already exists in the data store
	sha1 = hashlib.sha1(content).hexdigest()
	existing_report = db.GqlQuery("SELECT * FROM RawReport WHERE report_date = :1 AND sha1 = :2 LIMIT 1", date, sha1).get()

	if existing_report == None:
		report = models.raw_report.RawReport()
		report.filename = filename
		report.content = content
		report.sha1 = sha1
		report.report_date = date
		return report.put()
	else:
		return False

def persist_parsed_data(parsed_data):
	# Parsed data represents 1 daily report
	# Contains a dictionary with the first key being the date, and the value being another dictionary
	# This dictionary holds 2 keys: sales and upgrades
	# The values contain a list of products
	# Each product is represented by a dictionary
	date = parsed_data.keys()[-1]

	sales = parsed_data[date]['sales']
	upgrades = parsed_data[date]['upgrades']

	# Store sale and upgrade data in separate tables
	for product in sales:
		sale_store = models.data.Sale()
		_store_data(product, sale_store, date)
		sale_store.put()

	for product in upgrades:
		upgrade_store = models.data.Upgrade()
		_store_data(product, upgrade_store, date)
		upgrade_store.put()

def _store_data(product, store, date):
	store.income_revenue = float(product['incomeRevenue'])
	store.income_units = product['incomeUnits']
	store.revenue_by_currency = product['revenueByCurrency']
	store.units_by_country = product['unitsByCountry']
	store.refund_loss = float(product['refundLoss'])
	store.refund_units = float(product['refundUnits'])
	store.pid = product['pid']
	store.report_date = date
