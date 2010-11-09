
from solace import settings
from solace.search import get_engine
from solace.templating import render_template
from solace.utils.formatting import format_creole_diff, format_creole
from solace.application import url_for


def search(request):
    engine = get_engine()
    query = request.args.get('search', None)
    page = request.args.get('page', 1)
    res = engine.query(unicode(query), page=page)
    out = []
    for r in res:
        r['content'] = format_creole(r['content'])
        out.append(r)
        print r
    return render_template('kb/search.html', pagecount=res.pagecount, 
                            page=res.pagenum, res=out, query=query)
