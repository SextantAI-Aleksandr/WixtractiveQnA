


from typing import List, Dict, Tuple, Optional
from os import environ 
import torch
from transformers import BertTokenizer, BertForQuestionAnswering
from opensearch_client import connect, ARTICLE_INDEX_NAME


SMALL_MODEL = 'mrm8488/bert-tiny-finetuned-squadv2'
MEDIUM_MODEL = 'mrm8488/bert-medium-finetuned-squadv2'
LARGE_MODEL = 'bert-large-uncased-whole-word-masking-finetuned-squad'

# Tags for highligting OpenSearch results 
HIGHLIGHT_PRE_TAG = '<em>'  
HIGHLIGHT_POST_TAG = '</em>'

MAX_TOXENS = 512 # most models can't accept more input tokens than this 


class ArticleHit:
    # This class gives structure and type hints to an OpenSearch hit _source for a Wikipedia article
    def __init__(self, hit: Dict[str, object]):
        self.score: float = float(hit['_score'])                # relevance scoring
        self.id: int = int(hit['_id'])                          # the ID for the article
        self.title: str = hit['_source']['title']               # article title
        self.highlights: List[str] = hit['highlight']['text']   # List of highlighted text sections


class PossibleAnswer:
    # This class represents a possible answer to a question, drawn from one highlight from one article
    def __init__(self, hit: ArticleHit, excerpt: str, answer: str, score: float ):
        self.article_id: int = hit.id
        self.article_title: str = hit.title,
        self.excerpt: str = excerpt 
        self.answer: str = answer 
        self.score: float = score

    def __str__(self):
        # custom print() implementation
        return 'PossibleAnswer: score={} answer="{}" '.format(self.score, self.answer)


class ExtractiveQnA:
    def __init__(self, model_name=None):
        # initialize a client
        self.client = connect()
        # instantiate a transformers model
        if model_name == None:
            # if no model was provided, look for an environment variable
            # or use the default that gives good results: 'bert-large-uncased-whole-word-masking-finetuned-squad'
            model_name = environ.get('model', 'medium')
        model_name = {'small':SMALL_MODEL, 'medium':MEDIUM_MODEL, 'large':LARGE_MODEL}.get(model_name, model_name) # replace shorthan with full name
        self.model_name = model_name 
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        self.model = BertForQuestionAnswering.from_pretrained(model_name)
        self.req_no = 0     # for keeping track of request #s for web applications 


    def article_search(self,
        phrase,             # the phrase (or in this case, question) you are searching for
        n=4,                # the number of documents (=Wikipedia articles) to return
        fragment_size=250  # how many characters to return for each highlight snippet in each article
            # NOTE: This is a very influential parameter. Somewhat counter-intuitively, even though longer
            # excerpts should provide more context, shorter ones seem to lead to crisper and often better answers.
            # Shorter excerpts also have the benefit of processing faster
        ) -> List[ArticleHit]:
        # given a phrase (or question), return the best matching articles from Wikipedia
        # to modify the query, read the docs here:
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-multi-match-query.html
        resp = self.client.search(
            index=ARTICLE_INDEX_NAME, 
            body={
                'query':{
                    'multi_match':{
                        'query': phrase,
                        'type':'most_fields',
                        'fields':['title^2','text']     # give stronger weighting to hits in the title
                    }
                },
                'highlight':{
                    'fields':{
                        'text':{}                       # highlight excerpts from the text of the article
                    },
                    'pre_tags':[HIGHLIGHT_PRE_TAG],     # <em> HTML tag before matching words
                    'post_tags':[HIGHLIGHT_POST_TAG],   # </em> HTML tag after matching words
                    'fragment_size':fragment_size       # Number of characters to include in highlight                 
                }
            })
        article_hits = [ ArticleHit(hit) for hit in resp['hits']['hits'][:n] ]
        return article_hits


    def read_and_extract(self, excerpt, question) -> Tuple[float, str]:
        '''
        Given an excerpt that is supposed to contain an answer to a question,
        give the best answer you can from that excerpt along with an associated score
        '''
        # Tokenize
        input_ids = self.tokenizer.encode(question, excerpt
            .replace(HIGHLIGHT_PRE_TAG,'')  # you want highighting for the UI, but not the model! 
            .replace(HIGHLIGHT_POST_TAG, '') )  
        input_ids = input_ids[:MAX_TOXENS]
        # Search the input_ids for the first instance of the `[SEP]` token.
        sep_index = input_ids.index(self.tokenizer.sep_token_id)
        # The number of segment A tokens includes the [SEP] token istelf.
        num_seg_a = sep_index + 1
        # The remainder are segment B.
        num_seg_b = len(input_ids) - num_seg_a
        # Construct the list of 0s and 1s.
        segment_ids = [0]*num_seg_a + [1]*num_seg_b
        # There should be a segment_id for every input token.
        assert len(segment_ids) == len(input_ids)
        # ======== Evaluate ========
        # Run the question through the model.
        output = self.model(torch.tensor([input_ids]), # The tokens representing our input text.
            token_type_ids=torch.tensor([segment_ids])) # The segment IDs to differentiate question from excerpt
        # ======== Reconstruct Answer ========
        # Find the tokens with the highest `start` and `end` scores.
        answer_start = int(torch.argmax(output.start_logits))
        answer_end = int(torch.argmax(output.end_logits))
        # score the matches: see https://mccormickml.com/2020/03/10/question-answering-with-a-fine-tuned-BERT/#4-visualizing-scores
        score_start = float(torch.max(output.start_logits))
        score_end = float(torch.max(output.end_logits))
        score = (score_start + score_end )/2     # take arithmetic mean- don't let negatives cancel in a geometric mean
        # Get the string versions of the input tokens.
        tokens = self.tokenizer.convert_ids_to_tokens(input_ids)
        # Get the tokens associated with the answer
        answer = tokens[answer_start]
        # Select the remaining answer tokens and join them with whitespace.
        for i in range(answer_start + 1, answer_end + 1):
            # If it's a subword token, then recombine it with the previous token.
            if tokens[i][0:2] == '##':
                answer += tokens[i][2:]
            # Otherwise, add a space then the token.
            else:
                answer += ' ' + tokens[i]
        return score, answer


    def unfiltered_answers(self, question: str, **kwargs) -> List[PossibleAnswer]:
        # This function (1) searches for Wikipedia articles matching the question,
        # For each highlight in each article, it returns the best answer
        # NOTE: Many snippets of text may contain relevent keywords yet not answer the question
        # Therefore, it is expected that many may have a negative score
        unfiltered_answers = []
        article_hits  = self.article_search(question, **kwargs)
        for hit in article_hits:
            for excerpt in hit.highlights:
                score, answer = self.read_and_extract(excerpt, question)
                unfiltered_answers.append( PossibleAnswer(hit, excerpt, answer, score) )
        return unfiltered_answers

    
    def possible_answers(self, question: str, **kwargs) -> List[PossibleAnswer]:
        # remove answers with answer == '[CLS]' then rank them
        unfiltered_answers = self.unfiltered_answers(question, **kwargs) 
        return sorted([ ans for ans in unfiltered_answers if (ans.answer != '[CLS]') ], key=lambda x: -x.score)

    
    def answer(self, question: str, **kwargs) -> Optional[PossibleAnswer]:
        # This is a high-level function that both searches for articles and answers a question based on those articles
        # kwargs are passed to self.article_search: See definitions there 
        possible_answers = self.possible_answers(question, **kwargs)
        if not possible_answers:
            return None 
        return possible_answers[0]


    def response(self, question: str, **kwargs) -> Tuple[int,  Optional[PossibleAnswer]]:
        # for HTTP requests, increment the req_no as well 
        self.req_no += 1 
        answer = self.answer(question, **kwargs)
        return self.req_no, answer




def test_read_and_extract():
    # quick sanity check test
    xqa = ExtractiveQnA(model_name=None)
    _, ans = xqa.read_and_extract('Philip loves tomatoes- he ate 5 and Samantha ate 7.', 'How many tomatoes did Philip eat?')
    assert ans == '5'


def test_cherrypicked_answers():
    # The model doesn't get all the answers right, but it does get these ones right! 
    xqa = ExtractiveQnA(model_name=None)
    answer = xqa.answer('What engineering school is located in Golden Colorado?', fragment_size=250)
    assert answer.answer == 'the colorado school of mines'
    answer = xqa.answer('When was Ohio State founded?', fragment_size=250)
    assert answer.answer == '1870'
