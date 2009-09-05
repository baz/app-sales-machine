App Sales Machine is a Google App Engine application which does the following:
1. Imports a tarball of your existing sales reports and stores them in the datastore.
2. Logs into iTunes Connect every morning, downloads your latest sales report and stores it in the datastore.
3. Parses the downloaded report and stores the parsed data in the datastore.
4. Converts the reported income revenue of your sales to a configurable currency and stores that.
5. Pulls the rankings for your app every 8 hours (configurable) and stores that in the datastore.
6. Emails a report to a select group of recipients every morning with the latest cumulative figures, as well as the last downloaded report's figures.

For more information and instructions on how to install App Sales Machine see [this blog post](http://www.oiledmachine.com/posts/2009/09/05/app-sales-machine.html).
