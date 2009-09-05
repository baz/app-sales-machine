from google.appengine.ext import db
import models.data


def persist_ranking(pid, value, country, category):
	ranking = models.data.Ranking()
	ranking.pid = pid
	ranking.category = category
	ranking.country = country
	ranking.ranking = value
	return ranking.put()
