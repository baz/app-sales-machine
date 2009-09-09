import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext.webapp.util import login_required
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp import template
import datetime
import string
import locale
import sys
import os

import settings
import models.data

# Append lib path to sys.path for Graphy
sys.path.insert(0, settings.APP_ROOT_DIR + '/lib')
from graphy.backends import google_chart_api
from graphy import formatters
from graphy import line_chart


class EmailReport(webapp.RequestHandler):

	def get(self):
		products = settings.PRODUCTS.keys()
		for pid in products:
			product_name = settings.PRODUCTS[pid]['name']

			# Start and end dates
			sales_query_asc = db.Query(models.data.Sale)
			sales_query_asc.filter('pid =', pid)
			sales_query_asc.order('report_date')
			if sales_query_asc.get() == None:
				continue
			sales_start = sales_query_asc.get().report_date
			sales_query_desc = db.Query(models.data.Sale)
			sales_query_desc.filter('pid =', pid)
			sales_query_desc.order('-report_date')
			sales_end = sales_query_desc.get().report_date

			# Total number of downloads
			sales_total = self._total_income_units(sales_query_asc)

			# Last reported date downloads
			sales_query_desc.filter('report_date =', sales_end)
			last_reported_sales_total = self._total_income_units(sales_query_desc)

			# Total sales income
			sales_total_revenue = 0
			for sale in sales_query_asc:
				sales_total_revenue += sale.income_revenue

			# Upgrades
			product_versions = settings.PRODUCTS[pid]['versions']
			upgrades_start = upgrades_end = upgrades_total = upgrade_rate = upgrade_base = last_reported_upgrades_total = 0
			if len(product_versions) > 1:
				upgrades_query = db.Query(models.data.Upgrade)
				upgrades_query.order('report_date')
				upgrades_query.filter('pid =', pid)
				upgrades_start = settings.PRODUCTS[pid]['versions'][-1]['date']
				upgrades_end = sales_end

				# Total number of upgrades
				upgrades_total = self._total_income_units(upgrades_query)

				# Last reported date upgrades
				upgrades_query.filter('report_date =', upgrades_end)
				last_reported_upgrades_total = self._total_income_units(upgrades_query)

				# Calculate upgrade rate from date of second release if there are only 2 releases
				if len(product_versions) == 2:
					sales_query_asc.filter('report_date <=', upgrades_start)
					upgrade_base = self._total_income_units(sales_query_asc)
					if upgrade_base == 0: upgrade_base = sales_total
				else:
					# There are more than 2 release so the best we can do is calculate an upgrade rate over all downloads
					upgrade_base = sales_total

				upgrade_rate = (1.0 * upgrades_total / upgrade_base) * 100

			# Rankings
			ranking_query = db.Query(models.data.Ranking)
			ranking_query.order('-date_created')
			ranking_query.filter('pid =', pid)
			last_pull = ranking_query.get()
			rankings = []
			last_pull_date = datetime.date.today()
			if last_pull != None:
				last_pull_date = last_pull.date_created
				# Look for rankings created within an hour range since the last pull
				difference = datetime.timedelta(hours=-1)
				one_hour_from_last_pull_date = last_pull_date + difference
				ranking_query.filter('date_created <=', last_pull_date)
				ranking_query.filter('date_created >=', one_hour_from_last_pull_date)
				for ranking in ranking_query:
					dict = {'country': ranking.country, 'category': ranking.category, 'ranking': ranking.ranking}
					rankings.append(dict)

			overall_chart_url, concentrated_chart_url = self.units_chart(pid)
			product = {
					'name': product_name,
					'last_reported_sales_total': last_reported_sales_total,
					'last_reported_upgrades_total': last_reported_upgrades_total,
					'sales_start': self._date_string(sales_start),
					'sales_end': self._date_string(sales_end),
					'sales_total': self._format_number(sales_total),
					'sales_total_revenue': sales_total_revenue,
					'upgrades_start': self._date_string(upgrades_start),
					'upgrades_end': self._date_string(upgrades_end),
					'upgrades_total': self._format_number(upgrades_total),
					'upgrade_rate': str(round(upgrade_rate, 2)) + '%',
					'upgrade_base': self._format_number(upgrade_base),
					'currency': settings.SETTINGS['base_currency'],
					'rankings_pull_date': last_pull_date,
					'rankings': rankings,
					'overall_chart_url': overall_chart_url,
					'concentrated_chart_url': concentrated_chart_url,
					}

			path = os.path.join(settings.SETTINGS['template_path'], 'report.html')
			email_body = template.render(path, product)

			subject = '%s %s App Store report' % (datetime.date.today().strftime('%Y%m%d'), product['name'])
			self.send_email(pid, subject, email_body)

	def _total_income_units(self, reports):
		total = 0
		for report in reports:
			total += report.income_units
		return total

	def _date_string(self, date):
		return date.strftime('%Y-%m-%d')

	def _format_number(self, number):
		locale.setlocale(locale.LC_ALL,"")
		return locale.format('%d', number, True)

	def units_chart(self, pid):
		overall_chart = google_chart_api.LineChart()

		sales_query = db.Query(models.data.Sale)
		sales_query.filter('pid =', pid)
		sales_query.order('report_date')
		sales = []
		for sale in sales_query:
			sales.append([sale.income_units, sale.report_date])
		sales, dates = zip(*sales)

		# Make dates readable
		dates = [date.strftime('%d %b') for date in dates]

		# Add sales line
		overall_chart.AddLine(sales, width=line_chart.LineStyle.THICK, label='Sales')

		# Determine if an upgrades line needs to be drawn
		sales_start = sales_query.get().report_date
		# Use settings file as the definitive source of upgrade start date because iTunes Connect sometimes reports false upgrade numbers
		versions = settings.PRODUCTS[pid]['versions']
		if len(versions) > 1:
			# Convert to datetime to allow for timedelta calculation
			upgrades_start = datetime.datetime.combine(versions[1]['date'], datetime.time(sales_start.hour, sales_start.minute))
			difference_in_days = (upgrades_start - sales_start).days

			upgrades_query = db.Query(models.data.Upgrade)
			upgrades_query.filter('pid =', pid)
			upgrades_query.order('report_date')
			upgrades_query.filter('report_date >', upgrades_start)
			upgrades = []

			# Pad upgrades list with time before upgrade commenced
			for i in range(0, difference_in_days):
				upgrades.append(0)
			for upgrade in upgrades_query:
				upgrades.append(upgrade.income_units)

			# Add upgrades line
			overall_chart.AddLine(upgrades, width=line_chart.LineStyle.THICK, label='Upgrades')

		# Add horizontal labels
		max_num_horizontal_labels = 15
		segment_gap = 1
		if len(dates) > max_num_horizontal_labels:
			segment_gap = len(dates) / max_num_horizontal_labels

		overall_chart.bottom.min = 0
		overall_chart.bottom.max = max_num_horizontal_labels
		overall_chart.bottom.labels = dates
		overall_chart.bottom.labels = dates[::segment_gap]

		# Add vertical labels
		max_num_vertical_labels = 15
		overall_chart.left.min = 0
		overall_chart.left.max = max(upgrades) if max(upgrades) > max(sales) else max(sales)
		vertical_labels = []
		segment_gap = overall_chart.left.max / max_num_vertical_labels
		for i in range(0, max_num_vertical_labels + 1):
			vertical_labels.append(i * segment_gap)
			if len(vertical_labels) == max_num_vertical_labels + 1: break

		overall_chart.left.labels = vertical_labels
		overall_chart.bottom.label_gridlines = True

		# Build concentrated chart if there is enough data for one
		concentrated_chart = self.concentrated_units_chart(sales, upgrades, dates)
		if concentrated_chart != None:
			concentrated_chart = concentrated_chart.display.Url(1000, 300)

		return (overall_chart.display.Url(1000, 300), concentrated_chart)

	def concentrated_units_chart(self, sales, upgrades, dates):
		# Want results for the last 2 weeks
		concentrated_result_set_num = 14
		concentrated_chart = None
		if len(sales) > concentrated_result_set_num:
			concentrated_chart = google_chart_api.LineChart()
			# Slice to create the line for the concentrated chart
			calc_concentrated_result_set = lambda x: x[len(sales) - concentrated_result_set_num :len(sales)]
			sales_concentrated = calc_concentrated_result_set(sales)
			dates_concentrated = calc_concentrated_result_set(dates)
			upgrades_concentrated = calc_concentrated_result_set(upgrades)

			concentrated_chart.AddLine(sales_concentrated, width=line_chart.LineStyle.THICK, label='Sales')
			if len(upgrades_concentrated) == concentrated_result_set_num - 1:
				concentrated_chart.AddLine(upgrades_concentrated, width=line_chart.LineStyle.THICK, label='Upgrades')

			concentrated_chart.left.min = 0
			concentrated_chart.left.max = max(upgrades_concentrated) if max(upgrades_concentrated) > max(sales_concentrated) else max(sales_concentrated)
			segment_gap = concentrated_chart.left.max / concentrated_result_set_num
			concentrated_vertical_labels = []

			for i in range(0, concentrated_result_set_num + 1):
				concentrated_vertical_labels.append(i * segment_gap)
				if len(concentrated_vertical_labels) == concentrated_result_set_num + 1: break
			if concentrated_vertical_labels[-1] < concentrated_chart.left.max:
				new_max = concentrated_vertical_labels[-1] + segment_gap
				concentrated_vertical_labels.append(new_max)
				concentrated_chart.left.max = new_max

			concentrated_chart.left.labels = concentrated_vertical_labels
			concentrated_chart.bottom.labels = dates_concentrated
			concentrated_chart.left.label_gridlines = True
			concentrated_chart.bottom.label_gridlines = True
			return concentrated_chart
		else:
			return None

	def send_email(self, pid, subject, email_body):
		message = mail.EmailMessage(sender=settings.PRODUCTS[pid]['from_address'],
									subject=subject)
		message.to = settings.PRODUCTS[pid]['to_addresses']
		message.html = email_body
		message.send()


def main():
	application = webapp.WSGIApplication([('/jobs/email_report', EmailReport)], debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()
