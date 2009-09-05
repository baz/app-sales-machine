import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext.webapp.util import login_required
from google.appengine.api.labs import taskqueue
import datetime
import string
import locale

import settings
import models.data


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
					'rankings': self._rankings_string(rankings),
					}

			email_body = self._email_body(product)

			subject = '%s %s App Store report' % (datetime.date.today().strftime('%Y%m%d'), product['name'])
			self.send_email(pid, subject, email_body)

	def _total_income_units(self, reports):
		total = 0
		for report in reports:
			total += report.income_units
		return total

	def _email_body(self, product):
		body_template = string.Template("""Hello,

Here is your daily report for $name
--

Yesterday's ($sales_end) download figures:
	- $last_reported_sales_total

Yesterday's ($sales_end) upgrade figures:
	- $last_reported_upgrades_total

Total number of downloads ($sales_start to $sales_end):
	- $sales_total

Total number of upgrades ($upgrades_start to $upgrades_end):
	- $upgrades_total

Upgrade rate (over base of $upgrade_base):
	- $upgrade_rate

Approximate total income revenue ($currency):
	- $sales_total_revenue

Rankings (as of $rankings_pull_date UTC):

$rankings
""")
		return body_template.substitute(product)

	def _date_string(self, date):
		return date.strftime('%Y-%m-%d')

	def _format_number(self, number):
		locale.setlocale(locale.LC_ALL,"")
		return locale.format('%d', number, True)

	def _rankings_string(self, rankings):
		body = ''
		separator_width = 25
		header = 'Country'.ljust(separator_width, ' ') + 'Category'.ljust(separator_width, ' ') + 'Ranking'.ljust(separator_width, ' ')
		body += '\t' + header + '\n'
		header_underline = '-------'.ljust(separator_width, ' ') + '--------'.ljust(separator_width, ' ') + '-------'.ljust(separator_width, ' ')
		body += '\t' + header_underline + '\n'
		for ranking in rankings:
			row = ranking['country'].ljust(separator_width, ' ') + ranking['category'].ljust(separator_width, ' ') + str(ranking['ranking']).ljust(separator_width, ' ')
			body += '\t' + row + '\n'
		return body

	def send_email(self, pid, subject, email_body):
		message = mail.EmailMessage(sender=settings.PRODUCTS[pid]['from_address'],
									subject=subject)
		message.to = settings.PRODUCTS[pid]['to_addresses']
		message.body = email_body
		message.send()


def main():
	application = webapp.WSGIApplication([('/jobs/email_report', EmailReport)], debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()
