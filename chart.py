import sys
import settings
import models.data
import datetime
from google.appengine.ext import db
sys.path.insert(0, settings.APP_ROOT_DIR + '/lib')
from graphy.backends import google_chart_api
from graphy import formatters
from graphy import line_chart

class SalesChart(object):
	def units_chart(self, pid):
		overall_chart = google_chart_api.LineChart()

		sales_query = db.Query(models.data.Sale)
		sales_query.filter('pid =', pid)
		sales_query.order('report_date')
		sales = []
		for sale in sales_query:
			sales.append([sale.income_units, sale.report_date])

		if len(sales) == 0: return (None, None)
		sales, dates = zip(*sales)

		# Make dates readable
		dates = [date.strftime('%d %b') for date in dates]

		# Add sales line
		overall_chart.AddLine(sales, width=line_chart.LineStyle.THICK, label='Sales')

		# Determine if an upgrades line needs to be drawn
		sales_start = sales_query.get().report_date
		# Use settings file as the definitive source of upgrade start date because iTunes Connect sometimes reports false upgrade numbers
		versions = settings.PRODUCTS[pid]['versions']
		upgrades = []
		if len(versions) > 1:
			# Convert to datetime to allow for timedelta calculation
			upgrades_start = datetime.datetime.combine(versions[1]['date'], datetime.time(sales_start.hour, sales_start.minute))
			difference_in_days = (upgrades_start - sales_start).days

			upgrades_query = db.Query(models.data.Upgrade)
			upgrades_query.filter('pid =', pid)
			upgrades_query.order('report_date')
			upgrades_query.filter('report_date >', upgrades_start)

			# Pad upgrades list with time before upgrade commenced
			for i in range(0, difference_in_days):
				upgrades.append(0)
			for upgrade in upgrades_query:
				upgrades.append(upgrade.income_units)
			# Add upgrades line
			overall_chart.AddLine(upgrades, width=line_chart.LineStyle.THICK, label='Upgrades')

		# Add horizontal labels
		max_num_horizontal_labels = 15
		segment_gap = 1
		if len(dates) > max_num_horizontal_labels:
			segment_gap = len(dates) / max_num_horizontal_labels

		overall_chart.bottom.min = 0
		overall_chart.bottom.max = max_num_horizontal_labels
		overall_chart.bottom.labels = dates
		overall_chart.bottom.labels = dates[::segment_gap]

		# Add vertical labels
		max_num_vertical_labels = 15

		max_sales = 0
		min_sales = 0
		max_upgrades = 0
		min_upgrades = 0
		if sales:
			max_sales = max(sales)
			min_sales = min(sales)
		if upgrades:
			max_upgrades = max(upgrades)
			min_upgrades = min(upgrades)

		overall_chart.left.max = max_upgrades if max_upgrades > max_sales else max_sales
		overall_chart.left.min = min_upgrades if min_upgrades < min_sales else min_sales
		vertical_labels = []
		segment_gap = overall_chart.left.max / max_num_vertical_labels
		for i in range(0, max_num_vertical_labels + 1):
			vertical_labels.append(i * segment_gap)
			if len(vertical_labels) == max_num_vertical_labels + 1: break

		overall_chart.left.labels = vertical_labels
		overall_chart.bottom.label_gridlines = True

		# Build concentrated chart if there is enough data for one
		concentrated_chart = self.concentrated_units_chart(sales, upgrades, dates)
		if concentrated_chart != None:
			concentrated_chart = concentrated_chart.display.Url(1000, 300)

		return (overall_chart.display.Url(1000, 300), concentrated_chart)

	def concentrated_units_chart(self, sales, upgrades, dates):
		# Want results for the last 2 weeks
		concentrated_result_set_num = 14
		concentrated_chart = None
		if len(sales) > concentrated_result_set_num:
			concentrated_chart = google_chart_api.LineChart()
			# Slice to create the line for the concentrated chart
			calc_concentrated_result_set = lambda x: x[len(sales) - concentrated_result_set_num :len(sales)]
			sales_concentrated = calc_concentrated_result_set(sales)
			dates_concentrated = calc_concentrated_result_set(dates)
			upgrades_concentrated = calc_concentrated_result_set(upgrades)

			concentrated_chart.AddLine(sales_concentrated, width=line_chart.LineStyle.THICK, label='Sales')
			if len(upgrades_concentrated) == concentrated_result_set_num - 1:
				concentrated_chart.AddLine(upgrades_concentrated, width=line_chart.LineStyle.THICK, label='Upgrades')

			concentrated_chart.left.min = 0
			max_upgrades_concentrated = 0
			max_sales_concentrated = 0
			if upgrades_concentrated:
				max_upgrades_concentrated = max(upgrades_concentrated)
			if sales_concentrated:
				max_sales_concentrated = max(sales_concentrated)

			concentrated_chart.left.max = max_upgrades_concentrated if max_upgrades_concentrated > max_sales_concentrated else max_sales_concentrated
			segment_gap = concentrated_chart.left.max / concentrated_result_set_num
			concentrated_vertical_labels = []

			for i in range(0, concentrated_result_set_num + 1):
				concentrated_vertical_labels.append(i * segment_gap)
				if len(concentrated_vertical_labels) == concentrated_result_set_num + 1: break
			if concentrated_vertical_labels[-1] < concentrated_chart.left.max:
				new_max = concentrated_vertical_labels[-1] + segment_gap
				concentrated_vertical_labels.append(new_max)
				concentrated_chart.left.max = new_max

			concentrated_chart.left.labels = concentrated_vertical_labels
			concentrated_chart.bottom.labels = dates_concentrated
			concentrated_chart.left.label_gridlines = True
			concentrated_chart.bottom.label_gridlines = True
			return concentrated_chart
		else:
			return None


