from django.db.models import QuerySet
from django.views.generic.edit import FormMixin
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
try:
    from pandas import DataFrame
except ImportError:
    DataFrame = None

login_required_m = method_decorator(login_required)


class ReportList(object):

    def __init__(self, report_view, results):
        self._results = results
        self.report_view = report_view
        self._fields = self.report_view.get_fields()

    @property
    def fields(self):
        fields = self._fields
        if fields is None and self._results:
            fields = self._results[0].keys()
        return fields or []

    @property
    def results(self):
        if isinstance(self._results, QuerySet):
            records = self._results.values(self.fields)
        elif DataFrame is not None and isinstance(self._results, DataFrame):
            records = self._results.reset_index().T.to_dict().values()
        else:
            records = self._results
        for record in iter(records):
            yield self._items(record)

    def _items(self, record):
        for field in self.fields:
            try:
                attr_field = getattr(self.report_view, field)
            except AttributeError:
                yield record.get(field)
            else:
                if callable(attr_field):
                    yield attr_field(record)


class ReportView(TemplateView, FormMixin):
    template_name = 'report.html'
    title = ''
    fields = None

    # TODO: Handle fields labels
    # TODO: sortables columns (?)

    @login_required_m
    def dispatch(self, request, *args, **kwargs):
        return super(ReportView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ReportView, self).get_form_kwargs()
        if self.request.method == 'GET':
            kwargs.update({
                'data': self.request.GET,
            })
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs = super(ReportView, self).get_context_data(**kwargs)
        form = self.get_form(self.get_form_class())
        if 'form' not in kwargs:
            kwargs['form'] = form
        kwargs.update({
            'title': self.get_title(),
            'has_filters': self.get_form_class() is not None,
        })
        if form.is_valid():
            results = self.aggregate(form)
            kwargs.update({
                'rl': ReportList(self, results),
            })
        return kwargs

    def get_title(self):
        return self.title

    def get_fields(self):
        return self.fields

    def aggregate(self, form):
        ''' Implement here your data elaboration.
        Must return a list of dict.
        '''
        raise NotImplementedError('Subclasses must implement this method')
