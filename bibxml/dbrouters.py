from main.models import RefData


class IndexDBRouter(object):
    """Directs all operations on RefData to database 'index'."""

    def db_for_read(self, model, **hints):
        if model == RefData:
            return 'index'
        return None

    def db_for_write(self, model, **hints):
        if model == RefData:
            return 'index'
        return None

    def allow_migrate(self, db, app_label, model_name, *args, **kwargs):
        if model_name == 'RefData' and app_label == 'main':
            return db == 'index'
        if db == 'index':
            return model_name == 'RefData' and app_label == 'main'
        return None
