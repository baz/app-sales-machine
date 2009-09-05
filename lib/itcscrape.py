#!/usr/bin/python

'''
Scraper for iTunes Connect. Will download the last day's daily report.
Bugfixes gratefully accepted. Send to jamcode <james@jam-code.com>.

* Copyright (c) 2009, jamcode LLC
* All rights reserved.
*
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
*	  * Redistributions of source code must retain the above copyright
*		notice, this list of conditions and the following disclaimer.
*	  * Redistributions in binary form must reproduce the above copyright
*		notice, this list of conditions and the following disclaimer in the
*		documentation and/or other materials provided with the distribution.
*	  * Neither the name of the <organization> nor the
*		names of its contributors may be used to endorse or promote products
*		derived from this software without specific prior written permission.
*
* THIS SOFTWARE IS PROVIDED BY <copyright holder> ''AS IS'' AND ANY
* EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL <copyright holder> BE LIABLE FOR ANY
* DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
* ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

from google.appengine.api import urlfetch

import urllib, urllib2, sys, os, os.path, re, pprint, gzip, StringIO, getopt
import traceback
from datetime import datetime, timedelta
from BeautifulSoup import BeautifulSoup


baseURL = 'https://itts.apple.com'
refererURL = 'https://itts.apple.com/cgi-bin/WebObjects/Piano.woa'


def logMsg(m, v) :
	if v :
		print >> sys.stderr, m

def getLastDayReport(username, password, reportDate, verbose=False) :
	logMsg('Initialising session with iTunes connect...', verbose)
	
	s = urlfetch.fetch(url=refererURL,
							method=urlfetch.GET,
							deadline=10)

	logMsg('DONE', verbose)

	logMsg('Locating login form...', verbose)
	# Stop HTMLParser from complaining about the bad HTML on this page
	content = s.content.replace('</font />', '</font>')
	b = BeautifulSoup(content)
	form = b.findAll('form')[0]
	formArgs = dict(form.attrs)

	loginUrl = baseURL + formArgs['action']
	loginData = {
		'theAccountName' : username,
		'theAccountPW' : password,
		'1.Continue.x' : '36',
		'1.Continue.y' : '17',
		'theAuxValue' : ''
	}
	loginArgs = urllib.urlencode(loginData)
	logMsg('DONE', verbose)

	logMsg('Attempting to login to iTunes connect', verbose)
	h = urlfetch.fetch(url=loginUrl,
							method=urlfetch.POST,
							deadline=10,
				   			payload=loginArgs)

	# Stop HTMLParser from complaining about the bad HTML on this page
	content = h.content.replace('</font />', '</font>')
	b = BeautifulSoup(content)
	reportURL = baseURL + dict(b.findAll(attrs={'name' : 'frmVendorPage'})[0].attrs)['action']
	logMsg('DONE', verbose)

	logMsg('Fetching report form details...', verbose)
	reportTypeName = str(dict(b.findAll(attrs={'id' : 'selReportType'})[0].attrs)['name'])
	dateTypeName = str(dict(b.findAll(attrs={'id' : 'selDateType'})[0].attrs)['name'])

	'''
	Captured with Live HTTP Headers:
		9.7=Summary
		9.9=Daily
		hiddenDayOrWeekSelection=Daily
		hiddenSubmitTypeName=ShowDropDown
	'''

	reportData = [
		(reportTypeName, 'Summary'),
		(dateTypeName, 'Daily'),
		('hiddenDayOrWeekSelection', 'Daily'),
		('hiddenSubmitTypeName', 'ShowDropDown')
	]

	reportArgs = urllib.urlencode(reportData)
	h = urlfetch.fetch(url=reportURL,
							method=urlfetch.POST,
							deadline=10,
				   			payload=reportArgs)

	b = BeautifulSoup(h.content)

	reportURL = baseURL + dict(b.findAll(attrs={'name' : 'frmVendorPage'})[0].attrs)['action']

	# Don't know if these change between calls. Re-fetch them to be sure.
	reportTypeName = str(dict(b.findAll(attrs={'id' : 'selReportType'})[0].attrs)['name'])
	dateTypeName = str(dict(b.findAll(attrs={'id' : 'selDateType'})[0].attrs)['name'])
	dateName = str(dict(b.findAll(attrs={'id' : 'dayorweekdropdown'})[0].attrs)['name'])
	logMsg('DONE', verbose)


	logMsg("Fetching report for %s..." % reportDate, verbose)
	'''
	Captured with Live HTTP Headers:
		9.7=Summary
		9.9=Daily
		9.11.1=03%2F12%2F2009
		download=Download
		hiddenDayOrWeekSelection=03%2F12%2F2009
		hiddenSubmitTypeName=Download
	'''

	reportData = [
		(reportTypeName, 'Summary'),
		(dateTypeName, 'Daily'),
		(dateName, reportDate),
		('download', 'Download'),
		('hiddenDayOrWeekSelection', reportDate),
		('hiddenSubmitTypeName', 'Download')
	]

	reportArgs = urllib.urlencode(reportData)
	h = urlfetch.fetch(url=reportURL,
							method=urlfetch.POST,
							deadline=10,
				   			payload=reportArgs)

	# Un-gzipped automatically
	filename = h.headers['filename'].replace('.gz', '')
	return {'filename': filename, 'content': h.content}

def usage(executableName) :
	print >> sys.stderr, "Usage: %s -u <username> -p <password> [-d mm/dd/year]" % executableName

def main(args) :
	username, password, verbose = None, None, None
	try :
		opts, args = getopt.getopt(sys.argv[1:], 'vu:p:d:')
	except getopt.GetoptError, err :
		print >> sys.stderr, "Error: %s" % str(err)
		usage(os.path.basename(args[0]))
		sys.exit(2)

	# Get today's date by default. Actually yesterday's date
	reportDay = datetime.today() - timedelta(1)
	reportDate = reportDay.strftime('%m/%d/%Y')

	for o, a in opts :
		if o == '-u' : 
			username = a
		if o == '-p' :
			password = a
		if o == '-d' :
			reportDate = a
		if o == '-v' :
			verbose = True
	
	if None in (username, password) :
		print >> sys.stderr, "Error: Must set -u and -p options."
		usage(os.path.basename(args[0]))
		sys.exit(3)

	result = None
	if verbose :
		# If the user has specified 'verbose', just let the exception propagate
		# so that we get a stacktrace from python.
		result = getLastDayReport(username, password, reportDate, True)
	else :
		try :
			result = getLastDayReport(username, password, reportDate)
		except Exception, e :
			print >> sys.stderr, "Error: problem processing output. Check your username and password."
			print >> sys.stderr, "Use -v for more detailed information."

	print result

if __name__ == '__main__' :
	main(sys.argv)

