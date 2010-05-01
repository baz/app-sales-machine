#!/usr/bin/env python

import wsgiref.handlers
import os
import sys
import settings
from google.appengine.ext import webapp
 
# Force sys.path to have our own directory first, in case we want to import from it
sys.path.insert(0, settings.APP_ROOT_DIR)

from handlers import admin


def main():
	application = webapp.WSGIApplication([('/', admin.RootHandler),
											('/admin', admin.RootHandler),
											('/admin/upload', admin.UploadHandler),
                                            ('/admin/chart', admin.ChartHandler),
									  		], debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()
