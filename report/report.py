import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.api import urlfetch


class CSVReport(webapp.RequestHandler):

	def get(self):
		pass

class ViewReport(webapp.RequestHandler):

	def get(self):
		pass

def main():
	application = webapp.WSGIApplication([('/report/csv/.*', CSVReport),
									  		('/report/view/.*', ViewReport)], debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()
