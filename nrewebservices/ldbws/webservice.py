from .responses import StationBoard

from suds.client import Client
from suds.sax.element import Element

import logging

log = logging.getLogger(__name__)
LDBWS_NAMESPACE = ('com','http://thalesgroup.com/RTTI/2010-11-01/ldb/commontypes')

class Session(object):
    """
    This class provides the interface to the LDBWS web service session.

    Note:
        There are some (unknown) internal rules on the LDBWS server which limit the number of
        services returned in a response, sometimes to less than the number requested by the
        `time_window` and/or `rows` parameters to a request. Unfortunately there is nothing that can
        be done about this, so you just have to work with it.
    """
    def __init__(self, wsdl=None, api_key=None, timeout=5):
        """
        You should normally instantiate this class only once per application, as it fetches and
        parses the WSDL from the server on instantiation, normally taking a few seconds to complete.

        Args:
            wsdl (str): the URL of the web service WSDL. Be sure to pass the ?ver=2016-02-16 on the
                end of the URL to get the version this library currently supports. If this parameter
                is not provided, the code expects to find an environment variable called
                **NRE_LDBWS_WSDL** containing it instead.

            api_key (str): your LDBWS API key. If this is not provided, the code expects to find an
                environment variable called **NRE_LDBWS_API_KEY** containing it instead.

            timeout (int): the number of seconds the after which the underlying SOAP client should
                timeout unfinished requests.

        Raises:
            ValueError: if neither of the `wsdl` parameter or the **NRE_LDBWS_WSDL** environment
                variable are provided.
            ValueError: if neither of the `api_key` parameter or the **NRE_LDBWS_API_KEY**
                environment variable are provided.
        """

        # Try getting the WSDL and API KEY from the environment if they aren't explicitly passed.
        if not wsdl:
            try:
                wsdl = os.environ['NRE_LDBWS_WSDL']
            except AttributeError:
                raise ValueError("LDBWS WSDL must be either explicitly provided to the Session initializer or via the environment variable NRE_LDBWS_WSDL.")

        if not api_key:
            try:
                api_key = os.environ['NRE_LDBWS_API_KEY']
            except AttributeError:
                raise ValueError("LDBWS API key must be either explicitly provided to the Session initializer or via the environment variable NRE_LDBWS_API_KEY.")

        # Build the SOAP client.
        self._soap_client = Client(wsdl)
        self._soap_client.set_options(timeout=timeout)
        self._service = self._soap_client.service['LDBServiceSoap']

        # Build the SOAP authentication headers.
        access_token = Element('AccessToken', ns=LDBWS_NAMESPACE)
        access_token_value = Element('TokenValue', ns=LDBWS_NAMESPACE)
        access_token_value.setText(api_key)
        access_token.append(access_token_value)
        self._soap_client.set_options(soapheaders=(access_token))

    def get_station_board(self, crs, rows=10, include_departures=True, include_arrivals=False,
            from_filter_crs=None, to_filter_crs=None, time_offset=None, time_window=None):
        """
        Get a list of public services at a station as would populate a departure/arrival board.

        Args:
            crs (str): the CRS code of the station for which this board is being fetched.

            rows (int, from 1 to 150): the maximum number of services to include in the returned
                board.

            include_departures (boolean): whether the returned services should include departures
                from this station. At least one of `include_departures` or `include_arrivals` must
                be set to true.

            include_arrivals (boolean): whether the returned services should include arrivals at
                this station. At least one of `include_departures` or `include_arrivals` must be set
                to true.

            from_filter_crs (str): the CRS code of a station at which all services returned must
                have called previously. Only one of `from_filter_crs` and `to_filter_crs` can be set
                for a given request.

            to_filter_crs (str): the CRS code of a station at which all services returned must
                subsequently call. Only one of `from_filter_crs` and `to_filter_crs` can be set for
                a given request.

            time_offset (int, from -120 to 120): An offset in minutes against the current time which
                determines the starting point of the time window for which services are returned. If
                set to `None`, the value of 0 will be used.

            time_window (int, from -120 to 120): How far into the future from the value passed as
                `time_offset` should services be fetched. If the value passed is negative, the time
                window starts before the value of `time_offset` and ends at `time_offset`. If `None`
                is passed, the default value is 120.

        Returns:
            StationBoard: a `StationBoard` object containing the station details and the requested
            services.

        Raises:
            ValueError: if neither include_departures or include_arrivals are set to True.

        Note:
            Each time this his method is called, it makes **1** request to the LDBWS server.
        """

        # Get the appropriate SOAP query method.
        if include_departures and include_arrivals:
            query = self._service.GetArrivalDepartureBoard
        elif include_departures:
            query = self._service.GetDepartureBoard
        elif include_arrivals:
            query = self._service.GetArrivalBoard
        else:
            raise ValueError("When calling get_station_board, either include_departures or include_arrivals must be set to True.")

        # Construct the query parameters.
        params = {}
        params['crs'] = crs
        params['numRows'] = rows
        if to_filter_crs:
            if from_filter_crs:
                log.warn("get_station_board() can only be filtered on one of from_filter_crs and to_filter_crs. Since both are provided, using only to_filter_crs")
            params['filterCrs'] = to_filter_crs
            params['filterType'] = 'to'
        elif from_filter_crs:
            params['filterCrs'] = from_filter_crs
            params['filterType'] = 'from'
        if time_offset is not None:
            params['timeOffset'] = time_offset
        if time_window is not None:
            params['timeWindow'] = time_window

        # Do the SOAP query.
        # TODO: Some form of error handling.
        soap_response = query(**params)
        return StationBoard(soap_response)


