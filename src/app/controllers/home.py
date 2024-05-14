import os
import threading

from src import _ROOT
from src.app.views import View
from src.app.models import Model
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
        prev_selection = self.model.home.selected_measure
        self.model.home.selected_measure = self.page.measure_id_list.selected_measure
        try:
            self.update_measure_versions()
            return
        except NotFoundError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Measures Not Found')
        except ETRMResponseError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Server Error')
        except UnauthorizedError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Unauthorized Access')
        self.model.home.selected_measure = prev_selection
        self.page.measure_id_list.selected_measure = prev_selection

    def next_page(self):
        try:
            self.model.home.increment_offset()
            self.update_measure_ids()
            return
        except NotFoundError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Measures Not Found')
        except ETRMResponseError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Server Error')
        except UnauthorizedError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Unauthorized Access')
        self.model.home.decrement_offset()

    def prev_page(self):
        try:
            self.model.home.decrement_offset()
            self.update_measure_ids()
            return
        except NotFoundError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Measures Not Found')
        except ETRMResponseError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Server Error')
        except UnauthorizedError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Unauthorized Access')
        self.model.home.increment_offset()

    def reset_ids(self):
        self.model.home.selected_measure = None
        self.page.measure_id_list.selected_measure = None
        self.page.measure_version_list.versions = []
        self.page.measure_id_list.search_bar.clear()
        try:
            self.update_measure_ids()
        except NotFoundError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Measures Not Found')
        except ETRMResponseError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Server Error')
        except UnauthorizedError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Unauthorized Access')
        self.unfocus()

    def search_measure_ids(self, *args):
        measure_id = self.__sanitize(self.page.measure_id_list.search_bar.get())
        if measure_id == '':
            self.reset_ids()
            self.page.measure_id_list.search_bar.clear()
            return

        prev_selection = self.page.measure_id_list.selected_measure
        try:
            self.model.home.selected_measure = measure_id
            self.update_measure_versions()
            self.unfocus()
            self.page.measure_id_list.measure_ids = [measure_id]
            self.page.measure_id_list.selected_measure = measure_id
            return
        except NotFoundError as err:
            self.page.open_info_prompt(f'No measure with the ID {measure_id}'
                                       ' was found',
                                       title=' Measure Not Found')
        except ETRMResponseError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Server Error')
        except UnauthorizedError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Unauthorized Access')
        self.model.home.selected_measure = prev_selection

    def __bind_id_list(self):
        self.page.measure_id_list.measure_frame.set_command(self.select_measure_id)
        self.page.measure_id_list.next_btn.configure(command=self.next_page)
        self.page.measure_id_list.back_btn.configure(command=self.prev_page)
        self.page.measure_id_list.search_bar.search_btn.configure(command=self.search_measure_ids)
        self.page.measure_id_list.search_bar.search_bar.bind('<Return>', self.search_measure_ids)
        self.page.measure_id_list.search_bar.search_bar.bind('<Escape>', self.unfocus)
        self.page.measure_id_list.search_bar.reset_btn.configure(command=self.reset_ids)

    def update_measure_selections(self):
        self.page.measures_selection_list.measures = self.model.home.selected_versions
        if self.model.home.selected_versions != []:
            self.page.measures_selection_list.clear_btn.configure(state='normal')
            self.page.measures_selection_list.add_btn.configure(state='normal')
        else:
            self.page.measures_selection_list.clear_btn.configure(state='disabled')
            self.page.measures_selection_list.add_btn.configure(state='disabled')

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

        self.update_measure_selections()

    def reset_versions(self):
        self.page.measure_version_list.search_bar.clear()
        try:
            if self.model.home.selected_measure != None:
                self.update_measure_versions()
        except NotFoundError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Measures Not Found')
        except ETRMResponseError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Server Error')
        except UnauthorizedError as err:
            self.page.open_info_prompt(err.message,
                                       title=' Unauthorized Access')
        self.unfocus()

    def search_measure_versions(self, *args):
        version_id = self.__sanitize(self.page.measure_version_list.search_bar.get())
        if version_id == '':
            self.reset_versions()
            self.page.measure_version_list.search_bar.clear()
            self.unfocus()
            return

        if version_id not in self.model.home.measure_versions:
            self.page.measure_version_list.versions = []
            self.unfocus()
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

    @staticmethod
    def __create_summary(dir_path: str,
                         file_name: str,
                         selected_versions: list[str],
                         model: Model,
                         view: View):
        summary = MeasureSummary(dir_path=dir_path, file_name=file_name)
        for measure_id in selected_versions:
            try:
                measure = model.connection.get_measure(measure_id)
            except NotFoundError as err:
                view.home.close_prompt()
                view.home.open_info_prompt(err.message,
                                           title=' Measure Not Found')
                return
            except ETRMResponseError as err:
                view.home.close_prompt()
                view.home.open_info_prompt(err.message,
                                           title=' Server Error')
                return
            except UnauthorizedError as err:
                view.home.close_prompt()
                view.home.open_info_prompt(err.message,
                                           title=' Unauthorized Access')
                return
            summary.add_measure(measure)
        summary.build()
        model.results.summary_path = summary.file_path
        model.results.file_name = summary.file_name
        view.home.close_prompt()
        view.home.open_info_prompt('Success!')
        view.home.measure_version_list.selected_versions = []
        view.home.measures_selection_list.measures = []
        model.home.selected_versions = []

    def create_summary(self):
        if self.model.home.selected_versions != []:
            def_path = os.path.join(_ROOT, '..', 'summaries')
            if not os.path.exists(def_path):
                def_path = os.path.join(_ROOT, 'summaries')
                if not os.path.exists(def_path):
                    raise FileNotFoundError(f'no {def_path} folder exists')
            def_fname = 'measure_summary'
            result = self.page.open_fd_prompt(os.path.normpath(def_path),
                                              def_fname,
                                              title=' Summary PDF Details')
            if result[2] == False:
                return

            dir_path = result[0]
            if dir_path == '':
                self.page.open_info_prompt('A destination folder is required'
                                           ' to create a measure summary.')
                return

            file_name = result[1]
            if file_name == '':
                self.page.open_info_prompt('A file name is required to create'
                                           ' a measure summary.')
                return

            path = os.path.normpath(os.path.join(dir_path, file_name + '.pdf'))
            if os.path.exists(path):
                conf = self.page.open_yesno_prompt(f'A file named {file_name} already'
                                                   f' exists in {dir_path}, '
                                                   ' would you like to overwrite it?',
                                                   title=' File Conflict Detected')
                if not conf:
                    return

            self.page.open_prompt('Generating summary, please be patient...')
            process = threading.Thread(target=self.__create_summary,
                                       args=[dir_path,
                                             file_name,
                                             self.model.home.selected_versions,
                                             self.model,
                                             self.view])
            process.start()
        else:
            self.page.open_info_prompt(text='At least one measure version is'
                                            ' required to create a summary')

    def add_measure_version(self, *args):
        version_id = self.__sanitize(self.page.measures_selection_list.search_bar.get())
        if version_id == '':
            self.page.measures_selection_list.search_bar.clear()
            return

        if version_id in self.model.home.selected_versions:
            return

        try:
            self.model.connection.get_measure(version_id)
        except NotFoundError as err:
            self.unfocus()
            self.page.open_info_prompt(err.message,
                                       title=' Measures Not Found')
            return
        except ETRMResponseError as err:
            self.unfocus()
            self.page.open_info_prompt(err.message,
                                       title=' Server Error')
            return
        except UnauthorizedError as err:
            self.unfocus()
            self.page.open_info_prompt(err.message,
                                       title=' Unauthorized Access')
            return

        self.model.home.selected_versions.append(version_id)
        self.page.measures_selection_list.measures = self.model.home.selected_versions

        self.page.measures_selection_list.search_bar.clear()
        self.unfocus()

    def clear_selected_measures(self):
        self.model.home.selected_versions = []
        self.page.measures_selection_list.measures = []
        self.page.measure_version_list.selected_versions = []
        self.page.measures_selection_list.clear_btn.configure(state='disabled')
        self.page.measures_selection_list.add_btn.configure(state='disabled')

    def __bind_selected_list(self):
        self.page.measures_selection_list.add_btn.configure(command=self.create_summary)
        self.page.measures_selection_list.clear_btn.configure(command=self.clear_selected_measures)
        self.page.measures_selection_list.search_bar.add_btn.configure(command=self.add_measure_version)
        self.page.measures_selection_list.search_bar.search_bar.bind('<Return>', self.add_measure_version)
        self.page.measures_selection_list.search_bar.search_bar.bind('<Escape>', self.unfocus)
