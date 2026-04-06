from django.views.generic import TemplateView


class DashboardOverviewView(TemplateView):
    template_name = "dashboard/overview.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_page"] = "overview"
        return ctx


class DashboardReportsView(TemplateView):
    template_name = "dashboard/reports.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_page"] = "reports"
        return ctx
