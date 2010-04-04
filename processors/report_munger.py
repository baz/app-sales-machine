import sys, os, time
import urllib, urllib2
import datetime
import StringIO
import csv, decimal
import xml.dom.minidom	#Used for currency converter
from google.appengine.api import urlfetch

# Munging code taken and modified from http://www.rogueamoeba.com/utm/2009/05/04/itunesconnectarchiver/
# Thanks RA!


class AppStoreSalesDataMunger(object):

	def _combineDayData( self, rowSet ):
	
		combinedData = {}
	
		nonRefundRows = [row for row in rowSet if row['units'] >= 0]
		refundRows = [row for row in rowSet if row['units'] < 0]
	
		totalRevenue = 0
		for row in nonRefundRows:
			totalRevenue += (row['priceInSellerCurrency'] * row['units'])
		combinedData['incomeRevenue'] = totalRevenue
	
		totalUnits = sum( [row['units'] for row in rowSet] )
		combinedData['incomeUnits'] = totalUnits
		
		unitsByCountry = {}
		for row in nonRefundRows:
			countryCode = row['country']
			countryTotal = unitsByCountry.get( countryCode, 0 )
			countryTotal += row['units']
			unitsByCountry[countryCode] = countryTotal
		combinedData['unitsByCountry'] = unitsByCountry
		
		revenueByCurrency = {}
		for row in nonRefundRows:
			currencyType = row['buyerCurrencyType']
			currencyTotal = revenueByCurrency.get( currencyType, 0 )
			currencyTotal += (row['priceInBuyerCurrency'] * row['units'])
			revenueByCurrency[currencyType] = currencyTotal
		combinedData['revenueByCurrency'] = revenueByCurrency
		
		if len(refundRows):
			totalRefundsLoss = 0
			for row in refundRows:
				totalRefundsLoss += (row['priceInSellerCurrency'] * row['units'])
			combinedData['refundLoss'] = totalRefundsLoss
			
			totalRefundsUnits = 0
			for row in refundRows:
				totalRefundsUnits += row['units']
			combinedData['refundUnits'] = totalRefundsUnits
		else:
			combinedData['refundLoss'] = 0
			combinedData['refundUnits'] = 0
		
		return combinedData

	def munge(self, day, currency ):
		### First pass, toss everything we don't need and dictionarize
		daySalesRows = []
		dayUpgradeRows = []
		currencyConverter = XavierMediaCurrencyConverter()
		reader = csv.reader( StringIO.StringIO(day), 'excel-tab' ) #This is probably overkill, but what the hell
		for row in reader:
			if not len(row):
				continue
			if row[0] != 'APPLE':
				continue

			rowFields = {}
			rowFields['productID']		= row[2]
			rowFields['date']			= time.strptime( row[11], '%m/%d/%Y' )
			rowFields['salesType']		= int(row[8], 16)
			rowFields['units']			= int(row[9])

			rowFields['buyerCurrencyType']		= row[15]
			rowFields['priceInBuyerCurrency']	= decimal.Decimal(row[10])
			rowFields['sellerCurrencyType']		= currency
			
			rowFields['priceInSellerCurrency'] = rowFields['priceInBuyerCurrency']
			rowFields['priceInSellerCurrency'] 	= \
				currencyConverter.convert( rowFields['buyerCurrencyType'], rowFields['sellerCurrencyType'], rowFields['date'], rowFields['priceInBuyerCurrency'] )

			rowFields['country']		= row[14]
			# Capture upgrade stats
			if rowFields['salesType'] == 7:
				dayUpgradeRows.append( rowFields )
			else:
				daySalesRows.append( rowFields )

		parsedSales = self._groupRowData( daySalesRows )
		parsedUpgrades = self._groupRowData( dayUpgradeRows )

		# Recover date
		date = parsedSales[-1]['date']
		if date == None:
			date = parsedUpgrades[-1]['date']
		date = datetime.datetime.strptime(date, '%Y-%m-%d')

		return {date: {'sales': parsedSales, 'upgrades': parsedUpgrades}}

	def _groupRowData(self, parsedData):
		### Group rows by date, and then product, and then process them
		allDates = set( [row['date'] for row in parsedData] )
		allProducts = set( [row['productID'] for row in parsedData] )

		products = []
		for date in allDates:
			for product in allProducts:
				subRows = [row for row in parsedData if row['date'] == date and row['productID'] == product]
				newRow = self._combineDayData( subRows )
				newRow['date'] = time.strftime('%Y-%m-%d', date )
				newRow['pid'] = product
				products.append(newRow)

		return products


class XavierMediaCurrencyConverter(object):

	__cachedTables = {} #We shared this between classes to save from hitting the webserver so hard

	def conversionTableForDate( self, date ):
		dateStr = time.strftime( '%Y/%m/%d', date )
		
		table = self.__cachedTables.get( dateStr, None )
		if table == None:
			table = []
			
			#We do little error checking here, because I'm not really in the mood to be paranoid
			#Should just wrap it in giant try: block at some point

			response = urlfetch.fetch(url='http://api.finance.xaviermedia.com/api/latest.xml',
							 method=urlfetch.GET,
							 deadline=10)
			xmlData = response.content

			xmlTree = xml.dom.minidom.parseString( xmlData )
			baseCurrency = xmlTree.getElementsByTagName('basecurrency')[0].firstChild.data
			fxElements = xmlTree.getElementsByTagName( 'fx' )
			for element in fxElements:
				targetCurrency = element.getElementsByTagName( 'currency_code' )[0].firstChild.data
				rate = decimal.Decimal( element.getElementsByTagName( 'rate' )[0].firstChild.data )
				
				entry = {'base': baseCurrency, 'target': targetCurrency, 'rate': rate }
				table.append( entry )
			
			self.__cachedTables[dateStr] = table
		
		return table
				
	def convert( self, startCurrency, targetCurrency, dateTuple, startAmount ):
		if startCurrency == targetCurrency:
			return startAmount
		if startAmount == 0:
			return startAmount
		
		conversionTable = self.conversionTableForDate( dateTuple )
		
		startEntry = [e for e in conversionTable if e['target'] == startCurrency][0]
		amountInStartBase = startAmount / startEntry['rate']

		endEntry = [e for e in conversionTable if e['target'] == targetCurrency][0]
		if endEntry['base'] != startEntry['base']: #Lots of code could handle this case
			return None

		amountInEndBase = endEntry['rate'] * amountInStartBase

		return amountInEndBase
