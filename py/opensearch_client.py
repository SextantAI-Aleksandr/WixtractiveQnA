

import opensearchpy
from opensearchpy import OpenSearch
from opensearchpy.client import OpenSearch as Client


ARTICLE_INDEX_NAME = 'articles'
ARTICLE_INDEX_BODY = {
    "mappings": {
        "properties": {
            "headings": {
                "type": "nested" # See https://opster.com/guides/elasticsearch/data-architecture/elasticsearch-nested-field-object-field/
            },
            "categories": {
                "type": "nested" # See https://opster.com/guides/elasticsearch/data-architecture/elasticsearch-nested-field-object-field/
            },
            "places": {
                "type": "nested" # See https://opster.com/guides/elasticsearch/data-architecture/elasticsearch-nested-field-object-field/
            },
            "outgoing_links": {
                "type": "nested" # See https://opster.com/guides/elasticsearch/data-architecture/elasticsearch-nested-field-object-field/
            },
            "external_links": {
                "type": "nested" # See https://opster.com/guides/elasticsearch/data-architecture/elasticsearch-nested-field-object-field/
            }
        }
    }
}


def connect(host=None, port=None, auth=None) -> Client:
    # create a client connection and initialize indexes
    # See https://opensearch.org/docs/1.0/clients/python/
    if host == None:
        host = 'localhost'
    if port == None:
        port = 9200
    if auth == None:
        auth = ('admin', 'admin') # For testing only. Don't store credentials in code.
    # OTHER SECURITY SETTING YOU SHOULD CHANGE IN PRODUCTION:
    # ca_certs_path = '/full/path/to/root-ca.pem' # Provide a CA bundle if you use intermediate CAs with your root CA.
    # Optional client certificates if you don't want to use HTTP basic authentication.
    # client_cert_path = '/full/path/to/client.pem'
    # client_key_path = '/full/path/to/client-key.pem'

    # Create the client
    client = OpenSearch(
            hosts = [{'host': host, 'port': port}],
            http_compress = True, # enables gzip compression for request bodies
            http_auth = auth,
            # client_cert = client_cert_path,
            # client_key = client_key_path,
    #     use_ssl = True,
    #     verify_certs = True,
    #     ssl_assert_hostname = False,
    #     ssl_show_warn = False,
    #     ca_certs = ca_certs_path
    )

    # Ensure you have the indexes you want now before you start adding documents 
    try:
        _response = client.indices.create(ARTICLE_INDEX_NAME, body=ARTICLE_INDEX_BODY)
    except opensearchpy.exceptions.RequestError as e:
        if e.error != 'resource_already_exists_exception':
            # some unexpected error occurred 
            raise e 
        else:
            pass # you expect an error if you try to create an index that already exists 
    
    # having ensured that you have the index you want, return the client
    return client 


