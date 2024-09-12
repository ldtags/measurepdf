import os
import re
import sys
import tkinter as tk
import customtkinter as ctk

from src import _ROOT, patterns, lookups, utils
from src.app.enums import Result, SUCCESS, FAILURE
from src.app.views import View
from src.app.models import Model
from src.app.controllers.base import BaseController, etrm_request
from src.etrm.models import Measure
from src.etrm.connection import ETRMConnection
from src.etrm.exceptions import ETRMResponseError
from src.summarygen import MeasureSummary


class HomeController(BaseController):
    """MVC Controller for the Home module."""

    def __init__(self, model: Model, view: View):
        BaseController.__init__(self, view, model)
        self.model = model.home
        self.view = view.home
        self.__bind_id_list()
        self.__bind_version_list()
        self.__bind_selected_list()

    @property
    def connection(self) -> ETRMConnection | None:
        return self.model_root.connection

    def unfocus(self, *args):
        """Removes focus from any currently focused widget."""

        self.view.parent.focus()

    def perror(self, error: Exception):
        if isinstance(error, ETRMResponseError):
            match error.status:
                case 401:
                    self.view.open_info_prompt(error.message,
                                               title=' Unauthorized')
                case 404:
                    self.view.open_info_prompt(error.message,
                                               title=' Not Found')
                case 500:
                    self.view.open_info_prompt(error.message,
                                               title=' Server Error')
        elif isinstance(error, PermissionError) and error.errno == 13:
            self.view.open_info_prompt('Cannot overwrite the PDF while it is'
                                       ' open.',
                                       title=' Permission Error')
        elif isinstance(error, ConnectionError):
            self.view.open_info_prompt('Please check your network connection'
                                       ' and try again.',
                                       title=' Connection Error')
        else:
            self.view.open_info_prompt('An unexpected error occurred:'
                                       f'\n{error}',
                                       title=' Error')

    @etrm_request
    def get_measure_ids(self,
                        offset: int=0,
                        limit: int=25,
                        use_category: str | None=None
                       ) -> tuple[list[str], int]:
        """Returns a list of measure IDs and the total count of measures."""

        return self.connection.get_measure_ids(
            offset=offset,
            limit=limit,
            use_category=use_category
        )

    @etrm_request
    def get_all_measure_ids(self, use_category: str | None=None) -> list[str]:
        return self.connection.get_all_measure_ids(use_category)

    @etrm_request
    def get_measure_versions(self, statewide_id: str) -> list[str]:
        """Returns a list of all versions of `statewide_id`."""

        return self.connection.get_measure_versions(statewide_id)

    @etrm_request
    def get_all_measure_versions(self,
                                 use_category: str | None=None
                                ) -> list[str]:
        """Returns a list of the most recent published version of each
        measure.
        """

        published_versions: list[str] = []
        measure_ids = self.connection.get_all_measure_ids(use_category)
        for measure_id in measure_ids:
            measure_versions = self.connection.get_measure_versions(measure_id)
            measure_versions.sort(key=utils.version_key)
            published_version: str | None = None
            for measure_version in measure_versions:
                if measure_version.count('-') == 1:
                    published_version = measure_version
                    break
            if published_version is None:
                continue
            published_versions.append(published_version)
        return published_versions

    @etrm_request
    def get_measure(self, version_id: str) -> Measure:
        return self.connection.get_measure(version_id)

    def get_current_measure_ids(self) -> list[str]:
        """Returns the list of measure IDs that should be shown in the view
        based on the current state of the model.
        """

        return self.get_measure_ids(
            offset=self.model.offset,
            limit=self.model.limit,
            use_category=self.model.use_category
        )

    def show(self):
        """Shows the home view."""

        if self.model.measure_ids == [] or self.model.count == 0:
            measure_ids, count = self.get_current_measure_ids()
            self.model.measure_ids = measure_ids
            self.model.count = count
            self.view.measure_id_list.measure_ids = measure_ids

        self.view.tkraise()

    def update_measure_ids_view(self) -> None:
        """Updates the measure id list frame in the view to match
        the current state of the model.
        """

        back_btn = self.view.measure_id_list.back_btn
        if self.model.offset == 0:
            if back_btn._state == tk.NORMAL:
                back_btn.configure(state=tk.DISABLED)
        elif back_btn._state == tk.DISABLED:
            back_btn.configure(state=tk.NORMAL)

        next_btn = self.view.measure_id_list.next_btn
        if self.model.offset + self.model.limit >= self.model.count:
            if next_btn._state == tk.NORMAL:
                next_btn.configure(state=tk.DISABLED)
        elif next_btn._state == tk.DISABLED:
            next_btn.configure(state=tk.NORMAL)

        measure_ids = sorted(
            self.model.measure_ids,
            key=utils.statewide_key
        )
        self.view.measure_id_list.measure_ids = measure_ids
        self.view.measure_id_list.selected_measures = list(
            filter(
                lambda measure_id: measure_id in self.model.selected_measures,
                measure_ids
            )
        )

    def update_measure_ids(self) -> Result:
        """Sets the measure IDs in the Home view to the correct set of
        measure IDs using the `offset` and `limit` in the Home model.

        Call when any changes have been made to the measure id related
        properties of the model (i.e., limit, offset, use_category).
        """

        try:
            measure_ids, count = self.get_current_measure_ids()
        except ETRMResponseError as err:
            match err.status:
                case 404:
                    self.view.open_info_prompt(
                        'Could not find any measures',
                        title='Not Found'
                    )
                case _:
                    self.perror(err)
            return FAILURE

        self.model.measure_ids = measure_ids
        self.model.count = count
        self.update_measure_ids_view()
        return SUCCESS

    def update_measure_versions_view(self) -> None:
        """Updates the measure versions frame of the view to be consistent
        with the current state of the model
        """

        measure_versions = sorted(
            self.model.all_versions,
            key=utils.version_key
        )
        self.view.measure_version_list.versions = measure_versions
        self.view.measure_version_list.selected_versions = list(
            filter(
                lambda version: version in self.model.selected_versions,
                measure_versions
            )
        )

    def update_measure_versions(self) -> Result:
        """Sets the measure version IDs in the Home view to the versions
        of the currently selected measures.
        """

        measure_versions: list[str] = []
        for measure_id in self.model.selected_measures:
            try:
                id_versions = self.get_measure_versions(measure_id)
            except ETRMResponseError as err:
                match err.status:
                    case 404:
                        self.view.open_info_prompt(
                            'Could not find versions of measure'
                                f' {measure_id}',
                            title='Not Found'
                        )
                    case _:
                        self.perror(err)
                return FAILURE
            measure_versions.extend(id_versions)

        # update model with retrieved measure versions
        for version in measure_versions:
            re_match = re.search(patterns.VERSION_ID, version)
            if re_match == None:
                continue
            statewide_id = re_match.group(2)
            try:
                self.model.measure_versions[statewide_id].append(version)
            except KeyError:
                self.model.measure_versions[statewide_id] = [version]

        self.update_measure_versions_view()
        return SUCCESS

    def update_measure_selections(self):
        """Sets the selected measure versions in the Home view to the
        selected measure versions in the Home model.

        Call this method when the selected measure versions in the model
        are updated.
        """

        self.view.measures_selection_list.measures = sorted(
            self.model.selected_versions,
            key=utils.version_key
        )
        if self.model.selected_versions != []:
            self.view.measures_selection_list.clear_btn.configure(state=ctk.NORMAL)
            self.view.measures_selection_list.add_btn.configure(state=ctk.NORMAL)
        else:
            self.view.measures_selection_list.clear_btn.configure(state=ctk.DISABLED)
            self.view.measures_selection_list.add_btn.configure(state=ctk.DISABLED)

    def select_measure_id(self, measure_ids: list[str] | None=None):
        """Event that occurs when a measure ID is selected."""

        self.view.measure_id_list.measure_frame.disable()
        prev_selections = self.model.selected_measures.copy()
        cur_selections = self.view.measure_id_list.selected_measures.copy()
        if measure_ids is not None:
            cur_selections.extend(measure_ids)

        selected = set(cur_selections).difference(prev_selections)
        for measure_id in selected:
            if measure_id not in self.model.selected_measures:
                self.model.selected_measures.append(measure_id)

        unselected = set(prev_selections).difference(cur_selections)
        for measure_id in unselected:
            if measure_id in self.view.measure_id_list.measure_ids:
                self.model.selected_measures.remove(measure_id)
                self.model.measure_versions[measure_id] = []

        result = self.update_measure_versions()
        if result != SUCCESS:
            self.model.selected_measures = prev_selections
            self.view.measure_id_list.selected_measures = prev_selections

        self.view.measure_id_list.measure_frame.enable()

    def next_id_page(self):
        """Increments the current set of measure IDs shown in the Home view.

        Updates the current set of measure IDs in the Home view accordingly.

        Opens an info popup on error defining which error occurred.
        """

        self.model.increment_offset()
        result = self.update_measure_ids()
        if result != SUCCESS:
            self.model.decrement_offset()

    def prev_id_page(self):
        """Decrements the current set of measure IDs shown in the Home view.

        Updates the current set of measure IDs in the Home view accordingly.

        Disables the `back_btn` in the Home view if the `offset` from the Home
        model is 0.

        Opens an info popup on error defining which error occurred.
        """

        self.model.decrement_offset()
        result = self.update_measure_ids()
        if result != SUCCESS:
            self.model.increment_offset()

    def reset_ids(self, *args):
        """Resets the measure IDs frame and selected measure in the
        Home view and the selected measure in the Home model.

        Opens an info popup on error defining which error occurred.
        """

        self.model.use_category = None
        self.model.offset = 0
        self.model.selected_measures = []
        self.view.measure_id_list.selected_measures = []
        self.view.measure_version_list.versions = []
        self.view.measure_id_list.search_bar.clear()
        self.update_measure_ids()
        self.unfocus()

    def search_measure_ids(self, *args):
        """Searches for a specific measure ID in the eTRM API.

        Updates the measure versions in the Home view accordingly.

        Opens an info popup on error defining which error occurred.
        """

        search_val = self.view.measure_id_list.search_bar.get()
        try:
            re_match = re.search(patterns.STWD_ID, search_val)
            if re_match != None:
                self.model.measure_ids = [search_val]
                self.update_measure_ids_view()
                return

            re_match = re.fullmatch(patterns.USE_CATEGORY, search_val)
            if re_match != None:
                use_category = re_match.group(2).upper()
                try:
                    self.model.use_category = use_category
                except ValueError as err:
                    self.view.open_info_prompt(str(err))
                    return
                self.model.offset = 0
                self.update_measure_ids()
                return

            self.model.measure_ids = []
            self.update_measure_ids_view()
        finally:
            self.view.measure_id_list.search_bar.clear()
            self.unfocus()

    def __bind_id_list(self):
        """Binds events to the widgets in the measure ID frame in
        the Home view.
        """

        id_view = self.view.measure_id_list
        id_view.measure_frame.set_command(self.select_measure_id)
        id_view.next_btn.configure(command=self.next_id_page)
        id_view.back_btn.configure(command=self.prev_id_page)
        id_view.search_bar.search_bar.bind('<Return>', self.search_measure_ids)
        id_view.search_bar.search_bar.bind('<Escape>', self.unfocus)
        id_view.reset_btn.configure(command=self.reset_ids)

    def select_measure_version(self):
        """Event that occurs when a measure version ID is selected."""

        selected_versions = self.view.measure_version_list.selected_versions
        all_versions = self.view.measure_version_list.versions
        unselected_versions = list(
            filter(lambda item: item not in selected_versions, all_versions))

        for version in unselected_versions:
            if version in self.model.selected_versions:
                self.model.selected_versions.remove(version)

        for version in selected_versions:
            if version not in self.model.selected_versions:
                self.model.selected_versions.append(version)

        self.update_measure_selections()

    def reset_versions(self):
        """Sets the measure versions shown in the Home view to the set
        of all of the currently selected measure's versions.
        """

        self.view.measure_version_list.search_bar.clear()
        if self.model.selected_measures != []:
            self.update_measure_versions()
        self.unfocus()

    def search_measure_versions(self, *args):
        """Searches the versions of the currently selected measure for
        the version in the search bar entry widget.

        Displays an empty set of versions if none are found.
        """

        search_val = self.view.measure_version_list.search_bar.get()
        try:
            re_match = re.fullmatch(patterns.STWD_ID, search_val)
            if re_match != None:
                statewide_id = str(re_match.group(1)).upper()
                self.model.filter_versions(statewide_id=statewide_id)
                self.update_measure_versions_view()
                return

            re_match = re.fullmatch(patterns.VERSION_ID, search_val)
            if re_match != None:
                statewide_id = str(re_match.group(2)).upper()
                version = str(re_match.group(6))
                self.model.filter_versions(statewide_id=statewide_id,
                                           version=version)
                self.update_measure_versions_view()
                return

            self.model.measure_versions = {}
            self.update_measure_versions_view()
        finally:
            self.view.measure_version_list.search_bar.clear()
            self.unfocus()

    def __bind_version_list(self):
        """Binds events to the widgets in the measure version ID frame in
        the Home view.
        """

        versions_view = self.view.measure_version_list
        versions_view.version_frame.set_command(self.select_measure_version)
        versions_view.search_bar.search_bar.bind('<Return>',
                                                 self.search_measure_versions)
        versions_view.search_bar.search_bar.bind('<Escape>', self.unfocus)

    def clear_selected_measures(self):
        """Clears all selected measures from the Home view and Home model."""

        self.model.selected_versions = []

        view = self.view
        view.measures_selection_list.measures = []
        view.measure_version_list.selected_versions = []
        view.measures_selection_list.clear_btn.configure(state=ctk.DISABLED)
        view.measures_selection_list.add_btn.configure(state=ctk.DISABLED)

    def add_use_category(self, use_category: str):
        try:
            verbose_name = lookups.USE_CATEGORIES[use_category]
        except KeyError:
            keys = list(lookups.USE_CATEGORIES.keys())
            self.view.open_info_prompt(f'{use_category} is not a'
                                       ' valid use category.\n'
                                       'Valid use categories are:'
                                       f' [{",".join(keys)}]')
            return
        self.view.open_prompt(f'Retrieving all {verbose_name} measures...')
        measure_ids = self.get_all_measure_ids(use_category)
        for measure_id in measure_ids:
            self.view.update_prompt('Retrieving the most recent published'
                                    f' version of {measure_id}...')
            try:
                versions = self.get_measure_versions(measure_id)
            except ETRMResponseError:
                continue
            versions.sort(key=utils.version_key)
            for version in versions:
                if version.count('-') == 1:
                    self.model.selected_versions.append(version)
                    break
        self.update_measure_selections()
        self.view.close_prompt()

    def add_measure_version(self, *args):
        """Directly adds a measure version to the selected measure versions.

        Opens an info popup on error defining which error occurred.
        """

        search_val = self.view.measures_selection_list.search_bar.get()
        if search_val == '':
            self.view.open_info_prompt('Please enter the full statewide ID'
                                            ' for the desired measure.',
                                       title=' Missing Statewide ID')
            return

        re_match = re.fullmatch(patterns.USE_CATEGORY, search_val)
        if re_match != None:
            use_category = re_match.group(2).upper()
            try:
                lookups.USE_CATEGORIES[use_category]
            except KeyError:
                keys = list(lookups.USE_CATEGORIES.keys())
                self.view.open_info_prompt(f'{use_category} is not a'
                                                ' valid use category.'
                                                '\nValid use categories are:'
                                                f' {keys}')
                return
            self.add_use_category(use_category)
            self.view.measures_selection_list.search_bar.clear()
            self.unfocus()
            return

        re_match = re.fullmatch(patterns.VERSION_ID, search_val)
        if re_match == None:
            self.view.open_info_prompt('Cannot find a measure with the full'
                                       f' statewide ID: {search_val}',
                                       title=' Invalid Statewide ID')
            return

        version_id = re_match.group(1)
        if version_id in self.model.selected_versions:
            self.view.open_info_prompt(f'{version_id} is already selected.',
                                       title=' Redundant Selection')
            return

        self.view.open_prompt(f'Searching for measure {version_id}...')
        error: Exception | None = None
        try:
            self.get_measure(version_id)
            self.model.selected_versions.append(version_id)
            self.update_measure_selections()
        except Exception as err:
            error = err
        finally:
            self.view.close_prompt()
            self.view.measures_selection_list.search_bar.clear()
            self.unfocus()

        if error == None:
            return

        self.perror(error)

    def get_file_info(self) -> tuple[str, str] | None:
        """Opens the user prompts for defining the file name and destination
        of the measure summary PDF.
        
        Returns the tuple: (directory path, file name)
        """

        if getattr(sys, 'frozen', False):
            def_path = os.path.join(_ROOT, '..', '..', 'summaries')
        else:
            def_path = os.path.join(_ROOT, '..', 'summaries')
        def_path = os.path.normpath(def_path)
        if not os.path.exists(def_path):
            self.view.open_info_prompt(f'no {def_path} folder exists')
            return None

        def_fname = 'measure_summary'
        result = self.view.open_fd_prompt(def_path,
                                          def_fname,
                                          title=' Summary PDF Details')
        if result[2] == False:
            return None

        dir_path = result[0]
        if dir_path == '':
            self.view.open_info_prompt('A destination folder is required'
                                       ' to create a measure summary.')
            return None

        file_name = result[1]
        if file_name == '':
            self.view.open_info_prompt('A file name is required to create'
                                       ' a measure summary.')
            return None

        path = os.path.normpath(os.path.join(dir_path, file_name + '.pdf'))
        if os.path.exists(path):
            conf = self.view.open_yesno_prompt(f'A file named {file_name} already'
                                               f' exists in {dir_path}, '
                                               ' would you like to overwrite it?',
                                               title=' File Conflict Detected')
            if not conf:
                return None

        return (dir_path, file_name)

    def create_summary(self):
        """Opens the user prompts for defining the file name and destination
        of the measure summary PDF.

        Calls the measure summary PDF generation function after user input.
        """

        if self.model.selected_versions == []:
            self.view.open_info_prompt(text='At least one measure version is'
                                            ' required to create a summary')
            return

        file_info = self.get_file_info()
        if file_info == None:
            return

        self.view.open_prompt('Retrieving measures, please be patient...')
        dir_path, file_name = file_info
        error: Exception | None = None
        try:
            summary = MeasureSummary(dir_path=dir_path,
                                     file_name=file_name,
                                     connection=self.connection)
            for measure_id in self.model.selected_versions:
                self.view.update_prompt(f'Retrieving measure {measure_id}...')
                measure = self.get_measure(measure_id)
                summary.add_measure(measure)
        except Exception as err:
            error = err
        else:
            try:
                self.view.update_prompt('Generating summary PDF...')
                summary.build()
                self.clear_selected_measures()
                self.unfocus()
                self.view.close_prompt()
                self.view.open_info_prompt('Success!')
                return
            except Exception as err:
                error = err

        self.view.close_prompt()
        self.perror(error)

    def __bind_selected_list(self):
        """Binds events to the widgets in the selected measure version
        ID frame in the Home view.
        """

        view = self.view.measures_selection_list
        view.add_btn.configure(command=self.create_summary)
        view.clear_btn.configure(command=self.clear_selected_measures)
        view.search_bar.search_bar.bind('<Return>', self.add_measure_version)
        view.search_bar.search_bar.bind('<Escape>', self.unfocus)
