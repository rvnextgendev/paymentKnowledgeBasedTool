from fastapi import FastAPI
from pydantic import BaseModel, Field
from graph import agent
app=FastAPI(title='Payment RAG AI')
class Ask(BaseModel): question:str=Field(min_length=1,max_length=4000)
class Review(BaseModel): diff:str=Field(min_length=1,max_length=18000)
@app.post('/ask')
def ask(req:Ask):
    result=agent.invoke({'kind':'chat','question':req.question})
    return {'answer':result['answer'],'sources':result.get('sources',[])}
@app.post('/review')
def review(req:Review):
    result=agent.invoke({'kind':'pr','diff':req.diff})
    return {'review':result['answer'],'sources':result.get('sources',[])}
