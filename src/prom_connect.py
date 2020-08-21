from prometheus_api_client import PrometheusConnect, MetricSnapshotDataFrame

class promClient:
    def __init__(self, prom_url, prom_token):
        """
            Instantiate a prometheus client instance
            bearing the prometheus API url (prom_url)
            and access token (prom_token)
        """
        self.url = prom_url
        self.headers = {"Authorization": f"bearer {prom_token}"}
        self.pc = None

    def connector( self ):
        """
            Instantiate a prometheus connector
        """
        self.pc = PrometheusConnect(
                url=self.url,
                headers=self.headers,
                disable_ssl=True
                )

    def querier( self, q, timestamp=None ):
        """
            Perform a query (q) for a given evaluation
            timestamp (timestamp) - in unix time
        """
        if timestamp:
            q_result = self.pc.custom_query(
                    q,
                    params = {'time': timestamp}
                )
        else:
            q_result = self.pc.custom_query(
                    q
                    )
        
        return q_result
