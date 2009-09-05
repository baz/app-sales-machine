from google.appengine.ext import db
import pickle
import StringIO


class AbstractReport(db.Model):
	income_revenue = db.FloatProperty()
	income_units = db.IntegerProperty()
	refund_loss = db.FloatProperty()
	refund_units = db.FloatProperty()
	pid = db.StringProperty(multiline=False)
	report_date = db.DateTimeProperty()
	date_created = db.DateTimeProperty(auto_now_add=True)

	# Intended to store dictionaries, but can store any object
	# See: http://appengine-cookbook.appspot.com/recipe/how-to-put-any-python-object-in-a-datastore
	_revenue_by_currency = db.BlobProperty()
	def _set_revenue_by_currency(self, x):
		f = StringIO.StringIO()
		pickle.dump(x, f)
		self._revenue_by_currency = db.Blob(f.getvalue())

	revenue_by_currency = property(lambda self:pickle.load(StringIO.StringIO(self._revenue_by_currency)), _set_revenue_by_currency)

	_units_by_country = db.BlobProperty()
	def _set_units_by_country(self, x):
		f = StringIO.StringIO()
		pickle.dump(x, f)
		self._units_by_country = db.Blob(f.getvalue())
   
	units_by_country = property(lambda self:pickle.load(StringIO.StringIO(self._revenue_by_currency)), _set_units_by_country)


class Sale(AbstractReport):
	pass

class Upgrade(AbstractReport):
	pass

class Ranking(db.Model):
	date_created = db.DateTimeProperty(auto_now_add=True)
	pid = db.StringProperty(multiline=False)
	category = db.StringProperty(multiline=False)
	country = db.StringProperty(multiline=False)
	ranking = db.IntegerProperty()
