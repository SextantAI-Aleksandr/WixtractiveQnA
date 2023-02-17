

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from question_answering import ExtractiveQnA 

xqa = ExtractiveQnA()     # initiate a SageQnA instance
app = Starlette()   # initiate a Starlette app
req_no = 0          # initiate a request counter 


@app.route("/")
async def homepage(request):
    question = request.query_params.get('q', None)
    if not question:
        return JSONResponse({ 'status': 400, 'message':'I have a question: What is your question?' })
    if not question.endswith('?'):
        question += '?'
    req_no, answer = xqa.response(question)
    print('\nQ: {}'.format(question))
    print('A: {}'.format(answer))
    return JSONResponse({ 'req_no': req_no, 'status': 200, 'message':answer })

