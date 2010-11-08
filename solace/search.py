
from solace import settings
from solace.models import Topic, Post

from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import TEXT, NUMERIC, ID, BOOLEAN, Schema
from whoosh.index import create_in, open_dir, EmptyIndexError
from whoosh.lang.porter import stem
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.query import And
from whoosh.searching import Facets


class WhooshEngine(object):
    def __init__(self):
        try:
            self.ix = self.get_index()
        except EmptyIndexError:
            self.ix = self.create_index()

    def get_schema(self):
        stem_ana = StemmingAnalyzer()
        schema = Schema(topicid=ID(stored=True),
                    title=TEXT(stored=True, analyzer = stem_ana),
                    content=TEXT(stored=True, analyzer = stem_ana),
                    postid = ID(unique=True, stored=True),
                    votes=NUMERIC,
                    dtype=ID(stored=True),
                    hotness=NUMERIC,
                    )
        return schema

    def create_index(self):
        """Create Whoosh index, returns index object
        """
        ix = create_in(settings.WHOOSH_DB, self.get_schema())
        return ix

    def get_index(self):
        return open_dir(settings.WHOOSH_DB)

    def _get_ptype(self, post):
        if post.is_answer or post.is_question:
            if post.is_question:
                return u'question'
            return u'answer'
        return u'post'

    def rebuild_index(self, incremental=False):
        writer = self.ix.writer()
        if incremental:
            pass
        else:
            for p in Post.query.all():
                print p.topic.id, p.id
                self._add_post(p, writer)
            writer.commit()

    def remove_post(self, post, commit=False):
        writer = self.ix.writer()
        writer.delete_by_term('postid', unicode(post.id))
        if commit:
            writer.commit()

    def add_post(self, post, writer, commit=False):
        writer.add_document(
            topicid = unicode(post.topic.id),
            title = unicode(post.topic.title),
            content = unicode(post.text),
            postid = unicode(post.id),
            votes = post.votes,
            dtype = self._get_ptype(post),
            hotness = post.topic.hotness)
        if commit:
            writer.commit()

    def update_post(self, post, writer=None, commit=True):
        if writer is None:
            writer = self.ix.writer()
        self.remove_post(post, commit)
        self.add_post(post, writer, commit)

    def query(self, query, only_questions=False, only_answered=False):
        searcher = self.ix.searcher()
        stem_ana = StemmingAnalyzer()
        query = ' '.join([token.text for token in stem_ana(query)])
        q = MultifieldParser(['title','content']).parse(query)
        if only_questions:
            qq = QueryParser('dtype').parse(u'question')
            q = And([q,qq])
        res = searcher.search(q)
        #facets = Facets.from_field(searcher, "topicid")
        #cats = facets.categorize(res)
        return res

def get_tids(res):
    return [r.get("topicid") for r in res]

def get_pid_tid(res):
    d = []
    for r in res:
        d.append({"topic": r.get("topicid"), "post": r.get("postid")})
    return d