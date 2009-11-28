import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import urlfetch
from google.appengine.api.labs import taskqueue
import re
import string
import settings
import jobs.app_store_codes
from processors import ranking_persister


class RankingsJob(webapp.RequestHandler):

	def get(self):
		for pid in settings.PRODUCTS:
			paid = settings.PRODUCTS[pid]['paid']
			category = jobs.app_store_codes.CATEGORIES[settings.PRODUCTS[pid]['category_name']]
			if 'popId' not in category:
				category['popId'] = 30 if paid else 27
			# Queue requests for category rankings
			self.fetch_rankings(pid, category)

			# Queue requests for top 100 list
			if paid:
				self.fetch_rankings(pid, jobs.app_store_codes.CATEGORIES['Top 100 Paid'])
				# Queue requests for top grossing list
				self.fetch_rankings(pid, jobs.app_store_codes.CATEGORIES['Top Grossing'])
			else:
				self.fetch_rankings(pid, jobs.app_store_codes.CATEGORIES['Top 100 Free'])

	def fetch_rankings(self, pid, category):
		app_id = settings.PRODUCTS[pid]['app_id']

		# Fetch ranking in each country for the application's category
		# Break into queued tasks for offline, asychronous processing
		countries_per_task = 3
		count = 0
		store_ids_to_process = []
		for store_id in jobs.app_store_codes.COUNTRIES:
			count += 1
			store_ids_to_process.append(store_id)
			if self._is_int(1.0 * count / countries_per_task):
				# Enqueue task and reset list
				taskqueue.add(url='/jobs/pull_rankings/worker',
								method='POST',
								params={
										'pid': pid,
										'app_id': app_id,
										'store_ids': ','.join(map(str, store_ids_to_process)),
										'category_id': category['id'],
										'pop_id': category['popId'],
										})
				store_ids_to_process = []

	def _is_int(self, value):
		if int(value) == value:
			return True
		else:
			return False


class RankingsWorker(webapp.RequestHandler):

	def post(self):
		pid = self.request.get('pid')
		app_id = int(self.request.get('app_id'))
		store_ids = string.split(self.request.get('store_ids'), ',')
		category_id = int(self.request.get('category_id'))
		pop_id = int(self.request.get('pop_id'))

		for store_id in store_ids:
			ranking = self.category_ranking(app_id, int(store_id), category_id, pop_id)

			if ranking != None:
				# Store this ranking
				ranking_persister.persist_ranking(pid, ranking, jobs.app_store_codes.COUNTRIES[int(store_id)], self._category_for_id(category_id))

	def category_ranking(self, app_id, store_id, category_id, pop_id):
		# Append the store id to the URL because GAE caches the request otherwise
		url = "http://itunes.apple.com/WebObjects/MZStore.woa/wa/viewTop?id=%d&popId=%d&%d" % (category_id, pop_id, store_id)
		user_agent = "iTunes/4.2 (Macintosh; U; PPC Mac OS X 10.2"
		headers = {
					'User-Agent': user_agent,
					'X-Apple-Store-Front': "%d-1" % store_id,
					'Cache-Control': 'max-age=0',
				}
		response = urlfetch.fetch(url=url,
								method=urlfetch.GET,
								deadline=10,
								headers=headers)

		pattern = re.compile(r"buyParams=.+?Id=(\d+)")
		rankings = pattern.findall(response.content)

		rank = 0
		value = None
		for app in rankings:
			rank += 1
			if int(app) == app_id:
				value = rank
				break

		return value

	def _category_for_id(self, category_id):
		for key, value in jobs.app_store_codes.CATEGORIES.items():
			if value == category_id:
				return key
		return None


def main():
	application = webapp.WSGIApplication([('/jobs/pull_rankings', RankingsJob),
											('/jobs/pull_rankings/worker', RankingsWorker)], debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()
