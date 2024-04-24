from src.app.models import Model
from src.app.views import View

from src.summarygen import MeasureSummary


class HomeController:
    def __init__(self, model: Model, view: View):
        self.model = model
        self.view = view
        self.page = view.home
        self.__bind()

    def show(self):
        self.page.tkraise()

    def get_measure_ids(self) -> list[str]:
        offset = self.model.home.offset
        limit = self.model.home.limit
        return self.model.connection.get_measure_ids(offset, limit)

    def get_measure_versions(self) -> list[str]:
        measure_id = self.model.home.selected_measure
        if measure_id == '':
            return []
        return self.model.connection.get_measure_versions(measure_id)

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

    def next_page(self):
        self.model.home.increment_offset()
        self.update_measure_ids()

    def prev_page(self):
        self.model.home.decrement_offset()
        self.update_measure_ids()

    def reset(self):
        self.model.home.selected_measure = None
        self.page.measure_id_list.selected_measure = None
        self.page.measure_version_list.versions = []
        self.update_measure_ids()

    def __sanitize(self, input: str) -> str:
        sanitized = input.upper()
        return sanitized

    def search(self, *args):
        measure_id = self.__sanitize(self.page.measure_id_list.search_bar.get())
        if measure_id == '':
            self.reset()
            self.page.measure_id_list.search_bar.clear()
            return

        self.page.measure_id_list.measure_ids = [measure_id]
        self.model.home.selected_measure = measure_id
        self.page.measure_id_list.selected_measure = measure_id
        self.update_measure_versions()

    def create_summary(self):
        summary = MeasureSummary(relative_dir='summaries', override=True)
        for measure_id in self.model.home.selected_versions:
            measure = self.model.connection.get_measure(measure_id)
            summary.add_measure(measure)
        summary.build()

    def __bind(self):
        self.page.measure_id_list.measure_frame.set_command(self.select_measure_id)
        self.page.measure_id_list.next_btn.configure(command=self.next_page)
        self.page.measure_id_list.back_btn.configure(command=self.prev_page)
        self.page.measure_id_list.search_bar.search_bar.bind('<Return>', self.search)
        self.page.measure_id_list.search_bar.search_btn.configure(command=self.search)
        self.page.measure_id_list.search_bar.reset_btn.configure(command=self.reset)
        self.page.measure_version_list.version_frame.set_command(self.select_measure_version)
        self.page.measures_selection_list.add_btn.configure(command=self.create_summary)
        
        