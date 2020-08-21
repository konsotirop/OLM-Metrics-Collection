import argparse
import os
import yaml
from prom_connect import *
from datetime import datetime, timezone
import time
import urllib3
import pandas as pd
import csv
from prometheus_api_client import MetricSnapshotDataFrame as MSDF
from prometheus_api_client.exceptions import PrometheusApiClientException
import os.path
from multiprocessing import Process, Lock, Manager
import gspread
from df2gspread import df2gspread as d2g
from oauth2client.service_account import ServiceAccountCredentials
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def appendToCSV( final_results, save_data ):
    """
    Appends final aggregate results to existing ones
    If save_data flag is set, results are also exported
    as a csv file
    """
    # If file does not exist, write header
    if os.path.isfile('output/OLM_weekly_prometheus.csv'):
        write_header = False
    else:
        write_header = True
    if write_header:
        with open('output/OLM_weekly_prometheus.csv', 'a+', newline='') as olm_datasource:
            dict_writer = csv.DictWriter(olm_datasource, list(final_results.keys()))
            dict_writer.writeheader()
            dict_writer.writerow( final_results)
    else:
        # Append new data AND possibly new columns (measures) using pandas dataframes
        current_data = pd.read_csv('output/OLM_weekly_prometheus.csv', index_col=False)
        new_data = pd.DataFrame.from_dict( final_results )
        final_df = pd.concat([current_data, new_data], axis =0)
        # Sort by date
        #final_df = final_df.sort_values(by=['Date'])
        print(final_df.tail())
        # Write to CSV file
        if save_data:
            final_df.to_csv('output/OLM_weekly_prometheus.csv', index=False, sep=',')
    return 


def iter_pd(df):
    for val in df.columns:
        yield val
    for row in df.to_numpy():
        for val in row:
            if pd.isna(val):
                yield ""
            else:
                yield val

def uploadToGSheets():
    """
        Reads the produced csv files and uploads content to GSheets
    """
    # Set credentials
    scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'authentication/service_key.json', scope)
    gc = gspread.authorize(credentials)

    # Load pandas dataframe from CSV file
    df = pd.read_csv('output/OLM_weekly_prometheus.csv', index_col=False)
    
    # Upload data to Google Sheets
    spreadsheet_key = "XXXXXXXXXXXXXXXXXXXXXXXX"
    wks_name = "Sheet1"
    
    workbook = gc.open_by_key(spreadsheet_key)
    sheet = workbook.worksheet(wks_name)

    sheet.clear()
    (row,col) = df.shape

    cells = sheet.range("A1:{}".format(gspread.utils.rowcol_to_a1(row + 1, col)))
    for cell, val in zip(cells, iter_pd(df)):
        cell.value = val
    sheet.update_cells(cells)

def dateFormat(month, day, year):
    s_m = str(int(month))
    s_d  = str(int(day))
    s_y = str(year)
    return s_m + '/' + s_d + '/' + s_y

def add_offset(query, offset_hours):
    if offset_hours <= 0:
        return query
    left, middle, right = query.partition('1h:5m]')
    new_query = left + middle + ' offset {}h '.format(offset_hours) + right
    return new_query

def add_offset_point(query, offset_hours):
    if offset_hours <= 0:
        return query
    left, middle, right = query.partition('1s')
    new_query =left+'{}h'.format(offset_hours)+right
    return new_query

def consume_results(metric, query_result, partial_results):
    """
        Loads hourly results to pandas dataframe
    """
    if metric == "email_clusters":
        partial_results[metric] = MSDF( query_result ).drop(['value', 'timestamp'],axis=1)
    elif metric == "csv_operators":
        partial_results[metric] = MSDF( query_result ).drop(['value', 'timestamp'],axis=1)
    elif metric == "retired_operators":
        partial_results[metric] = MSDF( query_result ).drop(['value', 'timestamp'],axis=1)
    elif metric == "olm_operators":
        partial_results[metric] = MSDF( query_result ).drop(['value', 'timestamp'],axis=1)
    elif metric == "olm_retired":
        if query_result:
            partial_results[metric] = MSDF( query_result ).drop(['value', 'timestamp'],axis=1)
        else:
            partial_results[metric] = pd.DataFrame()
    elif metric == "clusters_cpu":
        temp_df = MSDF( query_result ).drop(['timestamp'],axis=1)
        temp_df['value'] = temp_df['value'].astype(float)
        partial_results[metric] = temp_df
        #partial_results[metric]['value'] = pd.to_numeric(partial_results[metric]['value'])
    elif metric == "clusters_nodes":
        temp_df = MSDF( query_result ).drop(['timestamp'],axis=1)
        temp_df['value'] = temp_df['value'].astype(float)
        partial_results[metric] = temp_df
        #partial_results[metric]['value'] = partial_results[metric]['value'].astype(float)
    elif metric == "clusters_ram":
        temp_df = MSDF( query_result ).drop(['timestamp'],axis=1)
        temp_df['value'] = temp_df['value'].astype(float)
        partial_results[metric] = temp_df
        #partial_results[metric]['value'] = partial_results[metric]['value'].astype(float)
    elif metric == "workload_cpu":
        temp_df = MSDF( query_result ).drop(['timestamp'],axis=1)
        temp_df['value'] = temp_df['value'].astype(float)
        partial_results[metric] = temp_df
    elif metric == "workload_ram":
        temp_df = MSDF( query_result ).drop(['timestamp'],axis=1)
        temp_df['value'] = temp_df['value'].astype(float)
        partial_results[metric] = temp_df
    else:
        pass
        #print("There is no handler for this metric, yet...")
    return

def get_final_results(metric, accumulated_results, final_results):
    """
    Calculates aggregate results for different metrics
    and stores in them in a python dictionary
    """
    print(metric)
    if metric == "total_customers":
        result = accumulated_results[metric].shape[0]
        final_results[metric] = [result]
        print("Value: {}".format(result))
    elif metric == "olm_customers":
        result = accumulated_results[metric].email_domain.nunique()
        final_results[metric] = [result]
        print("Value: {}".format(result))
    elif metric == "unique_operators":
        result = accumulated_results[metric].shape[0]
        final_results[metric] = [result]
        print("Value: {}".format(result))
    elif metric == "olm_clusters":
        print(accumulated_results[metric].shape)
        result = accumulated_results[metric]._id.nunique()
        final_results[metric] = [result]
        print("Value: {}".format(result))
    elif metric == "optional_clusters":
        result = accumulated_results[metric]._id.nunique()
        final_results[metric] = [result]
        print("Value: {}".format(result))
    elif metric == "olm_versions": # DEPRECATED
        pass
        #result = dict(accumulated_results[metric].version.value_counts())
        #for key,value in result.items():
        #    final_results[key+' version'] = [value]
        #print("Value: {}".format(result))
    elif metric == "avg_cpu_olm_clusters":
        result = accumulated_results[metric].mean(axis=0)['value']
        final_results[metric] = [result]
        print("Value: {}".format(result))
    elif metric == "avg_node_olm_clusters":
        result = accumulated_results[metric].mean(axis=0)['value']
        print("Value: {}".format(result))
        final_results[metric] = [result]
    elif metric == "avg_ram_olm_clusters":
        result = accumulated_results[metric].mean(axis=0)['value']
        final_results[metric] = [result]
        print("Value: {}".format(result))
    elif metric == "avg_cpu_optional_clusters":
        result = accumulated_results[metric].mean(axis=0)['value']
        print("Value: {}".format(result))
        final_results[metric] = [result]
    elif metric == "avg_node_optional_clusters":
        result = accumulated_results[metric].mean(axis=0)['value']
        print("Value: {}".format(result))
        final_results[metric] = [result]
    elif metric == "avg_ram_optional_clusters":
        result = accumulated_results[metric].mean(axis=0)['value']
        print("Value: {}".format(result))
        final_results[metric] = [result]
    elif metric == "workload_cpu_olm_clusters":
        result = accumulated_results[metric].mean(axis=0)['value']
        print("Value: {}".format(result))
        final_results[metric] = [result]
    elif metric == "workload_ram_olm_clusters":
        result = accumulated_results[metric].mean(axis=0)['value']
        print("Value: {}".format(result))
        final_results[metric] = [result]
    elif metric == "workload_cpu_optional_clusters":
        result = accumulated_results[metric].mean(axis=0)['value']
        print("Value: {}".format(result))
        final_results[metric] = [result]
    elif metric == "workload_ram_optional_clusters":
        result = accumulated_results[metric].mean(axis=0)['value']
        print("Value: {}".format(result))
        final_results[metric] = [result]
    elif metric == "olm_utilization_cpu":
        result = accumulated_results[metric].mean(axis=0)['value']
        print("Value: {}".format(result))
        final_results[metric] = [result]
    elif metric == "optional_utilization_cpu":
        result = accumulated_results[metric].mean(axis=0)['value']
        print("Value: {}".format(result))
        final_results[metric] = [result]
    elif metric == "olm_utilization_ram":
        result = accumulated_results[metric].mean(axis=0)['value']
        print("Value: {}".format(result))
        final_results[metric] = [result]
    elif metric == "optional_utilization_ram":
        result = accumulated_results[metric].mean(axis=0)['value']
        print("Value: {}".format(result))
        final_results[metric] = [result]
    elif metric == "operator_versions":
        # Drop id
        metric_df = accumulated_results[metric].drop(['_id'],axis=1)
        latest_version = metric_df.groupby(['name'])['version'].transform(max) == metric_df['version']
        result = ( latest_version.sum() / metric_df.shape[0] )*100
        print("Value: {}".format(result))
        final_results['latest_version'] = [result]
        final_df = accumulated_results[metric].groupby(['name','version']).size().reset_index(name='count')
        test_df = accumulated_results[metric].groupby(['name']).ngroups
    elif metric == "clusters_operators":
        metric_df = accumulated_results['operator_versions'].groupby(['_id']).size().reset_index(name='count')
        metric_df.dropna(inplace=True)
        print(metric_df.shape)
        avg_cluster = metric_df['count'].mean()
        # Clusters having exactly 1 operator installed
        one = metric_df.apply(lambda x: True if x['count'] == 1 else False, axis=1)
        clusters_one = len(one[one == True].index)
        # Clusters having 2-4 operators installed
        twoToFour = metric_df.apply(lambda x: True if (x['count'] >= 2 and x['count'] <= 5) else False, axis=1)
        clusters_twoToFour = len(twoToFour[twoToFour == True].index)
        # Clusters having >=5 and less than 10 operators installed
        fiveToNine = metric_df.apply(lambda x: True if (x['count'] > 5 and x['count'] <= 9) else False, axis=1)
        clusters_fiveToNine = len(fiveToNine[fiveToNine == True].index)
        # Clusters having >=10 operators installed
        moreTen = metric_df.apply(lambda x: True if x['count'] >= 10 else False, axis=1)
        clusters_moreTen = len(moreTen[moreTen == True].index)
        # Save above to final_results dictionary
        final_results['avg_cluster'] = [avg_cluster]
        final_results['clusters_one'] = [clusters_one]
        final_results['clusters_twoToFour'] = [clusters_twoToFour]
        final_results['clusters_fiveToNine'] = [clusters_fiveToNine]
        final_results['cluster_MoreTen'] = [clusters_moreTen]
        print("Avg: {}, 1: {}, 2-4: {}, 5-9:{}, 10+: {}".format(avg_cluster, clusters_one, clusters_twoToFour, clusters_fiveToNine, clusters_moreTen))
    else:
        pass
        #print("Metric not currently implemented...")
    return

def join_from_partial( metric, partial_results, reused_results, accumulated_results ):
    """
        Updates dataframes for metrics on an hourly basis
    """
    if metric == "total_customers":
        temp_df = partial_results['email_clusters'].drop(['_id'],axis=1)
        accumulated_results[metric] = accumulated_results[metric].append(temp_df).drop_duplicates()
    elif metric == "olm_customers":
        temp_df = partial_results["olm_operators"].loc[:,["_id"]].merge(partial_results["csv_operators"].loc[:,["_id"]], on="_id", how="inner").drop_duplicates()
        metric_df = temp_df.merge(partial_results["email_clusters"], on="_id", how="inner")
        accumulated_results[metric] = accumulated_results[metric].append(metric_df).drop_duplicates()
    elif metric == "unique_operators":
        # Keep only operators that have not been replaced
        temp_df = partial_results['csv_operators'][~partial_results['csv_operators'].isin(partial_results['retired_operators'])].dropna()
        temp_df['name'] = temp_df['name'].str.split('.').str[0]
        # Merge with package_server_clusters and email_customers
        temp_df = temp_df.merge(partial_results["olm_operators"]["_id"], on="_id", how="inner")
        temp_df = temp_df.merge(partial_results["email_clusters"], on="_id", how="inner")
        metric_df = temp_df.drop(['_id'],axis=1)
        accumulated_results[metric] = accumulated_results[metric].append(metric_df).drop_duplicates()
    elif metric == "olm_clusters":
        temp_df = partial_results['olm_operators'][['_id','name']][~partial_results['olm_operators'][['_id','name']].isin(partial_results['retired_operators'])].dropna()
        metric_df = temp_df.drop(['name'],axis=1)
        metric_df = metric_df.merge(partial_results["email_clusters"], on="_id", how="inner").drop(['email_domain'], axis=1) # Drop RedHat/IBM clusters
        accumulated_results[metric] = accumulated_results[metric].append(metric_df).drop_duplicates()
        reused_results['olm_clusters'] = metric_df
    elif metric == "optional_clusters":
        temp_df = partial_results['csv_operators'][~partial_results['csv_operators'].isin(partial_results['retired_operators'])].dropna()
        temp_df = temp_df.merge(partial_results["olm_operators"]["_id"], on="_id", how="inner")
        metric_df = temp_df.drop(['name'],axis=1)
        metric_df = metric_df.merge(partial_results["email_clusters"], on="_id", how="inner").drop(['email_domain'], axis=1) # Drop RedHat/IBM clusters
        accumulated_results[metric] = accumulated_results[metric].append(metric_df).drop_duplicates()
        reused_results['optional_clusters'] = metric_df
    elif metric == "olm_versions":
        temp_df = partial_results['olm_operators'][~partial_results['olm_operators'].isin(partial_results['olm_retired'])].dropna()
        temp_df = temp_df.merge(partial_results["email_clusters"], on="_id", how="inner").drop(['email_domain', 'name'], axis=1) # Drop RedHat/IBM clusters
        accumulated_results[metric] = (accumulated_results[metric].append(temp_df)).groupby(['_id'], as_index=False).max() # Keep only latest version
        #accumulated_results[metric].set_index(['_id', 'version'])
    elif metric == "avg_cpu_olm_clusters":
        reused_results['cpu_olm'] = partial_results['clusters_cpu'].merge(reused_results['olm_clusters'].loc[:,['_id']], on="_id", how="inner")
        indexNames = reused_results['cpu_olm'][ reused_results['cpu_olm']['value'] < 0 ].index
        reused_results['cpu_olm'].drop(indexNames , inplace=True)
        accumulated_results[metric] = accumulated_results[metric].append(reused_results['cpu_olm']).groupby(['_id'], as_index=False).mean() # Get average over time
        reused_results['cpu_olm'].set_index('_id', inplace=True)
    elif metric == "avg_cpu_optional_clusters":
        reused_results['cpu_optional'] = partial_results['clusters_cpu'].merge(reused_results['optional_clusters'].loc[:,['_id']], on="_id", how="inner")
        indexNames = reused_results['cpu_optional'][ reused_results['cpu_optional']['value']  < 0 ].index
        reused_results['cpu_optional'].drop(indexNames , inplace=True)
        accumulated_results[metric] = accumulated_results[metric].append(reused_results['cpu_optional']).groupby(['_id'], as_index=False).mean() # Get average over time
        reused_results['cpu_optional'].set_index('_id', inplace=True)
    elif metric == "avg_node_olm_clusters":
        temp_df = partial_results['clusters_nodes'].merge(reused_results['olm_clusters'].loc[:,['_id']], on="_id", how="inner")
        accumulated_results[metric] = accumulated_results[metric].append(temp_df).groupby(['_id'], as_index=False).mean() # Get average over time
    elif metric == "avg_node_optional_clusters":
        temp_df = partial_results['clusters_nodes'].merge(reused_results['optional_clusters'].loc[:,['_id']], on="_id", how="inner")
        accumulated_results[metric] = accumulated_results[metric].append(temp_df).groupby(['_id'], as_index=False).mean() # Get average over time
    elif metric == "avg_ram_olm_clusters":
        reused_results['ram_olm'] = partial_results['clusters_ram'].merge(reused_results['olm_clusters'].loc[:,['_id']], on="_id", how="inner")
        accumulated_results[metric] = accumulated_results[metric].append(reused_results['ram_olm']).groupby(['_id'], as_index=False).mean() # Get average over time
        reused_results['ram_olm'].set_index('_id', inplace=True)
    elif metric == "avg_ram_optional_clusters":
        reused_results['ram_optional'] = partial_results['clusters_ram'].merge(reused_results['optional_clusters'].loc[:,['_id']], on="_id", how="inner")
        accumulated_results[metric] = accumulated_results[metric].append(reused_results['ram_optional']).groupby(['_id'], as_index=False).mean() # Get average over time
        reused_results['ram_optional'].set_index('_id', inplace=True)
    elif metric == "workload_cpu_olm_clusters":
        reused_results['wkld_cpu_olm'] = partial_results['workload_cpu'].merge(reused_results['olm_clusters'].loc[:,['_id']], on="_id", how="inner")
        indexNames = reused_results['wkld_cpu_olm'][ reused_results['wkld_cpu_olm']['value'] < 0 ].index
        reused_results['wkld_cpu_olm'].drop(indexNames , inplace=True)
        accumulated_results[metric] = accumulated_results[metric].append(reused_results['wkld_cpu_olm']).groupby(['_id'], as_index=False).mean() # Get average over time
        reused_results['wkld_cpu_olm'].set_index('_id', inplace=True)
    elif metric == "workload_ram_olm_clusters":
        reused_results['wkld_ram_olm'] = partial_results['workload_ram'].merge(reused_results['olm_clusters'].loc[:,['_id']], on="_id", how="inner")
        accumulated_results[metric] = accumulated_results[metric].append(reused_results['wkld_ram_olm']).groupby(['_id'], as_index=False).mean() # Get average over time
        reused_results['wkld_ram_olm'].set_index('_id', inplace=True)
    elif metric == "workload_cpu_optional_clusters":
        reused_results['wkld_cpu_optional'] = partial_results['workload_cpu'].merge(reused_results['optional_clusters'].loc[:,['_id']], on="_id", how="inner")
        indexNames = reused_results['wkld_cpu_optional'][ reused_results['wkld_cpu_optional']['value'] < 0 ].index
        reused_results['wkld_cpu_optional'].drop(indexNames , inplace=True)
        accumulated_results[metric] = accumulated_results[metric].append(reused_results['wkld_cpu_optional']).groupby(['_id'], as_index=False).mean() # Get average over time
        reused_results['wkld_cpu_optional'].set_index('_id', inplace=True)
    elif metric == "workload_ram_optional_clusters":
        reused_results['wkld_ram_optional'] = partial_results['workload_ram'].merge(reused_results['optional_clusters'].loc[:,['_id']], on="_id", how="inner")
        accumulated_results[metric] = accumulated_results[metric].append(reused_results['wkld_ram_optional']).groupby(['_id'], as_index=False).mean() # Get average over time
        reused_results['wkld_ram_optional'].set_index('_id', inplace=True)
    elif metric == "olm_utilization_cpu":
        metric_df = reused_results['wkld_cpu_olm'].div(reused_results['cpu_olm']).reset_index().dropna()
        accumulated_results[metric] = accumulated_results[metric].append(metric_df).groupby(['_id'], as_index=False).mean() # Get average over time
    elif metric == "optional_utilization_cpu":
        metric_df = reused_results['wkld_cpu_optional'].div(reused_results['cpu_optional']).reset_index().dropna()
        accumulated_results[metric] = accumulated_results[metric].append(metric_df).groupby(['_id'], as_index=False).mean() # Get average over time
    elif metric == "olm_utilization_ram":
        metric_df = reused_results['wkld_ram_olm'].div(reused_results['ram_olm']).reset_index().dropna()
        accumulated_results[metric] = accumulated_results[metric].append(metric_df).groupby(['_id'], as_index=False).mean() # Get average over time
    elif metric == "optional_utilization_ram":
        metric_df = reused_results['wkld_ram_optional'].div(reused_results['ram_optional']).reset_index().dropna()
        accumulated_results[metric] = accumulated_results[metric].append(metric_df).groupby(['_id'], as_index=False).mean() # Get average over time
    elif metric == "operator_versions":
        temp_df = partial_results['csv_operators'][~partial_results['csv_operators'].isin(partial_results['retired_operators'])].dropna()
        temp_df = temp_df.merge(partial_results["email_clusters"], on="_id", how="inner").drop(['email_domain'], axis=1) # Drop RedHat/IBM clusters
        temp_df[['name','version']] = temp_df.name.str.split('.',n=1,expand=True) # Split name and version
        temp_df = temp_df.drop_duplicates()
        accumulated_results[metric] = (accumulated_results[metric].append(temp_df)).groupby(['_id', 'name'], as_index=False).max() # Keep only latest version
    #elif metric == "clusters_operators": # KEEP ONLY LATEST VERSION OF OPERATOR
    #    metric_df = partial_results['csv_operators']
    #    accumulated_results[metric] = accumulated_results[metric].append(metric_df).drop_duplicates()
    else:
        pass
        #print("Metric not currently implemented...")
    return

def execute_queries(measure, partial_results, point_queries, q, x, unix_timestamp, prometheusClient, lock):
    """
    Execute query q. If failure, or timeout, retries 5 times before aborting
    """
    if ((x+1) % 24 == 0) or (x==0):
        if x != 0:
            days = (x+1) / 24
            print("Collecting data for {} days before for measure {}".format((days) + 1, measure))
        else:
            print("Collecting data for last day of week for measure {}".format(measure))
    query = add_offset( q, x )
    retries = 0
    query_result = None
    while (not query_result) and (retries <= 5):
        try:
            query_result = prometheusClient.querier(query, unix_timestamp)
            if not query_result and measure == "olm_retired": # Usually olm_retired returns nothing, so no need to re-try
                retries = 6                                  # Could possibly be deprecated
        except PrometheusApiClientException as e:
            print(e)
            query_result = None
        if retries == 5:
            print("failure for hour {} \n resorting to point query".format(x))
            point_query = point_queries[measure]
            point_query = add_offset_point(point_query, x)
            try:
                query_result = prometheusClient.querier(point_query, unix_timestamp)
            except PrometheusApiClientException as e:
                query_result = None
            if not query_result:
                print("Point query, also failed")
        elif (not query_result) and (measure != "olm_retired"):
            print("Time-out, retrying {}...".format(measure))
        retries += 1
        if retries == 6:
            print("Metric: {}, aborting..\n failure for hour {}".format(measure,x))
    if query_result or measure == "olm_retired":
        lock.acquire()
        consume_results(measure, query_result, partial_results)
        lock.release()
    else:
        print("No results for metric {} on day {}".format(measure,x))

    return

def main():
    # Parse end of the week
    parser = argparse.ArgumentParser(description='Define end of week in MMDDYYYY format for metric collection')
    parser.add_argument('-d', '--date', required=True, help="End of week in MMDDYYYY format")
    parser.add_argument('-s', '--save', required=False, default="n", help="Save data to Google Sheets (\"y\" for yes, \"n\" for \"no\" (default)")
    args = parser.parse_args()

    if args.date:
        month, day, year = args.date[:2], args.date[2:4], args.date[4:]
    
    if args.save == "y" or args.save == "yes":
        saveData = True
    else:
        saveData = False

    # Set unix timestamp in UTC
    dt_week = datetime(int(year),int(month),int(day),tzinfo=timezone.utc)
    unix_timestamp = dt_week.timestamp()
    
    # Read credentials (prom url and access token) from yaml files
    print(os.getcwd())
    with open('authentication/credentials.yaml', 'r') as f_cred:
        credentials = yaml.safe_load(f_cred)
    with open('queries/hybrid_queries.yaml','r') as f_query:
        complete_metrics = yaml.safe_load(f_query)
    with open('queries/point_queries.yaml','r') as f_backup:
        point_queries = yaml.safe_load(f_backup)
    with open('queries/smaller_queries2.yaml', 'r') as f_small:
        smaller_queries = yaml.safe_load(f_small)

    # Create the prometheus connector
    prometheusClient = promClient(credentials['prom_url'], credentials['prom_access_token'])
    prometheusClient.connector()
    
    accumulated_results = dict()
    for metric, _ in complete_metrics.items():
        accumulated_results[metric] = pd.DataFrame() 
   
    # perform the set of queries for x hours before
    for x in range(4):
        print("Collecting data for {} hours before".format(x))
        lock = Lock()
        manager = Manager()
        partial_results = manager.dict()
        reused_results = dict()
        p = {}
        for measure, q in smaller_queries.items(): # Perform first queries to be joined later
            p[measure] = Process(target=execute_queries, args=( measure, partial_results, point_queries, q, x, unix_timestamp, prometheusClient, lock))
            p[measure].start()
        for measure, _ in smaller_queries.items():
            p[measure].join()
        # Join for metric of interests from partial results
        for metric, _ in complete_metrics.items():
            try:
                join_from_partial( metric, partial_results, reused_results, accumulated_results )
            except:
                print("Join failed for measure {} on hour {}".format(metric,x))
    final_results = dict()
    final_results['Date'] = [dateFormat(month,day,year)]
    for metric, _ in complete_metrics.items():
        get_final_results( metric, accumulated_results, final_results )
    # append to CSV and upload to GSheets
    appendToCSV( final_results, saveData )
    if saveData:
        uploadToGSheets()

if __name__ == "__main__":
    main()
