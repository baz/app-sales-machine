from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
import os
import cgi
import tarfile
import settings
from processors import report_persister
from chart import SalesChart

PAGE_NAME = 'Admin'
TEMPLATE_PATH = os.path.join(settings.SETTINGS['template_path'], 'admin.html')

class RootHandler(webapp.RequestHandler):

	@login_required
	def get(self):
		template_values = {
			'company_name': settings.SETTINGS['company_name'],
			'page_name': PAGE_NAME,
			'file_upload_name': settings.SETTINGS['upload_form_name'],
			}

		self.response.out.write(template.render(TEMPLATE_PATH, template_values))


class UploadHandler(webapp.RequestHandler):

	def post(self):
		file_data = self.request.POST[settings.SETTINGS['upload_form_name']].file
		tarball = tarfile.open(fileobj=file_data)
		for tarinfo in tarball:
			if tarinfo.isreg():
				# Persist original report and then persist the parsed contents of it
				file_buffer = tarball.extractfile(tarinfo).read()
				report_persister.persist(tarinfo.name, file_buffer)
		tarball.close()

		filename = self.request.POST[settings.SETTINGS['upload_form_name']].filename
		template_values = {
			'file_name': filename,
			'company_name': settings.SETTINGS['company_name'],
			'page_name': PAGE_NAME,
			'file_upload_name': settings.SETTINGS['upload_form_name'],
			}

		self.response.out.write(template.render(TEMPLATE_PATH, template_values))

class ChartHandler(webapp.RequestHandler):
	def get(self):
		pid = self.request.get("pid", None)
		if not pid:
			return
		overall_chart_url, concentrated_chart_url = SalesChart().units_chart(pid)

		self.response.out.write("<img src='%s'/>" % overall_chart_url)
