"""GitHub Actions entrypoint. Reviews PR diff and posts one top-level comment."""
import os, sys
import requests
from graph import agent

def main():
    repo=os.environ['GITHUB_REPOSITORY']
    number=int(os.environ['PR_NUMBER'])
    token=os.environ['GITHUB_TOKEN']
    base=f'https://api.github.com/repos/{repo}'
    headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    session=requests.Session()
    session.headers.update(headers)
    # Fetch changed files with pagination. Never execute code from PR.
    patches=[]
    for page in range(1,6):
        response=session.get(f'{base}/pulls/{number}/files',params={'per_page':100,'page':page},timeout=30)
        response.raise_for_status()
        files=response.json()
        if not files: break
        for item in files:
            if item['filename'].endswith(('.cs','.md','.json','.yaml','.yml')) and item.get('patch'):
                patches.append(f"FILE {item['filename']}\n{item['patch']}")
        if len(files)<100: break
    if not patches:
        report='No supported text-file patches available for AI review.'
    else:
        diff='\n\n'.join(patches)
        if len(diff)>18000:
            diff=diff[:18000]
            warning='\n\n**Warning:** PR diff was truncated; this review is incomplete.'
        else: warning=''
        result=agent.invoke({'kind':'pr','diff':diff})
        report=result['answer']+warning
        if result.get('sources'): report+='\n\n**Retrieved sources:**\n'+'\n'.join('- '+s for s in result['sources'])
    body='## Payment RAG AI — advisory PR review\n\n'+report[:55000]+'\n\n_AI-generated; verify findings manually. No tests executed by this agent._'
    # Upsert one bot comment rather than spamming on each synchronize event.
    marker='## Payment RAG AI — advisory PR review'
    old=None
    for page in range(1,6):
        r=session.get(f'{base}/issues/{number}/comments',params={'per_page':100,'page':page},timeout=30)
        r.raise_for_status()
        comments=r.json()
        for comment in comments:
            if comment.get('body','').startswith(marker) and comment.get('user',{}).get('type')=='Bot': old=comment['id']; break
        if old or len(comments)<100: break
    if old:
        response=session.patch(f'{base}/issues/comments/{old}',json={'body':body},timeout=30)
    else:
        response=session.post(f'{base}/issues/{number}/comments',json={'body':body},timeout=30)
    response.raise_for_status()
    print(f'Posted/updated advisory review on PR #{number}')
if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(f'PR review failed: {exc}',file=sys.stderr)
        raise
