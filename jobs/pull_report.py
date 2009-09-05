import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import urlfetch
from google.appengine.api.labs import taskqueue
import datetime
import sys

from lib import itcscrape
import settings
from processors import report_persister


class ReportJob(webapp.RequestHandler):

	def get(self):
		try:
			# iTunes Connect stores reports with a 1 day delay
			now = datetime.date.today()
			one_day = datetime.timedelta(days=1)
			yesterday = now - one_day
			yesterday = yesterday.strftime('%m/%d/%Y')
			latest_report = itcscrape.getLastDayReport(settings.SETTINGS['itunesconnect_username'], settings.SETTINGS['itunesconnect_password'], yesterday)
			report_persister.persist(latest_report['filename'], latest_report['content'])
		except urlfetch.DownloadError:
			# Download failed most likely due to a timeout
			# Add to the task queue to keep trying to download the report
			taskqueue.add(url='/jobs/pull_report', method='GET')

def main():
	application = webapp.WSGIApplication([('/jobs/pull_report', ReportJob)], debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()
