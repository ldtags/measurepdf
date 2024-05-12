from src.app.models import Model
from src.app.views import View

from src.summarygen import MeasureSummary
from src.exceptions import (
    ETRMResponseError,
    UnauthorizedError,
    NotFoundError
)


class HomeController:
    def __init__(self, model: Model, view: View):
        self.model = model
        self.view = view
        self.page = view.home
        self.__bind_id_list()
        self.__bind_version_list()
        self.__bind_selected_list()

    def __sanitize(self, input: str) -> str:
        sanitized = input.upper()
        return sanitized

    def unfocus(self, *args):
        self.page.focus()

    def show(self):
        self.page.tkraise()

    def get_measure_ids(self) -> list[str]:
        offset = self.model.home.offset
        limit = self.model.home.limit
        return self.model.connection.get_measure_ids(offset, limit)

    def get_measure_versions(self, measure_id: str | None=None) -> list[str]:
        id = measure_id or self.model.home.selected_measure
        if id == '':
            return []
        return self.model.connection.get_measure_versions(id)

    def update_measure_ids(self):
        measure_ids = self.get_measure_ids()
        self.model.home.measure_ids = measure_ids
        self.page.measure_id_list.measure_ids = measure_ids

    def update_measure_versions(self):
        measure_versions = self.get_measure_versions()
        self.model.home.measure_versions = measure_versions
        self.page.measure_version_list.versions = measure_versions
        self.page.measure_version_list.selected_versions = list(
            filter(lambda version: version in self.model.home.selected_versions,
                   measure_versions))

    def select_measure_id(self):
        self.model.home.selected_measure = self.page.measure_id_list.selected_measure
        self.update_measure_versions()

    def next_page(self):
        self.model.home.increment_offset()
        self.update_measure_ids()

    def prev_page(self):
        self.model.home.decrement_offset()
        self.update_measure_ids()

    def reset_ids(self):
        self.model.home.selected_measure = None
        self.page.measure_id_list.selected_measure = None
        self.page.measure_version_list.versions = []
        self.page.measure_id_list.search_bar.clear()
        self.update_measure_ids()

    def search_measure_ids(self, *args):
        measure_id = self.__sanitize(self.page.measure_id_list.search_bar.get())
        if measure_id == '':
            self.reset_ids()
            self.page.measure_id_list.search_bar.clear()
            return

        self.page.measure_id_list.measure_ids = [measure_id]
        self.page.measure_id_list.selected_measure = measure_id
        self.model.home.selected_measure = measure_id
        self.update_measure_versions()
        self.unfocus()

    def __bind_id_list(self):
        self.page.measure_id_list.measure_frame.set_command(self.select_measure_id)
        self.page.measure_id_list.next_btn.configure(command=self.next_page)
        self.page.measure_id_list.back_btn.configure(command=self.prev_page)
        self.page.measure_id_list.search_bar.search_btn.configure(command=self.search_measure_ids)
        self.page.measure_id_list.search_bar.search_bar.bind('<Return>', self.search_measure_ids)
        self.page.measure_id_list.search_bar.search_bar.bind('<Escape>', self.unfocus)
        self.page.measure_id_list.search_bar.reset_btn.configure(command=self.reset_ids)

    def select_measure_version(self):
        selected_versions = self.page.measure_version_list.selected_versions
        all_versions = self.page.measure_version_list.versions
        unselected_versions = list(
            filter(lambda item: item not in selected_versions, all_versions))

        for version in unselected_versions:
            if version in self.model.home.selected_versions:
                self.model.home.selected_versions.remove(version)

        for version in selected_versions:
            if version not in self.model.home.selected_versions:
                self.model.home.selected_versions.append(version)

        self.page.measures_selection_list.measures = self.model.home.selected_versions

    def reset_versions(self):
        self.page.measure_version_list.search_bar.clear()
        self.update_measure_versions()

    def search_measure_versions(self, *args):
        version_id = self.__sanitize(self.page.measure_version_list.search_bar.get())
        if version_id == '':
            self.reset_versions()
            self.page.measure_version_list.search_bar.clear()
            return

        if version_id not in self.model.home.measure_versions:
            self.page.measure_version_list.versions = []
            return

        self.page.measure_version_list.versions = [version_id]
        if version_id in self.model.home.selected_versions:
            self.page.measure_version_list.selected_versions = [version_id]
        self.unfocus()

    def __bind_version_list(self):
        self.page.measure_version_list.version_frame.set_command(self.select_measure_version)
        self.page.measure_version_list.search_bar.search_btn.configure(command=self.search_measure_versions)
        self.page.measure_version_list.search_bar.search_bar.bind('<Return>', self.search_measure_versions)
        self.page.measure_version_list.search_bar.search_bar.bind('<Escape>', self.unfocus)
        self.page.measure_version_list.search_bar.reset_btn.configure(command=self.reset_versions)

    def create_summary(self):
        summary = MeasureSummary(relative_dir='..\\summaries', override=True)
        for measure_id in self.model.home.selected_versions:
            measure = self.model.connection.get_measure(measure_id)
            summary.add_measure(measure)
        summary.build()

    def add_measure_version(self, *args):
        version_id = self.__sanitize(self.page.measures_selection_list.search_bar.get())
        if version_id == '':
            self.page.measures_selection_list.search_bar.clear()
            return

        if version_id in self.model.home.selected_versions:
            return

        try:
            self.model.connection.get_measure(version_id)
        except NotFoundError:
            return

        self.model.home.selected_versions.append(version_id)
        self.page.measures_selection_list.measures = self.model.home.selected_versions
        self.page.measures_selection_list.search_bar.clear()
        self.unfocus()

    def clear_selected_measures(self):
        self.model.home.selected_versions = []
        self.page.measures_selection_list.measures = []
        self.page.measure_version_list.selected_versions = []

    def __bind_selected_list(self):
        self.page.measures_selection_list.add_btn.configure(command=self.create_summary)
        self.page.measures_selection_list.clear_btn.configure(command=self.clear_selected_measures)
        self.page.measures_selection_list.search_bar.add_btn.configure(command=self.add_measure_version)
        self.page.measures_selection_list.search_bar.search_bar.bind('<Return>', self.add_measure_version)
        self.page.measures_selection_list.search_bar.search_bar.bind('<Escape>', self.unfocus)
