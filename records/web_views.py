from django.views.generic import TemplateView


class TransactionsPageView(TemplateView):
    template_name = "records/transactions.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_page"] = "transactions"
        return ctx
