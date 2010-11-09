
from solace import settings

from solace.search import get_engine
from solace.templating import render_template
from solace.utils.formatting import format_creole_diff, format_creole


def search(request):
    engine = get_engine()
    query = request.args.get('search', None)
    res = engine.query(unicode(query))
    out = []
    for r in res:
        outres = r.fields()
        outres['content'] = format_creole(outres['content'])
        out.append(outres)
    return render_template('kb/search.html', res=out, query=query)
