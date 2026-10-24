from fastapi import FastAPI
from pydantic import BaseModel, Field
from graph import agent
app=FastAPI(title='Payment RAG AI', description='Ask about indexed payment code and rules, or request an advisory diff review. Retrieval combines semantic and keyword search by default. See /docs for interactive examples.')
class Ask(BaseModel):
    question:str=Field(min_length=1,max_length=4000, description='Question about indexed payment code or business rules.', examples=['Explain PaymentRequest'])
class Review(BaseModel):
    diff:str=Field(min_length=1,max_length=18000, description='Git diff to review against indexed code and business rules.', examples=['- if (request.Amount <= 0)\n+ if (request.Amount < 0)'])
class AskResponse(BaseModel):
    answer: str = Field(description='Generated answer grounded in retrieved evidence.')
    sources: list[str] = Field(description='Retrieved source paths with character offsets.')
class ReviewResponse(BaseModel):
    review: str = Field(description='Advisory review; no tests are executed by this endpoint.')
    sources: list[str] = Field(description='Retrieved source paths with character offsets.')
@app.post('/ask', response_model=AskResponse, tags=['Knowledge'], summary='Ask about payment code and rules', responses={500: {'description': 'Retrieval or model-provider failure; inspect server logs.'}})
def ask(req:Ask):
    result=agent.invoke({'kind':'chat','question':req.question})
    return {'answer':result['answer'],'sources':result.get('sources',[])}
@app.post('/review', response_model=ReviewResponse, tags=['Review'], summary='Review a proposed code diff', responses={500: {'description': 'Retrieval or model-provider failure; inspect server logs.'}})
def review(req:Review):
    result=agent.invoke({'kind':'pr','diff':req.diff})
    return {'review':result['answer'],'sources':result.get('sources',[])}
