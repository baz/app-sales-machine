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
		# iTunes Connect stores reports with a 1 day delay
		now = datetime.date.today()
		one_day = datetime.timedelta(days=1)
		yesterday = now - one_day
		yesterday = yesterday.strftime('%m/%d/%Y')
		try:
			latest_report = itcscrape.getLastDayReport(settings.SETTINGS['itunesconnect_username'], settings.SETTINGS['itunesconnect_password'], yesterday)
			report_persister.persist(latest_report['filename'], latest_report['content'])
		except:
			# Download failed (timeout or report not available yet)
			# Send email to administrator
			message = mail.EmailMessage(sender=settings.SETTINGS['admin_email_address'],
							   subject='[ASM] Report job failed for: ' + yesterday)
			message.to = settings.SETTINGS['admin_email_address']
			message.body = 'Failed to download the iTunes Connect sales report for: ' + yesterday
			message.send()

def main():
	application = webapp.WSGIApplication([('/jobs/pull_report', ReportJob)], debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()
