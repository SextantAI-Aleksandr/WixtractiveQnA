# This file downloads three different models for use in Question Answering

import torch
from transformers import BertTokenizer, BertForQuestionAnswering
from question_answering import SMALL_MODEL, MEDIUM_MODEL, LARGE_MODEL

for model in (SMALL_MODEL, MEDIUM_MODEL, LARGE_MODEL):
    print('Downloading (if needed) model=', model)
    _tokenizer = BertTokenizer.from_pretrained(model)
    _model = BertForQuestionAnswering.from_pretrained(model)

