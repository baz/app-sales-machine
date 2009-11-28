from google.appengine.ext import db

class RawReport(db.Model):
	filename = db.StringProperty(multiline=False)
	content = db.TextProperty()
	report_date = db.DateTimeProperty()
	sha1 = db.StringProperty(multiline=False)
	date_added = db.DateTimeProperty(auto_now_add=True)
