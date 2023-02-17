

from sys import argv 
from time import time 
from opensearchpy.helpers import bulk
from WikiEnGine import WikiEngine # https://github.com/SextantAI-Aleksandr/WikiEnGine.git
from opensearch_client import connect, ARTICLE_INDEX_NAME

BATCH_SIZE = 2500 # The batch size to use for document insertion 

if __name__ == '__main__':
    # EXAMPLE USAGE:
    # python3 load_articles.py /path/to/enwiki-20230206-cirrussearch-content.json
    path_to_cirrus_dump = argv[1]
    client = connect() 
    wen = WikiEngine(path_to_cirrus_dump)
    bulk_data = []
    tot_succ, tot_failed, t_last = 0, 0, time ()
    tot_prior = int(client.cat.count(index=ARTICLE_INDEX_NAME, format='json')[0]['count']) # number of documents already there
    for (i, article) in enumerate(wen.generate()):
        if i < tot_prior:
            if i % 10000 == 0:
                print('Skipped {:,} rows until resuming at row {:,}  '.format(i, tot_prior), end='\r')
            continue
        if article == None:
            stats = bulk(client, bulk_data, stats_only=True)
            print('FINISHED LOADING!')
            break
        doc = {
            '_op_type': 'index',
            '_index': ARTICLE_INDEX_NAME,
            '_id': article.page_id,
            '_source': {
                'title': article.title,
                'text': article.text, 
                'updated_at': article.updated,
                'count_incoming_links': article.count_incoming_links, 
                'count_incoming_links': article.count_incoming_links,
                # Why all the dictionaries? See the example at 
                # https://opster.com/guides/elasticsearch/data-architecture/elasticsearch-nested-field-object-field/
                'headings': [{'name':x for x in article.headings}], 
                'categories': [{'name':x for x in article.categories}],
                'outgoing_links': [{'name': x for x in article.outgoing_links}],
                'external_links': [{'url':x for x in article.external_links}]
            }
        }
        bulk_data.append(doc)
        # dump the data every 100 rows
        # for help with bulk data inserts, see https://github.com/opensearch-project/opensearch-py/blob/main/opensearchpy/helpers/actions.py
        if (i % BATCH_SIZE == 0) and (i > 1):
            success, failed = bulk(client, bulk_data, stats_only=True)
            speed = int(BATCH_SIZE / (time() - t_last + 0.01))
            t_last = time()
            tot_succ += success
            tot_failed += failed
            print('Loading data @ {:,} rows. @ {:,}/sec. success/failed={:,}/{:,} totals = {:,}/{:,}'.format(i, speed, success, failed, tot_succ, tot_failed))
            bulk_data = []
