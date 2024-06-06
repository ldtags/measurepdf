import os
import re
import sys
import customtkinter as ctk

from src import _ROOT, patterns
from src.app.views import View
from src.app.models import Model
from src.summarygen import MeasureSummary
from src.exceptions import (
    ETRMResponseError,
    UnauthorizedError,
    NotFoundError
)


class HomeController:
    """MVC Controller for the Home module."""

    def __init__(self, model: Model, view: View):
        self.model = model
        self.view = view
        self.page = view.home
        self.__bind_id_list()
        self.__bind_version_list()
        self.__bind_selected_list()

    def sanitize_stwd_id(self, statewide_id: str) -> str | None:
        """Ensures that `statewide_id` is a valid measure
        statewide id.
        """

        re_match = re.search(patterns.STWD_ID, statewide_id)
        if re_match == None:
            return None

        sanitized = statewide_id.upper()
        return sanitized

    def sanitize_vrsn_id(self, version_id: str) -> str | None:
        """Ensures that `version_id` is a valid measure
        version id.
        """

        re_match = re.search(patterns.VRSN_ID, version_id)
        if re_match == None:
            return None

        sanitized = re_match.group(2).upper() + '-' + re_match.group(3)
        return sanitized

    def unfocus(self, *args):
        """Removes focus from any currently focused widget."""

        self.page.focus()

    def show(self):
        """Shows the home view."""

        if self.model.home.measure_ids == [] or self.model.home.count == 0:
            measure_ids, count = self.model.connection.get_init_measure_ids()
            self.model.home.measure_ids = measure_ids
            self.model.home.count = count
            self.page.measure_id_list.measure_ids = measure_ids

        self.page.tkraise()

    def perror(self, error: Exception):
        if isinstance(error, NotFoundError):
            self.page.open_info_prompt(error.message,
                                       title=' Measure Not Found')
        elif isinstance(error, ETRMResponseError):
            self.page.open_info_prompt(error.message,
                                       title=' Server Error')
        elif isinstance(error, UnauthorizedError):
            self.page.open_info_prompt(error.message,
                                       title=' Unauthorized Access')
        elif isinstance(error, PermissionError) and error.errno == 13:
            self.page.open_info_prompt('Cannot overwrite the PDF while it is'
                                       ' open.',
                                       title=' Permission Error')
        elif isinstance(error, ConnectionError):
            self.page.open_info_prompt('Please check your network connection'
                                       ' and try again.',
                                       title=' Connection Error')
        else:
            self.page.open_info_prompt('An unexpected error occurred:'
                                       f'\n{error}',
                                       title=' Error')

    def is_selected_measure(self, measure_id: str) -> bool:
        """Determines if `measure_id` is already selected."""

        return measure_id in self.model.home.selected_measures

    def is_current_measure(self, measure_id: str) -> bool:
        """Determines if `measure_id` exists on the current page."""

        return measure_id in self.page.measure_id_list.measure_ids

    def is_selected_version(self, version_id: str) -> bool:
        """Determines if `version_id` is already selected."""

        return version_id in self.model.home.selected_versions

    def get_measure_ids(self) -> list[str]:
        """Returns a list of measure IDs.

        Uses the `offset` and `limit` from the Home model to retrieve
        the current set of measure IDs from the eTRM API.

        Does not handle eTRM connection errors.
        """

        offset = self.model.home.offset
        limit = self.model.home.limit
        return self.model.connection.get_measure_ids(offset, limit)

    def get_measure_versions(self) -> list[str]:
        """Returns a list of all versions of all selected measures.

        Does not handle eTRM connection errors.
        """

        versions = []
        for id in self.model.home.selected_measures:
            id_versions = self.model.connection.get_measure_versions(id)
            versions.extend(id_versions)

        return versions

    def update_measure_ids(self, measures: list[str] | None=None):
        """Sets the measure IDs in the Home view to the correct set of
        measure IDs using the `offset` and `limit` in the Home model.

        Does not handle eTRM connection errors.
        """

        measure_ids = measures or self.get_measure_ids()
        self.model.home.measure_ids = measure_ids
        self.page.measure_id_list.measure_ids = measure_ids
        self.page.measure_id_list.selected_measures = list(
            filter(lambda measure: self.is_selected_measure(measure),
                   measure_ids))

    def update_measure_versions(self, versions: list[str] | None=None):
        """Sets the measure version IDs in the Home view to the versions
        of the currently selected measures.

        Does not handle eTRM connection errors.
        """

        measure_versions = versions or self.get_measure_versions()
        self.model.home.measure_versions = measure_versions
        self.page.measure_version_list.versions = measure_versions
        self.page.measure_version_list.selected_versions = list(
            filter(lambda version: self.is_selected_version(version),
                   measure_versions))

    def select_measure_id(self, measure_ids: list[str] | None=None):
        """Event that occurs when a measure ID is selected.

        If any error occurs while retrieving version IDs of the currently
        selected measures, the user selection is reset and the version IDs
        in the Home view do not change.

        Opens an info popup on error defining which error occurred.
        """

        self.page.measure_id_list.measure_frame.disable()
        try:
            prev_selections = self.model.home.selected_measures.copy()
            cur_selections = self.page.measure_id_list.selected_measures
            if measure_ids != None:
                cur_selections.extend(measure_ids)

            selected = list(set(cur_selections).difference(prev_selections))
            self.model.home.selected_measures.extend(selected)

            unselected = list(
                filter(lambda measure: self.is_current_measure(measure),
                       set(prev_selections).difference(cur_selections)))
            for measure_id in unselected:
                self.model.home.selected_measures.remove(measure_id)

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
        except ConnectionError:
            self.page.open_info_prompt('Please check your network connection'
                                       ' and try again.',
                                       title=' Connection Error')
        finally:
            self.page.measure_id_list.measure_frame.enable()

        self.model.home.selected_measures = prev_selections
        self.page.measure_id_list.selected_measures = prev_selections

    def next_id_page(self):
        """Increments the current set of measure IDs shown in the Home view.

        Updates the current set of measure IDs in the Home view accordingly.

        Opens an info popup on error defining which error occurred.
        """

        try:
            self.model.home.increment_offset()
            self.update_measure_ids()
            if self.model.home.offset != 0:
                self.page.measure_id_list.back_btn.configure(state=ctk.NORMAL)
            next_offset = self.model.home.offset + self.model.home.limit
            if next_offset >= self.model.home.count:
                self.page.measure_id_list.next_btn.configure(state=ctk.DISABLED)
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
        except ConnectionError:
            self.page.open_info_prompt('Please check your network connection'
                                       ' and try again.',
                                       title=' Connection Error')
        self.model.home.decrement_offset()

    def prev_id_page(self):
        """Decrements the current set of measure IDs shown in the Home view.

        Updates the current set of measure IDs in the Home view accordingly.

        Disables the `back_btn` in the Home view if the `offset` from the Home
        model is 0.

        Opens an info popup on error defining which error occurred.
        """

        try:
            self.model.home.decrement_offset()
            self.update_measure_ids()
            if self.model.home.offset == 0:
                self.page.measure_id_list.back_btn.configure(state=ctk.DISABLED)
            next_offset = self.model.home.offset + self.model.home.limit
            if next_offset < self.model.home.count:
                self.page.measure_id_list.next_btn.configure(state=ctk.NORMAL)
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
        except ConnectionError:
            self.page.open_info_prompt('Please check your network connection'
                                       ' and try again.',
                                       title=' Connection Error')
        self.model.home.increment_offset()

    def reset_ids(self):
        """Resets the measure IDs frame and selected measure in the
        Home view and the selected measure in the Home model.

        Opens an info popup on error defining which error occurred.
        """

        self.model.home.selected_measures = []
        self.page.measure_id_list.selected_measures = []
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
        except ConnectionError:
            self.page.open_info_prompt('Please check your network connection'
                                       ' and try again.',
                                       title=' Connection Error')
        self.unfocus()

    def search_measure_ids(self, *args):
        """Searches for a specific measure ID in the eTRM API.

        Updates the measure versions in the Home view accordingly.

        Opens an info popup on error defining which error occurred.
        """

        search_val = self.page.measure_id_list.search_bar.get()
        try:
            if search_val == '':
                self.page.open_info_prompt('Please enter the statewide id'
                                           ' of the measure being searched'
                                           ' for.',
                                           title=' Missing Statewide ID')
                return

            re_match = re.search(patterns.STWD_ID, search_val)
            if re_match == None:
                self.page.open_info_prompt(f'{search_val} is not a valid'
                                           ' statewide ID (i.e., SWAP001).',
                                           title=' Invalid Statewide ID')
                return

            self.select_measure_id([search_val])
        finally:
            self.page.measure_id_list.search_bar.clear()
            self.unfocus()

    def __bind_id_list(self):
        """Binds events to the widgets in the measure ID frame in
        the Home view.
        """

        self.page.measure_id_list.measure_frame.set_command(self.select_measure_id)
        self.page.measure_id_list.next_btn.configure(command=self.next_id_page)
        self.page.measure_id_list.back_btn.configure(command=self.prev_id_page)
        self.page.measure_id_list.search_bar.search_btn.configure(command=self.search_measure_ids)
        self.page.measure_id_list.search_bar.search_bar.bind('<Return>', self.search_measure_ids)
        self.page.measure_id_list.search_bar.search_bar.bind('<Escape>', self.unfocus)
        self.page.measure_id_list.search_bar.reset_btn.configure(command=self.reset_ids)

    def update_measure_selections(self):
        """Sets the selected measure versions in the Home view to the
        selected measure versions in the Home model.

        Disables the selected measure control panel if no versions are
        selected.

        Enables the selected measure control panel if any version is
        selected.
        """

        self.page.measures_selection_list.measures = self.model.home.selected_versions
        if self.model.home.selected_versions != []:
            self.page.measures_selection_list.clear_btn.configure(state=ctk.NORMAL)
            self.page.measures_selection_list.add_btn.configure(state=ctk.NORMAL)
        else:
            self.page.measures_selection_list.clear_btn.configure(state=ctk.DISABLED)
            self.page.measures_selection_list.add_btn.configure(state=ctk.DISABLED)

    def select_measure_version(self):
        """Event that occurs when a measure version ID is selected.

        Adds any newly selected versions to `selected_versions` in the
        Home model.

        Removes any unselected versions from `selected_versions` in the
        Home model.

        Updates the selected measure versions in the Home view accordingly.
        """

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
        """Sets the measure versions shown in the Home view to the set
        of all of the currently selected measure's versions.

        Opens an info popup on error defining which error occurred.
        """

        self.page.measure_version_list.search_bar.clear()
        try:
            if self.model.home.selected_measures != []:
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
        except ConnectionError:
            self.page.open_info_prompt('Please check your network connection'
                                       ' and try again.',
                                       title=' Connection Error')
        self.unfocus()

    def search_measure_versions(self, *args):
        """Searches the versions of the currently selected measure for
        the version in the search bar entry widget.

        Displays an empty set of versions if none are found.
        """

        search_val = self.page.measure_version_list.search_bar.get()
        try:
            re_match = re.search(patterns.STWD_ID, search_val)
            if re_match != None:
                stwd_id = search_val.upper()
                versions = self.model.home.measure_versions.get(stwd_id, [])
                self.update_measure_versions(versions)
                return

            re_match = re.search(patterns.VRSN_ID, search_val)
            if re_match != None:
                stwd_id = re_match.group(2).upper()
                versions = self.model.home.measure_versions.get(stwd_id, [])
                if versions != []:
                    vrsn_id = stwd_id + '-' + re_match.group(3)
                    if vrsn_id in versions:
                        versions = [vrsn_id]
                self.update_measure_versions(versions)
                return

            self.update_measure_versions([])
        finally:
            self.page.measure_version_list.search_bar.clear()
            self.unfocus()

    def __bind_version_list(self):
        """Binds events to the widgets in the measure version ID frame in
        the Home view.
        """

        self.page.measure_version_list.version_frame.set_command(self.select_measure_version)
        self.page.measure_version_list.search_bar.search_btn.configure(command=self.search_measure_versions)
        self.page.measure_version_list.search_bar.search_bar.bind('<Return>', self.search_measure_versions)
        self.page.measure_version_list.search_bar.search_bar.bind('<Escape>', self.unfocus)
        self.page.measure_version_list.search_bar.reset_btn.configure(command=self.reset_versions)

    def clear_selected_measures(self):
        """Clears all selected measures from the Home view and Home model."""

        self.model.home.selected_versions = []
        self.page.measures_selection_list.measures = []
        self.page.measure_version_list.selected_versions = []
        self.page.measures_selection_list.clear_btn.configure(state=ctk.DISABLED)
        self.page.measures_selection_list.add_btn.configure(state=ctk.DISABLED)

    def __add_measure_version(self, version_id: str):
        error: Exception | None = None
        try:
            self.model.connection.get_measure(version_id)
            self.model.home.selected_versions.append(version_id)
            self.update_measure_selections()
        except Exception as err:
            error = err
        finally:
            self.page.close_prompt()

        if error == None:
            return

        self.perror(error)

    def add_measure_version(self, *args):
        """Directly adds a measure version to the selected measure versions.

        Opens an info popup on error defining which error occurred.
        """

        search_val = self.page.measures_selection_list.search_bar.get()
        if search_val == '':
            self.page.open_info_prompt('Please enter the full statewide ID'
                                       ' for the desired measure.',
                                       title=' Missing Statewide ID')
            return

        version_id = self.sanitize_vrsn_id(search_val)
        if version_id == None:
            self.page.open_info_prompt('Cannot find a measure with the full'
                                       f' statewide ID: {search_val}',
                                       title=' Invalid Statewide ID')
            return

        if version_id in self.model.home.selected_versions:
            self.page.open_info_prompt(f'{version_id} is already selected.',
                                       title=' Redundant Selection')
            return

        self.page.open_prompt(f'Searching for measure {version_id}...')
        self.page.after(1000, self.__add_measure_version, version_id)
        self.page.measures_selection_list.search_bar.clear()
        self.unfocus()

    def __create_summary(self, dir_path, file_name):
        """Generates the measure summary PDF from the selected measure
        versions found in the Home model.

        Opens an info popup on error defining which error occurred.
        """

        error: Exception | None = None
        try:
            summary = MeasureSummary(dir_path=dir_path, file_name=file_name)
            for measure_id in self.model.home.selected_versions:
                self.page.update_prompt(f'Retrieving measure {measure_id}...')
                measure = self.model.connection.get_measure(measure_id)
                summary.add_measure(measure)
        except Exception as err:
            error = err

        if error == None:
            try:
                self.page.update_prompt('Generating summary PDF...')
                summary.build()
                self.clear_selected_measures()
                self.unfocus()
                self.page.close_prompt()
                self.page.open_info_prompt('Success!')
                return
            except Exception as err:
                error = err

        self.page.close_prompt()
        self.perror(error)

    def create_summary(self):
        """Opens the user prompts for defining the file name and destination
        of the measure summary PDF.

        Calls the measure summary PDF generation function after user input.
        """

        if self.model.home.selected_versions != []:
            if getattr(sys, 'frozen', False):
                def_path = os.path.join(_ROOT, '..', '..', 'summaries')
            else:
                def_path = os.path.join(_ROOT, '..', 'summaries')
            def_path = os.path.normpath(def_path)
            if not os.path.exists(def_path):
                self.page.open_info_prompt(f'no {def_path} folder exists')
                return
            def_fname = 'measure_summary'
            result = self.page.open_fd_prompt(def_path,
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

            self.page.open_prompt('Retrieving measures, please be patient...')
            self.page.after(1000, self.__create_summary, dir_path, file_name)
        else:
            self.page.open_info_prompt(text='At least one measure version is'
                                            ' required to create a summary')

    def __bind_selected_list(self):
        """Binds events to the widgets in the selected measure version
        ID frame in the Home view.
        """

        self.page.measures_selection_list.add_btn.configure(command=self.create_summary)
        self.page.measures_selection_list.clear_btn.configure(command=self.clear_selected_measures)
        self.page.measures_selection_list.search_bar.add_btn.configure(command=self.add_measure_version)
        self.page.measures_selection_list.search_bar.search_bar.bind('<Return>', self.add_measure_version)
        self.page.measures_selection_list.search_bar.search_bar.bind('<Escape>', self.unfocus)
