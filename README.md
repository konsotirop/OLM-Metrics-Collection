# OLM Tableau Datasource
Create or update a datasource that contains OLM week by week growth metrics to be visualized with Tableau.

A short summary of what Tableau is, how to request for a viewer's/editor's permission, how to view Red Hat's tableaus, as well what metrics are considered important by the OLM team to be included in Tableau can be found here:
https://docs.google.com/document/d/1OqxHeFBOw5X0SYlbqUgtC84Vdou0qjI8YT4AQcp8lhk/edit?usp=sharing

For using the current datasouce, one needs to follow the instructions as outlined here (especially in the "Programmatic Access" section):
https://help.datahub.redhat.com/docs/interacting-with-telemetry-data

More precisely:

* Install the [Prometheus API client](https://github.com/prometheus/client_python)
* Update the "credentials.yaml" file with a personal access token.
    * A temporary one that expires in ~24hrs can be obtained by login to:
    https://datahub.psi.redhat.com/console/catalog and choosing the "Copy Login Command" option
    from the dropwdown menu.
    * Otherwise one needs to request a service token for long-lived applications.

Metrics and queries:
* The metrics to be collected every week are specified in the [hybrid_queries.yaml](hybrid_queries.yaml) file. This file also includes the relevant PromQL queries.
As most OLM specific metrics involve joins over multiple metrics, that usually result in timeouts, the file [smaller_queries.yaml](smaller_queries2.yaml) decomposes those
into simple queries (without joins) that are later joined together using Pandas Dataframes.

Steps before running the script:
1. Install gspread, a module for Google Sheets that supports reading, editing and sharing a spreadsheet:

```bash
$ pip install gspread
```

2. Install df2gspread, a module that transforms Pandas dataframes into Google Spreadsheets and vice versa.

```bash
$ pip install df2gspread
```

To run the above code one should simply run:
```bash
python src/olm_datasource_generator.py -d mmddyyyy
```
Where the date is the last date up to (without including) metrics will be collected for
a period of one week.

By default new weekly data are NOT saved, neither uploaded to GSheets spreadsheet. If one wants to do so,
should add the -s parameter using either "y" or "yes" as argument.
```bash
python src/olm_datasource_generator.py -d mmddyyyy -s y
```

Afterwards, a file called `OLM_weekly_prometheus.csv` will be updated (or created if it does not currently exists).

Moreover, results are synced with a Google Sheet worksheet that will eventually be used as a datasource for Tableaux.
Code is based on this example: https://www.danielecook.com/from-pandas-to-google-sheets/
that also contains links on how to use Google's API to link to spreadsheets.
