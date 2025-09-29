
# Implement deterministic YOY via YA pair
def compute_yoy(rows):
    # rows expected list of dicts with 'metric' and 'metric_ya'
    out=[]
    for r in rows:
        metric=r.get('metric')
        metric_ya=r.get('metric_ya')
        delta=None
        pct_delta=None
        if metric is None or metric_ya is None:
            out.append({'metric':metric,'metric_ya':metric_ya,'delta':None,'pct_delta':None})
            continue
        delta = metric - metric_ya
        if metric_ya == 0:
            pct_delta = None
        else:
            pct_delta = (metric - metric_ya) / metric_ya
        out.append({'metric':metric,'metric_ya':metric_ya,'delta':delta,'pct_delta':pct_delta})
    return out
