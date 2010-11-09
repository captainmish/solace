
from solace import settings

from solace.search import get_engine
from solace.templating import render_template


def search(request):
    engine = get_engine()
    query = request.args.get('search', None)
    res = engine.query(unicode(query))
    return render_template('kb/search.html', res=res, query=query)
