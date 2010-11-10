
from datetime import datetime, timedelta, date

from solace import settings
from solace.models import Topic, Post

from whoosh.analysis import StemmingAnalyzer
from whoosh.lang.porter2 import stem as stem2
from whoosh.fields import TEXT, NUMERIC, ID, BOOLEAN, Schema, KEYWORD, DATETIME
from whoosh.index import create_in, open_dir, EmptyIndexError
from whoosh.lang.porter import stem
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.query import And
from whoosh.searching import Facets


def get_engine():
    return WhooshEngine()

class WhooshEngine(object):
    def __init__(self):
        self.stem_ana = StemmingAnalyzer(stemfn=stem2)
        try:
            self.ix = self.get_index()
        except EmptyIndexError:
            self.ix = self.create_index()

    def get_schema(self):
        schema = Schema(topicid=ID(stored=True),
                    title=TEXT(stored=True, analyzer = self.stem_ana),
                    content=TEXT(stored=True, analyzer = self.stem_ana),
                    postid = ID(unique=True, stored=True),
                    tags = KEYWORD(stored=True),
                    votes=NUMERIC,
                    dtype=ID(stored=True),
                    hotness=NUMERIC,
                    date_updated=DATETIME(stored=True),
                    date_indexed=DATETIME(stored=True),
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
                self.add_post(p, writer)
            writer.commit()

    def remove_post(self, post, writer=None, commit=False):
        if writer is None:
            writer = self.ix.writer()
        writer.delete_by_term('postid', unicode(post.id))
        if commit:
            writer.commit()

    def add_post(self, post, writer=None, commit=False):
        if writer is None:
            writer = self.ix.writer()
        writer.add_document(
            topicid = unicode(post.topic.id),
            title = unicode(post.topic.title),
            content = unicode(post.text),
            postid = unicode(post.id),
            tags = ','.join([t.name for t in post.topic.tags]) or None,
            votes = post.votes,
            dtype = self._get_ptype(post),
            hotness = post.topic.hotness,
            date_updated = post.updated,
            date_indexed = datetime.utcnow()
            )
        if commit:
            writer.commit()

    def update_post(self, post, commit=True):
        print 'readding %s' % post
        self.remove_post(post=post, commit=commit)
        self.add_post(post=post, commit=commit)

    def query(self, query, page=1, only_questions=True, only_answered=False):
        searcher = self.ix.searcher()
        query = ' '.join([token.text for token in self.stem_ana(query)])
        q = MultifieldParser(['title','content']).parse(query)
        if only_questions:
            qq = QueryParser('dtype').parse(u'question')
            q = And([q,qq])
        res = searcher.search_page(q, int(page), sortedby='hotness')
        #facets = Facets.from_field(searcher, "topicid")
        #cats = facets.categorize(res)
        return res


def handle_changes(changes):
    engine = get_engine()
    for model, action in changes:
        if isinstance(model, Post):
            engine.update_post(model)


# database signal handlers
from solace.models import Post, Topic, _Vote
from solace.signals import after_models_committed
after_models_committed.connect(handle_changes)
