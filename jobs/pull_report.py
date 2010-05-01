import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import urlfetch
from google.appengine.api import mail

import datetime
import sys

from lib import itcscrape
import settings
from processors import report_persister


class ReportJob(webapp.RequestHandler):

	def get(self):
		date = self.request.get("date", None)
		# iTunes Connect stores reports with a 1 day delay
		if not date:
			now = datetime.date.today()
			one_day = datetime.timedelta(days=1)
			yesterday = now - one_day
			date = yesterday.strftime('%m/%d/%Y')
		print date
		# Fetch for all available accounts
		for account_name in settings.ACCOUNTS:
			#try:
			latest_report = itcscrape.getLastDayReport(settings.ACCOUNTS[account_name]['itunesconnect_username'], settings.ACCOUNTS[account_name]['itunesconnect_password'], date)
			report_persister.persist(latest_report['filename'], latest_report['content'])
			#except:
				## Download failed (timeout or report not available yet)
				## Send email to administrator
				#message = mail.EmailMessage(sender=settings.SETTINGS['admin_email_address'],
								   #subject='[ASM] Report job failed for account: ' + account_name)
				#message.to = settings.SETTINGS['admin_email_address']
				#message.body = 'Failed to download the iTunes Connect sales report for: ' + date
				#message.send()

def main():
	application = webapp.WSGIApplication([
		('/jobs/pull_report', ReportJob)
	], debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()
