from datetime import date, datetime, timedelta
import mysql.connector
import requests
import os
import unicodedata
import glob
import re
from bs4 import BeautifulSoup

OUT_DIR = 'tmp'

CONFIG = {
  'user': 'sqluser',
  'password': 'sqluserpw',
  'host': '127.0.0.1',
  'database': 'haveiseenit',
  'raise_on_warnings': True
}

SERIES = {
	'elementary' : { 'name': 'Elementary', 'imdb_id': 'tt2191671' },
	'criminal_minds' : { 'name': 'Criminal Minds', 'imdb_id': 'tt0452046' },
	'hawaii_5_0' : { 'name': 'Hawaii 5.0', 'imdb_id': 'tt1600194' },
}


IMDB_LANDING_URL = 'http://www.imdb.com/title/%s'
IMDB_EPISODES_URL = 'http://www.imdb.com/title/%s/episodes'

class Episode():
	def __init__(self, imdb_id, season_nr, episode_nr, airdate, title, desc):
		self.imdb_id = imdb_id
		self.season_nr = season_nr
		self.episode_nr = episode_nr
		self.airdate = airdate
		self.title = title
		self.desc = desc

	def __repr__(self):
		return str(self.episode_nr) + ' - ' + self.title

def insert_series(conn, cursor, series):
	insert_series_stmt = (
		"INSERT INTO series (imdb_id, name) "
		"SELECT %(imdb_id)s, %(name)s "
		"ON DUPLICATE KEY UPDATE imdb_id=imdb_id;")
	cursor.execute(insert_series_stmt, series)
	conn.commit()

def insert_episode(conn, cursor, episode):
	insert_episode_stmt2 = (
		"INSERT INTO episodes (season, episode, title, airdate, description) "
		"SELECT %(season)s, %(episode)s, %(title)s, %(airdate)s, %(desc)s ")

	insert_episode_stmt = (
		"INSERT INTO episodes (series_id, season, episode, title, airdate, description) "
		"SELECT series.id, %(season)s, %(episode)s, %(title)s, %(airdate)s, %(desc)s "
		"FROM series WHERE series.imdb_id = %(imdb_id)s "
		"ON DUPLICATE KEY UPDATE title=%(title)s, airdate=%(airdate)s, description=%(desc)s;")
	
	cursor.execute(insert_episode_stmt, {
		'imdb_id': episode.imdb_id,
		'season': episode.season_nr,
		'episode': episode.episode_nr,
		'title': episode.title,
		'airdate': episode.airdate,
		'desc': episode.desc,
		})
	conn.commit()

def safe_mkdir(path):
	try:
		os.mkdir(path)
	except OSError:
		pass

def parse_data():
	add_series()
	pass

def downloaded_seasons(name):
	# returns all the seasons we've downloaded for the given series
	re_series = re.compile('(.+)_.+_(\d+)')
	seasons = set()
	for f in glob.glob(os.path.join(OUT_DIR, name + '_season_*')):
		_, filename = os.path.split(f)
		m = re_series.match(filename)
		if m:
			name = m.groups()[0]
			seasons.add(int(m.groups()[1]))
	return seasons

def download_raw_data(force = False, update = False):
	safe_mkdir(OUT_DIR)
	for k, v in SERIES.iteritems():
		id = v['imdb_id']
		name = v['name']
		# check if we've already downloaded the landing page
		body = None
		ff = os.path.join(OUT_DIR, id)
		if os.path.exists(ff):
			print 'Using existing landing page for : %s' % name
			body = open(ff).read()
		else:
			print 'Fetching: %s' % name
			# download series landing page, and get # seasons
			url = IMDB_LANDING_URL % id
			r = requests.get(url)
			body = r.content
			open(ff, 'wt').write(body)

		soup = BeautifulSoup(body)
		# extract the episode links. this is based on the current
		# imdb page layout, so it miiight break in the future
		num_seasons = None
		try:
			tmp = soup.select('.seasons-and-year-nav')
			divs = tmp[0].select('div')
			div3 = divs[2]
			episode_links = div3.select('a')
			num_seasons = len(episode_links)
			print 'Num seasons: %d' % num_seasons

			if not num_seasons:
				print 'Unable to parse #seasons. Skipping'
				continue

			v['num_seasons'] = num_seasons
			seasons = downloaded_seasons(k)

			url = IMDB_EPISODES_URL % id

			# download any seasons we don't have (as well as the last one)
			for i in range(1, num_seasons+1):
				if i not in seasons or (update and i == num_seasons) or force:
					s = str(i)
					payload = { 'season': s}
					r = requests.get(url, params=payload)
					p = os.path.join(OUT_DIR, k + '_season_' + s)
					open(p, 'wt').write(r.content)
					print 'Downloading season: %d' % i

		except:
			print 'Error parsing landing page. Skipping'

def get_first(tag, css_path):
	tmp = tag.select(css_path)
	if len(tmp) == 0:
		return None
	return tmp[0]

def parse_season(text, imdb_id, season_nr):
	episodes = []
	soup = BeautifulSoup(text)
	for x in soup.select('#episodes_content > div.clear > div.list.detail.eplist'):
		for y in x.select('div.info'):
			# grab the episode nr
			episode_nr = None
			tmp = get_first(y, 'meta')
			if tmp:
				episode_nr = tmp.get('content', None)

			# grab air date
			airdate = None
			tmp = get_first(y, 'div.airdate')
			if tmp:
				# strip any whitespace and convert 'Sep.' to 'Sep'
				tmp = str(tmp.contents[0]).strip()
				if len(tmp) > 0:
					tmp = tmp.replace('.', '')
					airdate = datetime.strptime(tmp, '%d %b %Y')

			# title
			title = None
			tmp = get_first(y, 'strong > a')
			if tmp:
				title = unicodedata.normalize('NFKD', tmp.contents[0]).encode('ascii','ignore').strip()

			# description
			desc = None
			tmp = get_first(y, 'div.item_description')
			if tmp:
				desc = unicodedata.normalize('NFKD', tmp.contents[0]).encode('ascii','ignore').strip()

			if episode_nr and airdate and title:
				episode = Episode(imdb_id, season_nr, episode_nr, airdate, title, desc)
				episodes.append(episode)
			else:
				print "Unable to parse episode: %s" % episode_nr

	return episodes

def add_episodes(series_name):

	conn = mysql.connector.connect(**CONFIG)
	cursor = conn.cursor()

	s = SERIES.get(series_name, None)
	if not s:
		print 'unable to find "%s"' % series_name

	num_seasons = s['num_seasons']
	imdb_id = s['imdb_id']
	for i in range(num_seasons):
		f = open(os.path.join(OUT_DIR, series_name + '_season_' + str(i+1))).read()
		episodes = parse_season(f, imdb_id, i+1)
		for ep in episodes:
			insert_episode(conn, cursor, ep)

	conn.close()

def add_all_episodes():
	for k, v in SERIES.iteritems():
		add_episodes(k)

def add_series():
	try:
		conn = mysql.connector.connect(**CONFIG)
		cursor = conn.cursor()

		for k, v in SERIES.iteritems():
			insert_series_stmt = (
				"INSERT INTO series (imdb_id, name, num_seasons) "
				"SELECT %(imdb_id)s, %(name)s, %(num_seasons)s "
				"ON DUPLICATE KEY UPDATE imdb_id=imdb_id;")
			cursor.execute(insert_series_stmt, v)
		conn.commit()

	except mysql.connector.Error as err:
		print 'error: ', err
		exit(1)

	conn.close()


def test_dump():
	r = open('tt2191671').read()
	soup = BeautifulSoup(r)
	tmp = soup.select('#title-episode-widget > div > div')
	episode_links = tmp[2].select('a') 
	print episode_links
	print len(episode_links)

download_raw_data()
add_series()
add_all_episodes()
